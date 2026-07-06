// Interfaces TypeScript reflétant les réponses de l'API de l'agent (endpoint
// /api/v1/analyze). Elles décrivent la recommandation complète : coups
// théoriques, évaluation moteur, contexte, vidéos et état des sources.

export interface TheoreticalMove {
  uci: string;
  san: string;
  white: number;
  draws: number;
  black: number;
  total: number;
}

export interface Evaluation {
  fen: string;
  type: string;
  value: number;
  best_move: string | null;
}

export interface RetrievedChunk {
  title: string | null;
  text: string;
  score: number;
}

export interface VideoResult {
  video_id: string;
  title: string;
  channel: string;
  url: string;
  embed_url: string;
  thumbnail: string | null;
  published_at: string | null;
}

export interface SourceStatus {
  ok: boolean;
  detail: string | null;
}

export interface AgentAnalysis {
  fen: string;
  opening: string | null;
  in_theory: boolean;
  theoretical_moves: TheoreticalMove[];
  evaluation: Evaluation | null;
  context: RetrievedChunk[];
  videos: VideoResult[];
  summary: string;
  sources: Record<string, SourceStatus>;
}
