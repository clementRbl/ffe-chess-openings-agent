"""Tests du dépôt Milvus.

Régression : le client Milvus garde un canal gRPC ouvert. Après un redémarrage
de Milvus, ce canal devient inutilisable et la recherche documentaire restait en
panne jusqu'au redémarrage du backend, alors même que la base était de nouveau
disponible et déclarée saine.
"""

import pytest

from app.services.milvus_client import MilvusError, MilvusRepository

UN_VECTEUR = [0.1, 0.2, 0.3]

RESULTAT = [
    [
        {
            "distance": 0.58,
            "entity": {"title": "Défense sicilienne", "text": "Un passage."},
        }
    ]
]


class FakeClient:
    """Client simulé, qui peut échouer un nombre donné de fois avant de répondre."""

    def __init__(self, echecs_restants: int = 0) -> None:
        self.echecs_restants = echecs_restants
        self.appels = 0
        self.ferme = False

    def search(self, **_kwargs):
        self.appels += 1
        if self.echecs_restants > 0:
            self.echecs_restants -= 1
            raise RuntimeError("Cannot invoke RPC on closed channel!")
        return RESULTAT

    def close(self):
        self.ferme = True


def _depot(
    monkeypatch, clients: list[FakeClient], vus: list[dict] | None = None
) -> MilvusRepository:
    """Construit un dépôt dont chaque reconnexion renvoie le client suivant.

    ``vus`` recueille, si fourni, les arguments passés à chaque construction de
    client — de quoi vérifier les options de connexion demandées.
    """
    from app.services import milvus_client as module

    restants = list(clients)

    def fabrique(**kwargs):
        if vus is not None:
            vus.append(kwargs)
        return restants.pop(0)

    monkeypatch.setattr(module, "MilvusClient", fabrique)
    return MilvusRepository()


def test_the_connection_is_dedicated(monkeypatch):
    """La connexion ne doit pas passer par le registre partagé de pymilvus.

    Régression : après un redémarrage de Milvus, le registre partagé resservait
    un canal gRPC définitivement fermé, et la recherche documentaire restait en
    panne jusqu'au redémarrage du backend.
    """
    vus: list[dict] = []
    depot = _depot(monkeypatch, [FakeClient()], vus)

    depot.search(UN_VECTEUR, top_k=1)

    assert vus[0]["dedicated"] is True


def test_search_maps_hits_to_the_domain_shape(monkeypatch):
    """Une recherche réussie est traduite en passages exploitables."""
    depot = _depot(monkeypatch, [FakeClient()])

    passages = depot.search(UN_VECTEUR, top_k=1)

    assert passages == [
        {"title": "Défense sicilienne", "text": "Un passage.", "score": 0.58}
    ]


def test_a_dead_channel_triggers_a_reconnection(monkeypatch):
    """Un canal gRPC mort provoque une reconnexion et une seconde tentative."""
    mort, neuf = FakeClient(echecs_restants=1), FakeClient()
    depot = _depot(monkeypatch, [mort, neuf])

    passages = depot.search(UN_VECTEUR, top_k=1)

    # Le premier client a échoué, le second a répondu : le service est rétabli
    # sans redémarrage du backend.
    assert mort.appels == 1
    assert neuf.appels == 1
    assert passages[0]["title"] == "Défense sicilienne"
    # Le canal rompu doit être explicitement fermé, sans quoi ``pymilvus`` le
    # resservirait au client suivant et la reconnexion serait inopérante.
    assert mort.ferme is True


def test_a_client_that_fails_to_close_does_not_break_the_retry(monkeypatch):
    """Une fermeture qui échoue ne doit pas empêcher la reconnexion."""

    class ClientRecalcitrant(FakeClient):
        def close(self):
            raise RuntimeError("channel already gone")

    depot = _depot(monkeypatch, [ClientRecalcitrant(echecs_restants=1), FakeClient()])

    passages = depot.search(UN_VECTEUR, top_k=1)

    assert passages[0]["title"] == "Défense sicilienne"


def test_a_real_outage_still_raises(monkeypatch):
    """Milvus réellement indisponible : l'erreur remonte après la seconde tentative.

    La reconnexion ne doit pas masquer une panne : le nœud du graphe a besoin de
    l'erreur pour signaler la source comme indisponible.
    """
    depot = _depot(
        monkeypatch, [FakeClient(echecs_restants=1), FakeClient(echecs_restants=1)]
    )

    with pytest.raises(MilvusError, match="Milvus search failed"):
        depot.search(UN_VECTEUR, top_k=1)


def test_only_one_retry_is_attempted(monkeypatch):
    """La reconnexion n'est tentée qu'une fois, sans boucle de tentatives."""
    clients = [FakeClient(echecs_restants=1), FakeClient(echecs_restants=1)]
    depot = _depot(monkeypatch, clients)

    with pytest.raises(MilvusError):
        depot.search(UN_VECTEUR, top_k=1)

    # Deux clients consommés, un appel chacun : pas de troisième tentative.
    assert [c.appels for c in clients] == [1, 1]
