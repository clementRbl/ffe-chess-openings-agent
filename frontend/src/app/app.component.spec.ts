import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { AppComponent } from './app.component';
import { VideoResult } from './models/agent.models';

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
      providers: [provideHttpClient()],
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

describe('AppComponent — lisibilité des recommandations', () => {
  let component: AppComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient()],
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

  it('exprime l’évaluation en pions, signe compris', () => {
    withEvaluation('cp', 36);
    expect(component.evaluationText).toBe('+0.36');

    withEvaluation('cp', -120);
    expect(component.evaluationText).toBe('-1.20');
  });

  it('annonce un mat sans signe négatif', () => {
    withEvaluation('mate', -3);
    expect(component.evaluationText).toBe('Mat en 3');
  });

  it('traduit l’évaluation en langage courant', () => {
    withEvaluation('cp', 20);
    expect(component.evaluationHint).toBe('La position est équilibrée.');

    withEvaluation('cp', 90);
    expect(component.evaluationHint).toBe('Léger avantage pour les Blancs.');

    withEvaluation('cp', -400);
    expect(component.evaluationHint).toBe('Position gagnante pour les Noirs.');
  });

  it('affiche un tiret quand l’évaluation est indisponible', () => {
    component.analysis = null;
    expect(component.evaluationText).toBe('—');
    expect(component.evaluationHint).toBe('');
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
