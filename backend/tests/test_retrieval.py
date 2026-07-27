"""Tests de la sélection des passages documentaires.

Régression : la carte « Comprendre cette ouverture » servait, sur la défense
sicilienne, un troisième passage traitant de la Caro-Kann. La recherche
vectorielle renvoyant toujours le nombre de passages demandé, le moins mauvais
candidat était affiché même lorsqu'il portait sur une autre ouverture.
"""

from app.graph.retrieval import keep_best_source


def _passage(title: str, score: float) -> dict:
    return {"title": title, "text": f"Extrait de {title}.", "score": score}


def test_passages_of_another_opening_are_dropped():
    """Seuls les passages de la fiche la mieux classée sont conservés."""
    hits = [
        _passage("Défense sicilienne", 0.58),
        _passage("Défense sicilienne", 0.52),
        _passage("Défense Caro-Kann", 0.45),
    ]

    passages = keep_best_source(hits, limit=3)

    assert [p["title"] for p in passages] == [
        "Défense sicilienne",
        "Défense sicilienne",
    ]


def test_the_best_ranked_source_wins_even_if_a_minority():
    """La fiche retenue est celle du passage le plus proche, pas la plus nombreuse.

    Le classement de la recherche fait foi : c'est la seule information dont on
    dispose sur la pertinence.
    """
    hits = [
        _passage("Partie italienne", 0.51),
        _passage("Défense Caro-Kann", 0.49),
        _passage("Défense Caro-Kann", 0.47),
    ]

    passages = keep_best_source(hits, limit=3)

    assert [p["title"] for p in passages] == ["Partie italienne"]


def test_the_displayed_count_is_capped():
    """Le vivier interrogé est plus large que ce qui est affiché."""
    hits = [_passage("Défense française", 0.6 - index / 100) for index in range(8)]

    passages = keep_best_source(hits, limit=3)

    assert len(passages) == 3
    # L'ordre de la recherche est conservé : du plus proche au plus lointain.
    assert [p["score"] for p in passages] == [0.6, 0.59, 0.58]


def test_an_empty_search_stays_empty():
    """Une recherche sans résultat ne doit pas faire échouer l'analyse."""
    assert keep_best_source([], limit=3) == []


def test_passages_without_a_title_are_grouped_together():
    """Un passage sans titre ne doit pas provoquer d'erreur.

    Le corpus est censé titrer chaque fiche, mais l'absence de titre ne doit
    pas interrompre l'analyse en cours de route.
    """
    hits = [_passage(None, 0.6), _passage(None, 0.55), _passage("Gambit dame", 0.5)]

    passages = keep_best_source(hits, limit=3)

    assert len(passages) == 2
    assert all(p["title"] is None for p in passages)
