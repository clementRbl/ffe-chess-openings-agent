import {
  arrowPath,
  buildArrows,
  isKnightJump,
  squareCenter,
} from './board-arrows';

describe('Repère du plateau', () => {
  it('place la colonne a à gauche et la rangée 1 en bas', () => {
    expect(squareCenter('a1')).toEqual({ x: 0.5, y: 7.5 });
    expect(squareCenter('h8')).toEqual({ x: 7.5, y: 0.5 });
    expect(squareCenter('e4')).toEqual({ x: 4.5, y: 4.5 });
  });

  it('reconnaît un saut de cavalier à sa géométrie', () => {
    expect(isKnightJump(squareCenter('g1'), squareCenter('f3'))).toBeTrue();
    expect(isKnightJump(squareCenter('b1'), squareCenter('c3'))).toBeTrue();
    // Deux cases en ligne droite : c'est le pion, pas le cavalier.
    expect(isKnightJump(squareCenter('e2'), squareCenter('e4'))).toBeFalse();
    // Diagonale du fou.
    expect(isKnightJump(squareCenter('f1'), squareCenter('c4'))).toBeFalse();
  });
});

describe('Tracé des flèches', () => {
  it('relie deux cases par un segment droit', () => {
    const path = arrowPath('e2e4');

    // Un seul segment : la colonne ne change pas, seule la rangée bouge. Les
    // deux extrémités sont raccourcies pour dégager la pièce et la pastille.
    expect(path).toBe('M4.5 6.16 L4.5 4.76');
  });

  it('fait passer le cavalier par un coude, grand côté d’abord', () => {
    const path = arrowPath('g1f3');

    // g1 → f3 : deux rangées puis une colonne, donc coude sur g3.
    expect(path.split(' L').length).toBe(3);
    expect(path).toContain('L6.5 5.5');
  });

  it('ignore la pièce de promotion quand elle est précisée', () => {
    expect(arrowPath('e7e8q')).toBe(arrowPath('e7e8'));
  });
});

describe('Flèches à superposer au plateau', () => {
  const MOVES = [
    { uci: 'g1f3' },
    { uci: 'b1c3' },
    { uci: 'c2c3' },
    { uci: 'd2d4' },
  ];

  it('numérote au plus trois coups de maîtres, dans l’ordre de la liste', () => {
    const arrows = buildArrows(MOVES, null);

    expect(arrows.length).toBe(3);
    expect(arrows.map((arrow) => arrow.label)).toEqual(['1', '2', '3']);
    expect(arrows.every((arrow) => arrow.kind === 'master')).toBeTrue();
  });

  it('ajoute le coup du moteur lorsqu’il sort de la liste', () => {
    const arrows = buildArrows(MOVES, 'd2d4');

    expect(arrows.length).toBe(4);
    expect(arrows[3].kind).toBe('engine');
    expect(arrows[3].label).toBe('★');
    expect(arrows[3].target).toEqual(squareCenter('d4'));
  });

  // Sans cette précaution, deux flèches identiques se superposeraient.
  it('n’ajoute pas le coup du moteur s’il est déjà tracé', () => {
    const arrows = buildArrows(MOVES, 'g1f3');

    expect(arrows.length).toBe(3);
    expect(arrows.every((arrow) => arrow.kind === 'master')).toBeTrue();
  });

  it('ne trace que le coup du moteur hors théorie', () => {
    const arrows = buildArrows([], 'e2e4');

    expect(arrows.length).toBe(1);
    expect(arrows[0].kind).toBe('engine');
  });

  it('ne trace rien sans coup à proposer', () => {
    expect(buildArrows([], null)).toEqual([]);
  });

  // Sur la sicilienne, le cavalier et le pion vont tous deux en c3 : sans
  // écartement, la seconde pastille masquerait la première.
  it('écarte les pastilles de deux coups visant la même case', () => {
    const arrows = buildArrows([{ uci: 'b1c3' }, { uci: 'c2c3' }], null);

    const [knight, pawn] = arrows;
    expect(knight.target.y).toBe(squareCenter('c3').y);
    expect(pawn.target.y).toBe(squareCenter('c3').y);
    expect(knight.target.x).toBeLessThan(squareCenter('c3').x);
    expect(pawn.target.x).toBeGreaterThan(squareCenter('c3').x);
    // Écartées d'au moins un diamètre de pastille, elles ne se recouvrent plus.
    expect(pawn.target.x - knight.target.x).toBeGreaterThanOrEqual(0.44);
  });

  it('laisse les pastilles centrées quand les cases diffèrent', () => {
    const arrows = buildArrows([{ uci: 'g1f3' }, { uci: 'b1c3' }], null);

    expect(arrows[0].target).toEqual(squareCenter('f3'));
    expect(arrows[1].target).toEqual(squareCenter('c3'));
  });
});
