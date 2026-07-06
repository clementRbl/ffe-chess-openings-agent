import { AfterViewInit, Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { NgxChessBoardModule, NgxChessBoardView } from 'ngx-chess-board';

import { AgentService } from './services/agent.service';
import { AgentAnalysis } from './models/agent.models';

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

  constructor(
    private readonly agentService: AgentService,
    private readonly sanitizer: DomSanitizer,
  ) {}

  /** Marque une URL d'intégration YouTube comme sûre pour un iframe. */
  embedUrl(url: string): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

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

  /** Représentation lisible de l'évaluation moteur (pions ou mat). */
  get evaluationText(): string {
    const evaluation = this.analysis?.evaluation;
    if (!evaluation) {
      return '—';
    }
    if (evaluation.type === 'mate') {
      return `Mat en ${evaluation.value}`;
    }
    const pawns = (evaluation.value / 100).toFixed(2);
    return evaluation.value > 0 ? `+${pawns}` : pawns;
  }

  /** Appelle l'agent pour analyser la position et met à jour l'affichage. */
  private runAnalysis(fen: string): void {
    this.currentFen = fen;
    this.loading = true;
    this.error = null;
    this.agentService.analyze(fen).subscribe({
      next: (analysis) => {
        this.analysis = analysis;
        this.loading = false;
      },
      error: (err) => {
        this.error =
          err?.error?.detail ?? "Erreur lors de l'analyse de la position.";
        this.loading = false;
      },
    });
  }
}
