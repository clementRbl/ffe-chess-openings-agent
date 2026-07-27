import { formatUciMove, toFrenchSan } from './chess-notation';

describe('Notation française des coups', () => {
  it('traduit l’initiale des pièces', () => {
    expect(toFrenchSan('Nf3')).toBe('Cf3');
    expect(toFrenchSan('Bc4')).toBe('Fc4');
    expect(toFrenchSan('Ra1')).toBe('Ta1');
    expect(toFrenchSan('Qd8')).toBe('Dd8');
    expect(toFrenchSan('Ke2')).toBe('Re2');
  });

  it('conserve les prises, échecs et mats', () => {
    expect(toFrenchSan('Bxc6+')).toBe('Fxc6+');
    expect(toFrenchSan('Qh4#')).toBe('Dh4#');
    expect(toFrenchSan('Nbd7')).toBe('Cbd7');
  });

  it('traduit la pièce de promotion', () => {
    expect(toFrenchSan('e8=Q')).toBe('e8=D');
  });

  it('laisse intacts les coups de pion et les roques', () => {
    expect(toFrenchSan('c5')).toBe('c5');
    // « b » minuscule est la colonne b, pas le fou.
    expect(toFrenchSan('bxc6')).toBe('bxc6');
    expect(toFrenchSan('O-O')).toBe('O-O');
    expect(toFrenchSan('O-O-O')).toBe('O-O-O');
  });
});

describe('Coup du moteur en notation UCI', () => {
  it('sépare la case de départ et la case d’arrivée', () => {
    expect(formatUciMove('g1f3')).toBe('g1 → f3');
    expect(formatUciMove('e2e4')).toBe('e2 → e4');
  });

  it('indique la pièce obtenue lors d’une promotion', () => {
    expect(formatUciMove('e7e8q')).toBe('e7 → e8=D');
  });
});
