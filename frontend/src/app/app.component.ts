import { AfterViewInit, Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { NgxChessBoardModule, NgxChessBoardView } from 'ngx-chess-board';

import { AgentService } from './services/agent.service';
import { TourService } from './services/tour.service';
import { AgentAnalysis, VideoResult } from './models/agent.models';

// Position de départ standard au format FEN.
const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

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

  /** Vidéo en cours de lecture, ou ``null`` si aucune n'a été demandée. */
  activeVideo: VideoResult | null = null;
  /** Section « détails techniques », repliée par défaut. */
  technicalOpen = false;

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
    this.runAnalysis(event.fen);
  }

  /** Réinitialise l'échiquier à la position de départ et relance l'analyse. */
  reset(): void {
    this.board.reset();
    this.runAnalysis(this.board.getFEN());
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

  /** Relance la visite guidée de l'interface. */
  startTour(): void {
    this.tour.start();
  }

  /** Évaluation du moteur exprimée en pions, ou annonce de mat. */
  get evaluationText(): string {
    const evaluation = this.analysis?.evaluation;
    if (!evaluation) {
      return '—';
    }
    if (evaluation.type === 'mate') {
      return `Mat en ${Math.abs(evaluation.value)}`;
    }
    const pawns = (evaluation.value / 100).toFixed(2);
    return evaluation.value > 0 ? `+${pawns}` : pawns;
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
    if (gap < 0.5) {
      return 'La position est équilibrée.';
    }
    if (gap < 1.5) {
      return `Léger avantage pour ${leader}.`;
    }
    if (gap < 3) {
      return `Avantage net pour ${leader}.`;
    }
    return `Position gagnante pour ${leader}.`;
  }

  /** Nombre de parties de référence, formaté pour la lecture. */
  formatGames(total: number): string {
    return total.toLocaleString('fr-FR');
  }

  /** Appelle l'agent pour analyser la position et met à jour l'affichage. */
  private runAnalysis(fen: string): void {
    this.currentFen = fen;
    this.loading = true;
    this.error = null;
    this.agentService.analyze(fen).subscribe({
      next: (analysis) => {
        this.analysis = analysis;
        this.syncActiveVideo(analysis.videos);
        this.loading = false;
        this.maybeStartTour();
      },
      error: (err) => {
        this.error =
          err?.error?.detail ?? "Erreur lors de l'analyse de la position.";
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
