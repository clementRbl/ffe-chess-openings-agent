"""Traduction des coups d'échecs en notation française.

Lichess renvoie la notation algébrique anglaise (« Nf3 »), alors que les
recommandations rédigées par l'agent s'adressent à un public francophone
(« Cf3 »). La conversion est appliquée aux textes produits pour l'utilisateur ;
les données conservées, elles, gardent la notation standard.
"""

# Initiale de chaque pièce, de l'anglais vers le français.
PIECES = {
    "K": "R",  # King -> Roi
    "Q": "D",  # Queen -> Dame
    "R": "T",  # Rook -> Tour
    "B": "F",  # Bishop -> Fou
    "N": "C",  # Knight -> Cavalier
}


def to_french_san(san: str) -> str:
    """Traduit un coup de la notation algébrique anglaise vers la française.

    Seules les majuscules désignent des pièces : les minuscules sont des
    colonnes (``b`` est la colonne b, ``B`` est le fou). Les coups de pion, les
    roques, les prises et les indications d'échec ou de mat traversent donc la
    fonction sans être modifiés.

    Args:
        san: Coup en notation algébrique anglaise, par exemple ``"Nf3"``.

    Returns:
        Le coup en notation française, par exemple ``"Cf3"``.
    """
    return "".join(PIECES.get(char, char) for char in san)
