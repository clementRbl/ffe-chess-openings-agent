"""Sélection des passages documentaires servis à l'utilisateur.

La recherche vectorielle classe les passages du corpus par proximité avec
l'ouverture jouée, mais elle en renvoie toujours le nombre demandé : sur la
sicilienne, le troisième passage le plus proche parlait de la Caro-Kann, faute
de mieux. Un enfant lisait donc une explication portant sur une autre ouverture,
sans rien pour l'en avertir.

Un seuil de score ne résout pas le problème : les mesures sur le corpus montrent
que les plages se recouvrent. Une ouverture bel et bien documentée peut plafonner
à 0,46 (la française Winawer) tandis qu'une ouverture absente du corpus atteint
0,58 (la Nimzo-indienne, rapprochée de l'est-indienne). Aucune valeur ne sépare
les deux cas.

Ce qui se décide en revanche de façon fiable, c'est **de quelle fiche** parlent
les passages. Le corpus est organisé par ouverture, une fiche par ouverture : en
ne retenant que les passages d'une seule fiche, la carte ne peut plus mélanger
deux ouvertures. Et comme le nom de la fiche retenue est affiché, le lecteur
sait toujours ce qu'il lit — y compris dans le cas, indétectable autrement, où
son ouverture n'est pas couverte par le corpus.
"""


def keep_best_source(hits: list[dict], limit: int) -> list[dict]:
    """Ne conserve que les passages issus de la fiche la mieux classée.

    Args:
        hits: Passages renvoyés par la recherche vectorielle, du plus proche au
            plus lointain. Chacun porte le titre de sa fiche d'origine.
        limit: Nombre maximal de passages à conserver.

    Returns:
        Les ``limit`` premiers passages de la fiche du passage le mieux classé,
        dans leur ordre d'origine. Une liste vide en entrée ressort vide.
    """
    if not hits:
        return []

    source = hits[0].get("title")
    return [hit for hit in hits if hit.get("title") == source][:limit]
