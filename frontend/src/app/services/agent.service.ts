import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AgentAnalysis } from '../models/agent.models';

// Service Angular chargé de communiquer avec l'API backend. Il expose l'analyse
// d'une position (FEN) par l'agent. L'URL de base est relative (/api) : nginx
// se charge de la rediriger vers le backend, ce qui évite tout problème de CORS.
@Injectable({ providedIn: 'root' })
export class AgentService {
  private readonly baseUrl = '/api/v1';

  constructor(private readonly http: HttpClient) {}

  /** Analyse une position au format FEN et renvoie la recommandation de l'agent. */
  analyze(fen: string): Observable<AgentAnalysis> {
    const params = new HttpParams().set('fen', fen);
    return this.http.get<AgentAnalysis>(`${this.baseUrl}/analyze`, { params });
  }
}
