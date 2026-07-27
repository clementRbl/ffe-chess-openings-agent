import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { AppComponent } from './app.component';
import { VideoResult } from './models/agent.models';
import { buildArrows } from './board-arrows';

// Deux vidéos factices, suffisantes pour les cas testés ici.
const VIDEO_A: VideoResult = {
  video_id: 'aaa111',
  title: 'La sicilienne expliquée',
  channel: 'Chess FR',
  url: 'https://www.youtube.com/watch?v=aaa111',
  embed_url: 'https://www.youtube.com/embed/aaa111',
  thumbnail: 'https://img.youtube.com/vi/aaa111/mqdefault.jpg',
  published_at: null,
};

const VIDEO_B: VideoResult = { ...VIDEO_A, video_id: 'bbb222', title: 'Autre vidéo' };

describe('AppComponent — lecteur vidéo', () => {
  let component: AppComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    component = TestBed.createComponent(AppComponent).componentInstance;
  });

  it('ne charge aucune vidéo tant que l’utilisateur n’en a pas demandé une', () => {
    expect(component.activeVideo).toBeNull();
    expect(component.videoUrl).toBeNull();
  });

  it('expose une URL après un clic sur une vignette', () => {
    component.playVideo(VIDEO_A);

    expect(component.activeVideo).toBe(VIDEO_A);
    expect(component.videoUrl).not.toBeNull();
  });

  // Régression : l'URL était auparavant produite par un appel de méthode dans le
  // template. Le sanitiseur renvoyant un nouvel objet à chaque appel, Angular
  // croyait la valeur modifiée à chaque cycle de détection de changement,
  // réécrivait l'attribut src de l'iframe et relançait donc la vidéo au moindre
  // clic dans la page.
  it('renvoie toujours la même référence d’URL pour une vidéo donnée', () => {
    component.playVideo(VIDEO_A);
    const first = component.videoUrl;

    expect(component.videoUrl).toBe(first);
    expect(component.videoUrl).toBe(first);
  });

  it('conserve la lecture si la vidéo est encore proposée après un coup joué', () => {
    component.playVideo(VIDEO_A);
    const before = component.videoUrl;

    component['syncActiveVideo']([VIDEO_A, VIDEO_B]);

    expect(component.activeVideo).toBe(VIDEO_A);
    expect(component.videoUrl).toBe(before);
  });

  it('ferme le lecteur si la vidéo n’est plus proposée', () => {
    component.playVideo(VIDEO_A);

    component['syncActiveVideo']([VIDEO_B]);

    expect(component.activeVideo).toBeNull();
    expect(component.videoUrl).toBeNull();
  });

  it('ferme le lecteur à la demande', () => {
    component.playVideo(VIDEO_A);
    component.closeVideo();

    expect(component.activeVideo).toBeNull();
    expect(component.videoUrl).toBeNull();
  });
});

describe('AppComponent — annulation des coups', () => {
  let component: AppComponent;
  let undoCalls: number;
  let boardFen: string;

  const AFTER_E4 =
    'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
  const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    component = TestBed.createComponent(AppComponent).componentInstance;

    // Doublure du plateau : on ne teste pas la librairie d'échiquier, mais la
    // synchronisation de l'application avec elle.
    undoCalls = 0;
    boardFen = START;
    component.board = {
      undo: () => {
        undoCalls += 1;
        boardFen = START;
      },
      reset: () => {
        boardFen = START;
      },
      getFEN: () => boardFen,
    } as never;
  });

  it('n’a rien à annuler sur la position de départ', () => {
    expect(component.canUndo).toBeFalse();

    component.undo();

    expect(undoCalls).toBe(0);
  });

  it('permet d’annuler dès qu’un coup a été joué', () => {
    component.onMove({ fen: AFTER_E4 });

    expect(component.canUndo).toBeTrue();
  });

  it('annule le coup et resynchronise la position analysée', () => {
    component.onMove({ fen: AFTER_E4 });
    expect(component.currentFen).toBe(AFTER_E4);

    component.undo();

    expect(undoCalls).toBe(1);
    expect(component.currentFen).toBe(START);
    expect(component.canUndo).toBeFalse();
    // Le trait suit la position restaurée.
    expect(component.turnLabel).toBe('Aux Blancs de jouer');
  });

  it('redevient inactif après une réinitialisation', () => {
    component.onMove({ fen: AFTER_E4 });
    component.reset();

    expect(component.canUndo).toBeFalse();
  });
});

