import { AfterViewInit, Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { NgxChessBoardModule, NgxChessBoardView } from 'ngx-chess-board';

import { AgentService } from './services/agent.service';
import { TourService } from './services/tour.service';
import { AgentAnalysis, VideoResult } from './models/agent.models';
import { formatUciMove, toFrenchSan } from './chess-notation';
import { buildArrows, MoveArrow } from './board-arrows';

// Position de départ standard au format FEN.
const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// Écart, en pions, en deçà duquel la position est tenue pour équilibrée. Un
// demi-pion est la convention usuelle : en dessous, l'avantage annoncé par le
// moteur ne se traduit par aucun plan concret sur l'échiquier.
const BALANCE_THRESHOLD = 0.5;

// Composant racine : affiche l'échiquier interactif et le panneau de
// recommandations de l'agent. À chaque coup joué, la position (FEN) est
// synchronisée avec l'agent via l'API backend.
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, NgxChessBoardModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent implements AfterViewInit {
  @ViewChild('board') board!: NgxChessBoardView;

  analysis: AgentAnalysis | null = null;
  loading = false;
  error: string | null = null;
  currentFen = START_FEN;

  // Couleurs de l'échiquier, accordées à la palette de l'interface. Elles sont
  // passées en entrées du composant plutôt que définies en CSS, la librairie
  // peignant les cases elle-même.
  readonly boardLightTile = '#efe6d4';
  readonly boardDarkTile = '#a98a63';
  readonly boardHighlight = 'rgba(196, 150, 46, 0.45)';
  readonly boardLegalMove = 'rgba(20, 98, 74, 0.65)';

  /** Vidéo en cours de lecture, ou ``null`` si aucune n'a été demandée. */
  activeVideo: VideoResult | null = null;
  /** Section « détails techniques », repliée par défaut. */
  technicalOpen = false;
  /** Affichage des flèches de recommandation sur le plateau. */
  showArrows = true;
  /** Rang de la flèche mise en avant au survol de la liste, ou ``null``. */
  highlightedRank: number | null = null;

  // Flèches superposées au plateau. Calculées à l'arrivée de l'analyse plutôt
  // que lues depuis un accesseur : le template les parcourt à chaque cycle de
  // détection de changement, et il serait inutile de retracer les mêmes
  // chemins à chaque fois.
  arrows: MoveArrow[] = [];

  // Nombre de coups joués depuis la position de départ. Compté ici plutôt que
  // lu sur le plateau : le bouton d'annulation est évalué dès le premier rendu,
  // avant que la vue de l'échiquier ne soit disponible.
  private movesPlayed = 0;

  // URL d'intégration de la vidéo active, calculée une seule fois. La conserver
  // ici est indispensable : appeler le sanitiseur depuis le template
  // renverrait un nouvel objet à chaque cycle de détection de changement, ce
  // qui réécrirait l'attribut src de l'iframe et relancerait la vidéo au
  // moindre clic dans la page.
  private activeVideoUrl: SafeResourceUrl | null = null;

  constructor(
    private readonly agentService: AgentService,
    private readonly sanitizer: DomSanitizer,
    private readonly tour: TourService,
  ) {}

  ngAfterViewInit(): void {
    // Analyse la position initiale (différée pour éviter une erreur de
    // détection de changement pendant l'initialisation de la vue).
    setTimeout(() => this.runAnalysis(this.board.getFEN()), 0);
  }

  /** Déclenché à chaque coup joué sur l'échiquier. */
  onMove(event: { fen: string }): void {
    this.movesPlayed += 1;
    this.runAnalysis(event.fen);
  }

  /** Vrai s'il reste au moins un coup à annuler. */
  get canUndo(): boolean {
    return this.movesPlayed > 0;
  }

  /**
   * Annule le dernier coup joué.
   *
   * ``undo()`` modifie le plateau sans émettre d'événement de coup : c'est donc
   * à nous de relancer l'analyse, faute de quoi les conseils, le trait et la
   * vidéo resteraient ceux de la position abandonnée.
   */
  undo(): void {
    if (!this.canUndo) {
      return;
    }
    this.board.undo();
    this.movesPlayed -= 1;
    this.runAnalysis(this.board.getFEN());
  }

  /** Réinitialise l'échiquier à la position de départ et relance l'analyse. */
  reset(): void {
    this.board.reset();
    this.movesPlayed = 0;
    this.runAnalysis(this.board.getFEN());
  }

  /**
   * Vrai si c'est aux Blancs de jouer.
   *
   * L'information est déjà portée par le second champ de la FEN (« w » ou
   * « b ») : inutile d'interroger l'agent pour l'afficher.
   */
  get whiteToMove(): boolean {
    return this.currentFen.split(' ')[1] !== 'b';
  }

  /** Libellé du trait, affiché sous l'échiquier. */
  get turnLabel(): string {
    return this.whiteToMove ? 'Aux Blancs de jouer' : 'Aux Noirs de jouer';
  }

  /**
   * Vrai tant qu'aucun coup n'a été joué.
   *
   * La comparaison porte sur la disposition des pièces, premier champ de la
   * FEN : aucune suite de coups légaux ne permet d'y revenir, les pions ne
   * reculant pas. C'est donc un test exact, et non un simple compteur.
   */
  get isStartPosition(): boolean {
    return this.currentFen.split(' ')[0] === START_FEN.split(' ')[0];
  }

  /** URL d'intégration de la vidéo active (référence stable). */
  get videoUrl(): SafeResourceUrl | null {
    return this.activeVideoUrl;
  }

  /** Lance la lecture d'une vidéo dans la page. */
  playVideo(video: VideoResult): void {
    this.activeVideo = video;
    this.activeVideoUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
      video.embed_url,
    );
  }

  /** Ferme le lecteur et revient à la liste des vignettes. */
  closeVideo(): void {
    this.activeVideo = null;
    this.activeVideoUrl = null;
  }

  /** Ouvre ou replie la section des détails techniques. */
  toggleTechnical(): void {
    this.technicalOpen = !this.technicalOpen;
  }

  /** Affiche ou masque les flèches de recommandation sur le plateau. */
  toggleArrows(): void {
    this.showArrows = !this.showArrows;
    this.highlightedRank = null;
  }

  /**
   * Met une flèche en avant, les autres s'estompant.
   *
   * Le survol d'un coup dans la liste répond à la question « lequel est-ce sur
   * le plateau ? » sans qu'il faille compter les pastilles.
   */
  highlight(rank: number | null): void {
    // Seuls les premiers coups sont tracés : survoler les suivants ne doit pas
    // estomper toutes les flèches au profit d'une flèche inexistante.
    const drawn = rank !== null && this.arrows.some((a) => a.rank === rank);
    this.highlightedRank = drawn ? rank : null;
  }

  /**
   * État d'affichage d'une flèche.
   *
   * Les quatre états s'excluent, et l'opacité de chacun est fixée en CSS par
   * un sélecteur d'attribut : c'est ce qui garantit qu'une flèche survolée
   * repasse au premier plan, quel que soit son rang.
   */
  arrowState(arrow: MoveArrow): 'primary' | 'secondary' | 'pinned' | 'dimmed' {
    if (this.highlightedRank !== null) {
      return this.highlightedRank === arrow.rank ? 'pinned' : 'dimmed';
    }
    // Au repos, le coup le plus joué et celui du moteur priment sur les autres.
    return arrow.rank === 1 || arrow.kind === 'engine' ? 'primary' : 'secondary';
  }

  /** Relance la visite guidée de l'interface. */
  startTour(): void {
    this.tour.start();
  }

  /**
   * Évaluation du moteur exprimée en pions, ou annonce de mat.
   *
   * Le nombre est formaté à la française (virgule décimale) et porte toujours
   * son signe : c'est lui qui désigne le camp avantagé.
   */
  get evaluationText(): string {
    const evaluation = this.analysis?.evaluation;
    if (!evaluation) {
      return '—';
    }
    if (evaluation.type === 'mate') {
      return `Mat en ${Math.abs(evaluation.value)}`;
    }
    return (evaluation.value / 100).toLocaleString('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: 'exceptZero',
    });
  }

  /**
   * Camp que l'évaluation désigne comme avantagé.
   *
   * Sert à colorer le nombre et à choisir la pastille : le signe seul ne dit
   * pas à un débutant qui, des Blancs ou des Noirs, est devant.
   */
  get evaluationLeader(): 'white' | 'black' | 'balanced' {
    const evaluation = this.analysis?.evaluation;
    if (!evaluation) {
      return 'balanced';
    }
    if (evaluation.type === 'mate') {
      return evaluation.value > 0 ? 'white' : 'black';
    }
    const pawns = evaluation.value / 100;
    if (Math.abs(pawns) < BALANCE_THRESHOLD) {
      return 'balanced';
    }
    return pawns > 0 ? 'white' : 'black';
  }

  /**
   * Libellé de la pastille accompagnant le nombre.
   *
   * Elle nomme le camp que le signe désigne : c'est ce qui rend le code
   * couleur lisible sans avoir à le mémoriser.
   */
  get evaluationLeaderLabel(): string {
    switch (this.evaluationLeader) {
      case 'white':
        return 'Blancs';
      case 'black':
        return 'Noirs';
      default:
        return 'Équilibre';
    }
  }

  /**
   * Part de la barre d'évaluation revenant aux Blancs, en pourcentage.
   *
   * L'écart est borné à cinq pions : au-delà, la position est de toute façon
   * gagnée et la barre n'a plus rien à nuancer.
   */
  get evaluationShare(): number {
    const evaluation = this.analysis?.evaluation;
    if (!evaluation) {
      return 50;
    }
    if (evaluation.type === 'mate') {
      return evaluation.value > 0 ? 100 : 0;
    }
    const pawns = Math.max(-5, Math.min(5, evaluation.value / 100));
    return 50 + pawns * 10;
  }

  /** Traduction en langage courant de l'évaluation du moteur. */
  get evaluationHint(): string {
    const evaluation = this.analysis?.evaluation;
    if (!evaluation) {
      return '';
    }
    if (evaluation.type === 'mate') {
      const side = evaluation.value > 0 ? 'Les Blancs' : 'Les Noirs';
      return `${side} forcent le mat.`;
    }
    const pawns = evaluation.value / 100;
    const leader = pawns > 0 ? 'les Blancs' : 'les Noirs';
    const gap = Math.abs(pawns);
    if (gap < BALANCE_THRESHOLD) {
      // Sous un demi-pion, l'écart n'a pas de traduction concrète : mieux vaut
      // le dire que de laisser croire à un avantage.
      return 'Écart trop faible pour départager les deux camps.';
    }
    if (gap < 1.5) {
      return `Léger avantage pour ${leader}.`;
    }
    if (gap < 3) {
      return `Avantage net pour ${leader}.`;
    }
    return `Position gagnante pour ${leader}.`;
  }

  /**
   * Fiche dont proviennent les passages affichés.
   *
   * L'agent ne sert que des passages d'une même fiche ; la nommer permet au
   * lecteur de savoir sur quelle ouverture porte ce qu'il lit, y compris quand
   * la sienne n'est pas couverte par le corpus.
   */
  get contextSource(): string | null {
    return this.analysis?.context[0]?.title ?? null;
  }

  /** Nombre de parties de référence, formaté pour la lecture. */
  formatGames(total: number): string {
    return total.toLocaleString('fr-FR');
  }

  /** Coup de Lichess traduit en notation française (« Nf3 » → « Cf3 »). */
  frenchMove(san: string): string {
    return toFrenchSan(san);
  }

  /** Coup du moteur, exprimé en cases de départ et d'arrivée. */
  get bestMoveText(): string {
    const bestMove = this.analysis?.evaluation?.best_move;
    return bestMove ? formatUciMove(bestMove) : '';
  }

  /** Appelle l'agent pour analyser la position et met à jour l'affichage. */
  private runAnalysis(fen: string): void {
    this.currentFen = fen;
    this.loading = true;
    this.error = null;
    this.agentService.analyze(fen).subscribe({
      next: (analysis) => {
        this.analysis = analysis;
        this.arrows = buildArrows(
          analysis.theoretical_moves,
          analysis.evaluation?.best_move,
        );
        this.highlightedRank = null;
        this.syncActiveVideo(analysis.videos);
        this.loading = false;
        this.maybeStartTour();
      },
      error: (err) => {
        this.error =
          err?.error?.detail ?? "Erreur lors de l'analyse de la position.";
        this.arrows = [];
        this.loading = false;
      },
    });
  }

  /**
   * Conserve la vidéo en cours si elle est toujours proposée sur la nouvelle
   * position, sinon ferme le lecteur.
   *
   * On garde volontairement la même référence d'URL : la remplacer par un objet
   * équivalent suffirait à faire repartir la lecture depuis le début.
   */
  private syncActiveVideo(videos: VideoResult[]): void {
    const active = this.activeVideo;
    if (!active) {
      return;
    }
    const stillProposed = videos.some(
      (video) => video.video_id === active.video_id,
    );
    if (!stillProposed) {
      this.closeVideo();
    }
  }

  /** Déclenche la visite guidée au tout premier affichage des recommandations. */
  private maybeStartTour(): void {
    if (!this.tour.isFirstVisit) {
      return;
    }
    // Laisse Angular peindre le panneau avant de pointer ses éléments.
    setTimeout(() => this.tour.start(), 400);
  }
}
