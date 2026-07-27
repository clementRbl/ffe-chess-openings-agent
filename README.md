# Agent IA – Apprentissage des ouvertures aux échecs (FFE)

Proof of Concept (POC) d'un **agent intelligent** accompagnant les jeunes espoirs
de la **Fédération Française des Échecs** dans l'apprentissage des **ouvertures**.

L'agent, pour une position donnée (identifiant **FEN**), guide l'utilisateur en
combinant plusieurs sources :

- les **coups théoriques** issus de la théorie (API **Lichess**) ;
- une **évaluation moteur** (**Stockfish**) lorsque la partie sort de la théorie ;
- du **contexte d'ouverture** via une recherche vectorielle (**Milvus** + Wikichess) ;
- des **vidéos explicatives** pertinentes (**YouTube Data v3**).

Les réponses des API externes sont mises en cache dans **MongoDB**, qui conserve
également l'historique des analyses produites par l'agent.

Le tout est orchestré par un agent **LangGraph** et exposé via une API
**FastAPI**, avec une interface **Angular** (échiquier interactif).

> Stack cible : **LangGraph · FastAPI · Milvus · MongoDB · Angular**, exécution
> locale via **Docker Compose**.

## Structure du projet

```
.
├── backend/                # API FastAPI + agent (Python)
│   ├── app/
│   │   ├── api/v1/         # Routes HTTP (versionnées : /api/v1)
│   │   ├── core/           # Configuration (variables d'environnement)
│   │   ├── graph/          # Workflows LangGraph (agent, RAG, vidéos)
│   │   ├── schemas/        # Modèles Pydantic des réponses
│   │   ├── scripts/        # Ingestion du corpus dans Milvus
│   │   ├── services/       # Logique métier (Lichess, Stockfish, Milvus, YouTube, MongoDB)
│   │   └── main.py         # Point d'entrée de l'application
│   ├── data/wikichess/     # Corpus d'articles d'ouvertures
│   └── tests/              # Tests pytest (sans service externe)
├── frontend/               # Interface Angular (échiquier + panneau agent)
│   ├── src/app/            # Composant racine, service d'appel à l'API
│   └── projects/           # Librairie ngx-chess-board (source locale, cf. note)
├── docs/                   # Livrables documentaires (note MCP, autoévaluation)
├── docker-compose.yml      # Orchestration de tous les services
├── .env.example            # Modèle de configuration
└── CONSIGNES.md            # Document de référence de la mission
```