describe('AppComponent — flèches sur le plateau', () => {
  let component: AppComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    component = TestBed.createComponent(AppComponent).componentInstance;
    component.arrows = buildArrows(
      [{ uci: 'g1f3' }, { uci: 'b1c3' }, { uci: 'c2c3' }],
      'd2d4',
    );
  });

  it('met en avant le coup le plus joué et celui du moteur au repos', () => {
    const states = component.arrows.map((arrow) => component.arrowState(arrow));

    expect(states).toEqual(['primary', 'secondary', 'secondary', 'primary']);
  });

  // Régression : la règle d'opacité des rangs suivants l'emportait sur celle de
  // l'estompage, si bien que le survol ne mettait rien en avant.
  it('isole la flèche survolée et efface toutes les autres', () => {
    component.highlight(2);

    const states = component.arrows.map((arrow) => component.arrowState(arrow));

    expect(states).toEqual(['dimmed', 'pinned', 'dimmed', 'dimmed']);
  });

  it('ignore le survol d’un coup qui n’a pas de flèche', () => {
    component.highlight(5);

    expect(component.highlightedRank).toBeNull();
  });

  it('coupe l’affichage et relâche la mise en avant', () => {
    component.highlight(1);
    component.toggleArrows();

    expect(component.showArrows).toBeFalse();
    expect(component.highlightedRank).toBeNull();
  });
});

describe('AppComponent — lisibilité des recommandations', () => {
  let component: AppComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    component = TestBed.createComponent(AppComponent).componentInstance;
  });

  function withEvaluation(type: string, value: number): void {
    component.analysis = {
      fen: '',
      opening: null,
      in_theory: false,
      theoretical_moves: [],
      evaluation: { fen: '', type, value, best_move: 'e2e4' },
      context: [],
      videos: [],
      summary: '',
      sources: {},
    };
  }

  it('exprime l’évaluation en pions, signe compris et virgule française', () => {
    withEvaluation('cp', 36);
    expect(component.evaluationText).toBe('+0,36');

    withEvaluation('cp', -120);
    expect(component.evaluationText).toBe('-1,20');
  });

  it('n’affiche pas de signe sur une position strictement égale', () => {
    withEvaluation('cp', 0);
    expect(component.evaluationText).toBe('0,00');
  });

  it('annonce un mat sans signe négatif', () => {
    withEvaluation('mate', -3);
    expect(component.evaluationText).toBe('Mat en 3');
  });

  it('traduit l’évaluation en langage courant', () => {
    withEvaluation('cp', 20);
    expect(component.evaluationHint).toBe(
      'Écart trop faible pour départager les deux camps.',
    );

    withEvaluation('cp', 90);
    expect(component.evaluationHint).toBe('Léger avantage pour les Blancs.');

    withEvaluation('cp', -400);
    expect(component.evaluationHint).toBe('Position gagnante pour les Noirs.');
  });

  // Le signe seul ne dit pas à un débutant qui mène : la carte nomme le camp.
  it('nomme le camp avantagé, et personne sous un demi-pion', () => {
    withEvaluation('cp', 31);
    expect(component.evaluationLeader).toBe('balanced');
    expect(component.evaluationLeaderLabel).toBe('Équilibre');

    withEvaluation('cp', 120);
    expect(component.evaluationLeader).toBe('white');
    expect(component.evaluationLeaderLabel).toBe('Blancs');

    withEvaluation('cp', -50);
    expect(component.evaluationLeader).toBe('black');
    expect(component.evaluationLeaderLabel).toBe('Noirs');
  });

  it('désigne le camp qui mate, quelle que soit la distance au mat', () => {
    withEvaluation('mate', 2);
    expect(component.evaluationLeader).toBe('white');

    withEvaluation('mate', -2);
    expect(component.evaluationLeader).toBe('black');
  });

  it('affiche un tiret quand l’évaluation est indisponible', () => {
    component.analysis = null;
    expect(component.evaluationText).toBe('—');
    expect(component.evaluationHint).toBe('');
  });

  // Lichess ne nomme aucune ouverture sur la position de départ, faute de coup
  // joué : l'écran doit inviter à commencer, pas annoncer un échec
  // d'identification.
  it('distingue la position de départ d’une ouverture inconnue', () => {
    expect(component.isStartPosition).toBeTrue();

    component.currentFen =
      'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
    expect(component.isStartPosition).toBeFalse();
  });

  it('lit le trait dans la FEN', () => {
    component.currentFen =
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    expect(component.whiteToMove).toBeTrue();
    expect(component.turnLabel).toBe('Aux Blancs de jouer');

    component.currentFen =
      'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
    expect(component.whiteToMove).toBeFalse();
    expect(component.turnLabel).toBe('Aux Noirs de jouer');
  });

  it('place le curseur de la barre au centre à l’équilibre', () => {
    withEvaluation('cp', 0);
    expect(component.evaluationShare).toBe(50);

    component.analysis = null;
    expect(component.evaluationShare).toBe(50);
  });

  it('fait pencher la barre du côté de celui qui mène', () => {
    withEvaluation('cp', 200);
    expect(component.evaluationShare).toBe(70);

    withEvaluation('cp', -200);
    expect(component.evaluationShare).toBe(30);
  });

  it('borne la barre à cinq pions et l’envoie à fond sur un mat', () => {
    withEvaluation('cp', 5000);
    expect(component.evaluationShare).toBe(100);

    withEvaluation('mate', -2);
    expect(component.evaluationShare).toBe(0);
  });
});
