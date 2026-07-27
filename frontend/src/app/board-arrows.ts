/**
 * Tracé des flèches superposées à l'échiquier.
 *
 * Les coordonnées sont exprimées en cases plutôt qu'en pixels : le calque SVG
 * déclare un repère de 8 × 8, si bien que les tracés restent justes quelle que
 * soit la taille à laquelle le plateau est affiché.
 *
 * Repère retenu — celui d'un plateau vu du côté des Blancs : la colonne « a »
 * est à gauche (x = 0) et la rangée 8 en haut (y = 0).
 */

/** Nombre de cases sur un côté du plateau. */
const BOARD_SIZE = 8;

/** Retrait du trait au départ, pour ne pas masquer la pièce qui joue. */
const START_GAP = 0.34;

/** Retrait à l'arrivée, pour laisser la place à la pastille numérotée. */
const END_GAP = 0.26;

/** Point du repère du plateau, en cases. */
export interface BoardPoint {
  x: number;
  y: number;
}

/** Flèche prête à être rendue par le template. */
export interface MoveArrow {
  /** Rang du coup (1 = le plus joué) ; 0 pour le coup du moteur. */
  rank: number;
  /** Étiquette portée par la pastille d'arrivée. */
  label: string;
  /** Tracé SVG, exprimé en cases. */
  path: string;
  /** Centre de la case d'arrivée, où se pose la pastille. */
  target: BoardPoint;
  /** Origine de la recommandation, qui détermine l'habillage. */
  kind: 'master' | 'engine';
}

/** Coup dont on sait tracer la flèche. */
interface PlayableMove {
  uci: string;
}

/** Nombre de flèches « coups des maîtres » affichées simultanément. */
export const MAX_MASTER_ARROWS = 3;

/** Écart appliqué aux pastilles qui visent la même case. */
const PIN_SPREAD = 0.46;

/**
 * Centre d'une case, en coordonnées de plateau.
 *
 * @param square Case en notation algébrique (« e4 »).
 */
export function squareCenter(square: string): BoardPoint {
  const file = square.charCodeAt(0) - 'a'.charCodeAt(0);
  const rank = Number(square[1]);
  return { x: file + 0.5, y: BOARD_SIZE - rank + 0.5 };
}

/**
 * Vrai si le déplacement est un saut de cavalier.
 *
 * Le saut en « L » (deux cases dans un sens, une dans l'autre) n'appartient
 * qu'au cavalier : la géométrie suffit à le reconnaître, sans avoir besoin de
 * connaître la pièce déplacée.
 */
export function isKnightJump(from: BoardPoint, to: BoardPoint): boolean {
  const dx = Math.abs(to.x - from.x);
  const dy = Math.abs(to.y - from.y);
  return (dx === 1 && dy === 2) || (dx === 2 && dy === 1);
}

/** Point situé à `distance` de `from` en direction de `to`. */
function along(from: BoardPoint, to: BoardPoint, distance: number): BoardPoint {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.hypot(dx, dy) || 1;
  return {
    x: from.x + (dx / length) * distance,
    y: from.y + (dy / length) * distance,
  };
}

/** Arrondi à trois décimales, pour ne pas alourdir le tracé. */
function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}

/**
 * Tracé SVG d'un coup donné en notation UCI (« g1f3 »).
 *
 * Le cavalier suit un trajet en « L », le grand côté d'abord, comme sur les
 * diagrammes d'ouverture : une ligne droite entre g1 et f3 ne ressemblerait à
 * aucun déplacement légal.
 */
export function arrowPath(uci: string): string {
  const from = squareCenter(uci.slice(0, 2));
  const to = squareCenter(uci.slice(2, 4));

  const points: BoardPoint[] = [from];
  if (isKnightJump(from, to)) {
    const horizontalFirst = Math.abs(to.x - from.x) > Math.abs(to.y - from.y);
    points.push(
      horizontalFirst ? { x: to.x, y: from.y } : { x: from.x, y: to.y },
    );
  }
  points.push(to);

  const last = points.length - 1;
  points[0] = along(points[0], points[1], START_GAP);
  points[last] = along(points[last], points[last - 1], END_GAP);

  return points
    .map(
      (point, index) =>
        `${index === 0 ? 'M' : 'L'}${round(point.x)} ${round(point.y)}`,
    )
    .join(' ');
}

/**
 * Écarte latéralement les pastilles qui visent la même case.
 *
 * Plusieurs coups aboutissent souvent au même endroit — sur la sicilienne, le
 * cavalier et le pion vont tous deux en c3. Sans cet écartement, la dernière
 * pastille tracée masquerait purement et simplement les précédentes.
 */
function spreadOverlappingPins(arrows: MoveArrow[]): void {
  const groups = new Map<string, MoveArrow[]>();
  for (const arrow of arrows) {
    const key = `${arrow.target.x},${arrow.target.y}`;
    groups.set(key, [...(groups.get(key) ?? []), arrow]);
  }

  for (const group of groups.values()) {
    if (group.length < 2) {
      continue;
    }
    group.forEach((arrow, index) => {
      const offset = (index - (group.length - 1) / 2) * PIN_SPREAD;
      arrow.target = {
        x: round(arrow.target.x + offset),
        y: arrow.target.y,
      };
    });
  }
}

/**
 * Construit les flèches à superposer au plateau.
 *
 * Les trois coups les plus joués sont tracés ensemble et numérotés comme dans
 * la liste des recommandations : c'est leur comparaison qui a une valeur
 * pédagogique. Le coup du moteur n'est ajouté que s'il en diffère, faute de
 * quoi deux flèches se superposeraient exactement.
 *
 * @param moves Coups théoriques, du plus joué au moins joué.
 * @param bestMove Coup du moteur en notation UCI, s'il est connu.
 */
export function buildArrows(
  moves: PlayableMove[],
  bestMove: string | null | undefined,
): MoveArrow[] {
  const masters = moves.slice(0, MAX_MASTER_ARROWS);
  const arrows: MoveArrow[] = masters.map((move, index) => ({
    rank: index + 1,
    label: String(index + 1),
    path: arrowPath(move.uci),
    target: squareCenter(move.uci.slice(2, 4)),
    kind: 'master',
  }));

  // Les coups de Lichess portent parfois la pièce de promotion en cinquième
  // caractère : la comparaison se fait sur les seules cases de départ et
  // d'arrivée.
  const alreadyDrawn = masters.some(
    (move) => move.uci.slice(0, 4) === bestMove?.slice(0, 4),
  );
  if (bestMove && !alreadyDrawn) {
    arrows.push({
      rank: 0,
      label: '★',
      path: arrowPath(bestMove),
      target: squareCenter(bestMove.slice(2, 4)),
      kind: 'engine',
    });
  }

  spreadOverlappingPins(arrows);
  return arrows;
}