> **Note sur `frontend/projects/`** : la librairie `ngx-chess-board` est intégrée
> au dépôt sous forme de source locale (comme dans le
> [repo de référence OpenClassrooms](https://github.com/OpenClassrooms-Student-Center/material-chessboard)),
> car le paquet npm publié ne suit pas la version d'Angular utilisée ici. Elle
> est compilée avant l'application par le `Dockerfile` du frontend.

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose v2
- ~8 Go d'espace disque (images Docker + modèle d'embedding)
- (Développement local hors Docker) Python 3.12+ et [uv](https://docs.astral.sh/uv/)

## Installation et démarrage

Depuis une installation fraîche, trois commandes suffisent :

```bash
# 1. Récupérer le projet
git clone <url-du-depot> && cd federation-francaise-des-echecs

# 2. Copier le modèle de configuration (puis y renseigner les clés, cf. § Configuration)
cp .env.example .env

# 3. Construire et lancer l'ensemble des services
docker compose up --build -d
```

Le premier démarrage construit les images (backend Python + Stockfish, frontend
Angular compilé puis servi par nginx) et télécharge les images de MongoDB,
Milvus, etcd et MinIO : comptez une dizaine de minutes selon la connexion.

Vérifier que les six services tournent et sont sains :

```bash
docker compose ps
```

Puis charger le corpus Wikichess dans Milvus (**obligatoire au premier
démarrage**, voir § Base vectorielle) :

```bash
docker compose exec backend uv run python -m app.scripts.ingest
```

| Service | URL |
|---------|-----|
| Interface Angular | http://localhost:4200 |
| API FastAPI | http://localhost:8000 |
| Documentation interactive (Swagger) | http://localhost:8000/docs |

Arrêter les services (`-v` supprime en plus les volumes de données) :

```bash
docker compose down
```

### Vérification bout en bout

```bash
# 1. Le backend répond
curl http://localhost:8000/api/v1/healthcheck
# -> {"status":"ok"}

# 2. L'interface est servie
curl -I http://localhost:4200
# -> HTTP/1.1 200 OK

# 3. Les appels /api de l'interface atteignent bien le backend (proxy nginx)
curl http://localhost:4200/api/v1/healthcheck
# -> {"status":"ok"}

# 4. L'agent agrège ses sources sur une ouverture reconnue (ici la sicilienne)
curl -G "http://localhost:8000/api/v1/analyze" \
  --data-urlencode "fen=rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
```

Le champ `sources` de la réponse indique l'état de chaque source **effectivement
consultée** (`lichess`, `stockfish`, `milvus`, `youtube`, `mongo`) : c'est le
moyen le plus rapide de repérer une clé d'API manquante ou un service non
démarré.

> Sur une position dont Lichess ne nomme pas l'ouverture — la position de départ,
> par exemple, où aucun coup n'a encore été joué — l'agent va directement au
> résumé fondé sur le moteur : `milvus` et `youtube` sont alors absents de
> `sources`, puisqu'il n'y a pas de nom d'ouverture à rechercher. C'est le
> comportement attendu de l'aiguillage du graphe. Utilisez donc une position
> nommée (§ Positions de démonstration) pour vérifier les cinq sources.

### Persistance des données

Cinq volumes nommés conservent les données entre deux redémarrages (données
MongoDB et Milvus, métadonnées etcd et MinIO, cache du modèle d'embedding) :

```bash
docker volume ls | grep echecs   # mongo_data, milvus_data, etcd_data, minio_data, hf_cache
```

Pour vérifier que la persistance fonctionne, recréez les conteneurs sans
supprimer les volumes — l'historique des analyses et l'index Milvus sont
toujours là :

```bash
docker compose down && docker compose up -d
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.analyses.countDocuments()"
curl "http://localhost:8000/api/v1/vector-search?query=sicilienne&top_k=1"
```

## Endpoints de l'API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/healthcheck` | Sonde de disponibilité du service |
| `GET` | `/api/v1/moves/{fen}` | Coups théoriques pour une position (Lichess opening explorer) |
| `GET` | `/api/v1/evaluate/{fen}` | Évaluation Stockfish de la position (centipions ou mat) |
| `GET` | `/api/v1/vector-search?query=...` | Passages Wikichess pertinents sur une ouverture (RAG Milvus via LangGraph) |
| `GET` | `/api/v1/videos/{opening}` | Vidéos YouTube explicatives sur une ouverture (via LangGraph) |
| `GET` | `/api/v1/analyze?fen=...` | **Analyse complète de l'agent** : agrège coups, éval, contexte et vidéos (LangGraph, choix conditionnel de la source) |

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

## Cache et historique (MongoDB)

MongoDB remplit deux rôles dans le POC, dans la base `ffe_chess` :

| Collection | Rôle |
|------------|------|
| `api_cache` | Cache des réponses Lichess et YouTube, avec expiration automatique (index TTL, 24 h par défaut). L'interface analysant la position **à chaque coup joué**, ce cache évite d'épuiser le quota YouTube et de solliciter Lichess inutilement. |
| `analyses` | Historique des analyses rendues par l'agent (position, ouverture, coups retenus, évaluation, résumé). Utile pour la démonstration et comme jeu de positions annotées. |

Une panne de MongoDB **ne bloque pas** l'agent : l'analyse se poursuit sans cache
et l'état de la source est signalé dans le champ `sources` de la réponse.

Inspecter le contenu de la base :

```bash
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.analyses.find().sort({created_at:-1}).limit(3)"
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.api_cache.countDocuments()"
```

## Positions de démonstration

Ces positions se jouent directement sur l'échiquier de l'interface (les coups
sont indiqués) ou s'interrogent en ligne de commande via `/analyze`. Elles
couvrent les deux chemins du graphe de l'agent.

| Position | Coups à jouer | Ce qu'elle démontre |
|----------|---------------|---------------------|
| Position de départ | — | Théorie très fournie : les coups les plus joués par les maîtres |
| Défense sicilienne | 1.e4 c5 | Ouverture reconnue → contexte Wikichess + vidéos explicatives |
| Partie italienne | 1.e4 e5 2.Cf3 Cc6 3.Fc4 | Ouverture classique enseignée aux jeunes joueurs |
| Gambit dame | 1.d4 d5 2.c4 | Ouverture fermée, contraste avec les ouvertures ouvertes |
| Hors théorie | 1.f3 e5 2.g4 | Position quittant les sentiers battus → bascule sur Stockfish, qui annonce la sanction (mat par 2…Dh4#) |

FEN correspondantes, pour un appel direct à l'API :

```bash
BASE="http://localhost:8000/api/v1/analyze"

# Défense sicilienne (1.e4 c5)
curl -G "$BASE" --data-urlencode "fen=rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"

# Partie italienne (1.e4 e5 2.Cf3 Cc6 3.Fc4)
curl -G "$BASE" --data-urlencode "fen=r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"

# Gambit dame (1.d4 d5 2.c4)
curl -G "$BASE" --data-urlencode "fen=rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2"

# Hors théorie (1.f3 e5 2.g4)
curl -G "$BASE" --data-urlencode "fen=rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2"
```

## Tests

```bash
cd backend && uv run pytest
```

Les tests s'exécutent sans aucun service externe : Lichess, Stockfish, Milvus,
YouTube et MongoDB sont remplacés par des doublures.

## Configuration

Toute la configuration passe par des **variables d'environnement** (fichier
`.env`, voir `.env.example`).

| Variable        | Description                                              | Défaut |
|-----------------|---------------------------------------------------------|--------|
| `BACKEND_PORT`    | Port exposé par l'API FastAPI                          | `8000` |
| `FRONTEND_PORT`   | Port exposé par l'interface Angular (nginx)            | `4200` |
| `LICHESS_TOKEN`   | Token personnel Lichess pour l'opening explorer (requis pour `/moves`) | *(vide)* |
| `YOUTUBE_API_KEY` | Clé API YouTube Data v3 (requise pour `/videos`)       | *(vide)* |
| `MONGO_DATABASE`  | Nom de la base MongoDB (cache + historique)            | `ffe_chess` |

> **Token Lichess :** l'opening explorer requiert désormais une authentification.
> Générez un token gratuit (sans scope) sur
> https://lichess.org/account/oauth/token et renseignez `LICHESS_TOKEN` dans
> `.env`. Sans token, `/api/v1/moves/{fen}` renvoie une erreur `502` explicite.
>
> **Clé YouTube :** créez une clé API dans la console Google Cloud (activez
> « YouTube Data API v3 ») et renseignez `YOUTUBE_API_KEY` dans `.env`. Sans
> clé, `/api/v1/videos/{opening}` renvoie une erreur `503` explicite.

## Livrables documentaires

| Document | Objet |
|----------|-------|
| [docs/note-analyse-video-mcp.md](docs/note-analyse-video-mcp.md) | Note sur le système avancé d'analyse vidéo : bénéfices, limites, architecture MCP, étude de faisabilité (coûts build + opex), alternatives et roadmap |

## Avancement (étapes de la mission)

- [x] **Étape 1** – Structure du projet, dépôt Git, `docker-compose` (healthcheck FastAPI)
- [x] **Étape 2** – Endpoints Lichess (coups théoriques) + Stockfish (évaluation)
- [x] **Étape 3** – RAG Wikichess → Milvus (recherche vectorielle) orchestré par LangGraph
- [x] **Étape 4** – Recherche de vidéos YouTube (API Data v3) orchestrée par LangGraph
- [x] **Étape 5** – Interface Angular (ngx-chess-board) + agent d'orchestration (`/analyze`)
- [x] **Étape 6** – Containerisation complète (6 services, volumes persistants) + démonstration
- [x] **Étape 7** – Note système d'analyse vidéo (MCP) : bénéfices, limites, faisabilité
