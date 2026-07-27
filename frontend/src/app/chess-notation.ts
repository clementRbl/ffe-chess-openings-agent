// Traduction des coups d'échecs en notation française.
//
// L'API Lichess renvoie la notation algébrique anglaise (« Nf3 »), alors que le
// public visé et les fiches d'ouverture de l'application sont francophones
// (« Cf3 »). La conversion se fait donc à l'affichage : l'API conserve la
// notation standard, l'interface parle la langue de l'utilisateur.

// Initiale de chaque pièce, de l'anglais vers le français.
const PIECES: Record<string, string> = {
  K: 'R', // King -> Roi
  Q: 'D', // Queen -> Dame
  R: 'T', // Rook -> Tour
  B: 'F', // Bishop -> Fou
  N: 'C', // Knight -> Cavalier
};

/**
 * Traduit un coup de la notation algébrique anglaise vers la française.
 *
 * Seules les majuscules désignent des pièces : les minuscules sont des colonnes
 * (`b` est la colonne b, `B` est le fou). Les coups de pion, les roques, les
 * prises et les indications d'échec ou de mat traversent donc la fonction sans
 * être modifiés.
 *
 * @example toFrenchSan('Nf3')   // 'Cf3'
 * @example toFrenchSan('Bxc6+') // 'Fxc6+'
 * @example toFrenchSan('e8=Q')  // 'e8=D'
 */
export function toFrenchSan(san: string): string {
  return san.replace(/[KQRBN]/g, (letter) => PIECES[letter]);
}

/**
 * Met en forme un coup reçu en notation UCI, celle des moteurs d'échecs.
 *
 * « g1f3 » décrit un déplacement de la case g1 vers la case f3 ; on l'affiche
 * tel quel plutôt que de le convertir, la traduction en notation française
 * demanderait de connaître la pièce déplacée.
 *
 * @example formatUciMove('g1f3')  // 'g1 → f3'
 * @example formatUciMove('e7e8q') // 'e7 → e8=D'
 */
export function formatUciMove(uci: string): string {
  const move = `${uci.slice(0, 2)} → ${uci.slice(2, 4)}`;
  const promotion = uci.slice(4, 5).toUpperCase();
  return promotion ? `${move}=${PIECES[promotion] ?? promotion}` : move;
}
