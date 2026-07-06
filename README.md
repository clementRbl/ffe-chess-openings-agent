# Agent IA – Apprentissage des ouvertures aux échecs (FFE)

Proof of Concept (POC) d'un **agent intelligent** accompagnant les jeunes espoirs
de la **Fédération Française des Échecs** dans l'apprentissage des **ouvertures**.

L'agent, pour une position donnée (identifiant **FEN**), guide l'utilisateur en
combinant plusieurs sources :

- les **coups théoriques** issus de la théorie (API **Lichess**) ;
- une **évaluation moteur** (**Stockfish**) lorsque la partie sort de la théorie ;
- du **contexte d'ouverture** via une recherche vectorielle (**Milvus** + Wikichess) ;
- des **vidéos explicatives** pertinentes (**YouTube Data v3**).

Le tout est orchestré par un agent **LangGraph** et exposé via une API
**FastAPI**, avec une interface **Angular** (échiquier interactif).

> Stack cible : **LangGraph · FastAPI · Milvus · MongoDB · Angular**, exécution
> locale via **Docker Compose**.

## Structure du projet

```
.
├── backend/            # API FastAPI + agent (Python)
│   └── app/
│       ├── api/        # Routes HTTP (versionnées : /api/v1)
│       ├── core/       # Configuration (variables d'environnement)
│       └── main.py     # Point d'entrée de l'application
├── frontend/           # Interface Angular (à venir – Étape 5)
├── docker-compose.yml  # Orchestration des services
├── .env.example        # Modèle de configuration
└── CONSIGNES.md        # Document de référence de la mission
```

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose
- (Développement local hors Docker) Python 3.12+ et [uv](https://docs.astral.sh/uv/)

## Démarrage rapide

```bash
# 1. Copier le modèle de configuration
cp .env.example .env

# 2. Lancer les services
docker compose up --build
```

L'API est alors disponible sur http://localhost:8000.

### Vérifier que le backend fonctionne

```bash
curl http://localhost:8000/api/v1/healthcheck
# -> {"status":"ok"}
```

La documentation interactive (Swagger) est accessible sur
http://localhost:8000/docs.

## Endpoints de l'API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/healthcheck` | Sonde de disponibilité du service |
| `GET` | `/api/v1/moves/{fen}` | Coups théoriques pour une position (Lichess opening explorer) |
| `GET` | `/api/v1/evaluate/{fen}` | Évaluation Stockfish de la position (centipions ou mat) |
| `GET` | `/api/v1/vector-search?query=...` | Passages Wikichess pertinents sur une ouverture (RAG Milvus via LangGraph) |
| `GET` | `/api/v1/videos/{opening}` | Vidéos YouTube explicatives sur une ouverture (via LangGraph) |

> Le paramètre `{fen}` contient des `/` et des espaces : les espaces doivent être
> encodés (`%20`). Exemple pour la position de départ :
> `/api/v1/evaluate/rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201`.
> Une position FEN invalide renvoie une erreur `400`.

## Base vectorielle (RAG Wikichess → Milvus)

Un petit corpus d'articles d'ouvertures (en français, dossier
[backend/data/wikichess/](backend/data/wikichess/)) est découpé en passages,
encodé avec le modèle d'embedding **Qwen3-Embedding-0.6B**
(`sentence-transformers`) puis indexé dans **Milvus**. La recherche est
orchestrée par un workflow **LangGraph** (encodage de la requête → recherche
vectorielle).

Après le premier démarrage, chargez les données dans Milvus (le modèle
d'embedding, ~1,2 Go, est téléchargé au premier lancement) :

```bash
docker compose exec backend uv run python -m app.scripts.ingest
```

Puis interrogez la base :

```bash
curl "http://localhost:8000/api/v1/vector-search?query=defense%20sicilienne&top_k=2"
```

## Configuration

Toute la configuration passe par des **variables d'environnement** (fichier
`.env`, voir `.env.example`).

| Variable        | Description                                              | Défaut |
|-----------------|---------------------------------------------------------|--------|
| `BACKEND_PORT`    | Port exposé par l'API FastAPI                          | `8000` |
| `LICHESS_TOKEN`   | Token personnel Lichess pour l'opening explorer (requis pour `/moves`) | *(vide)* |
| `YOUTUBE_API_KEY` | Clé API YouTube Data v3 (requise pour `/videos`)       | *(vide)* |

> **Token Lichess :** l'opening explorer requiert désormais une authentification.
> Générez un token gratuit (sans scope) sur
> https://lichess.org/account/oauth/token et renseignez `LICHESS_TOKEN` dans
> `.env`. Sans token, `/api/v1/moves/{fen}` renvoie une erreur `502` explicite.
>
> **Clé YouTube :** créez une clé API dans la console Google Cloud (activez
> « YouTube Data API v3 ») et renseignez `YOUTUBE_API_KEY` dans `.env`. Sans
> clé, `/api/v1/videos/{opening}` renvoie une erreur `503` explicite.

## Avancement (étapes de la mission)

- [x] **Étape 1** – Structure du projet, dépôt Git, `docker-compose` (healthcheck FastAPI)
- [x] **Étape 2** – Endpoints Lichess (coups théoriques) + Stockfish (évaluation)
- [x] **Étape 3** – RAG Wikichess → Milvus (recherche vectorielle) orchestré par LangGraph
- [x] **Étape 4** – Recherche de vidéos YouTube (API Data v3) orchestrée par LangGraph
- [ ] **Étape 5** – Interface Angular (ngx-chessboard)
- [ ] **Étape 6** – Containerisation complète + démonstration
- [ ] **Étape 7** – Note système d'analyse vidéo (MCP) : bénéfices, limites, faisabilité
