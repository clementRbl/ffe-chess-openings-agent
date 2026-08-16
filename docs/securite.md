# Sécurité

Ce document explique **comment l'agent est sécurisé**, et surtout où sont ses
limites assumées. Il complète [architecture.md](architecture.md) (fonctionnement)
et la [procédure de test manuel](tests-manuels.md) (vérification).

## 1. Périmètre

C'est un **POC local, mono-utilisateur**, destiné à tourner via
`docker compose up` sur le poste de démonstration — pas un service exposé sur
Internet. Le modèle de sécurité ci-dessous part de cette hypothèse ; la
section 7 liste ce qu'il faudrait ajouter avant une exposition publique.

## 2. Secrets

| Secret | Où il vit | Comment il circule |
|--------|-----------|---------------------|
| `LICHESS_TOKEN` | `.env` (non commité) | En-tête `Authorization: Bearer ...` vers Lichess uniquement |
| `YOUTUBE_API_KEY` | `.env` (non commité) | Paramètre `key=` géré par `google-api-python-client` vers Google uniquement |

- `.env` est dans `.gitignore` et n'a jamais été commité (vérifié :
  `git ls-files` ne le liste pas) ; seul `.env.example`, sans valeur, est
  versionné.
- Aucun secret n'est écrit en dur dans le code : tout passe par
  `app/core/config.py` (`pydantic-settings`), chargé depuis l'environnement.
- Le middleware de logging (`app/main.py`) journalise `request.url.path`, **pas**
  la chaîne de requête ni les en-têtes : même si un futur endpoint recevait un
  secret en paramètre, il ne finirait pas dans les journaux.
- Les identifiants MinIO (client S3 interne de Milvus, jamais exposé à
  l'hôte) passent par `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` dans `.env`,
  avec un défaut (`minioadmin` / `minioadmin`) qui n'a de conséquence réelle
  que si le réseau Docker cesse d'être cloisonné.

## 3. Validation des entrées

Toute position FEN traverse `app/services/fen.py` (basé sur `python-chess`)
**avant** le moindre appel à Lichess, Stockfish, Milvus ou MongoDB : une FEN
syntaxiquement invalide ou illégale (ex. échiquier sans roi) est rejetée en
`400` sans jamais atteindre une source externe. Les autres entrées (requête
`/vector-search`, ouverture pour `/videos`) passent par des modèles Pydantic
(`app/schemas/`), qui refusent tout payload mal formé (`422`) avant d'entrer
dans la logique métier.

## 4. Pas d'injection

- **MongoDB** : tous les filtres sont des dictionnaires Python construits par
  le code (`{"key": key, ...}`), jamais une chaîne assemblée à partir d'une
  entrée utilisateur puis interprétée. La valeur d'une clé de cache reste une
  valeur, jamais un opérateur Mongo (`$where`, `$ne`...).
- **SQL** : aucune base relationnelle dans ce projet — pas de surface
  d'injection SQL possible.
- **Stockfish** : la position est passée à la bibliothèque `stockfish` via son
  API Python (écriture sur le stdin du process), jamais via un shell — pas de
  risque d'injection de commande.

## 5. Surface réseau

- Le seul point d'entrée depuis l'hôte est **nginx** (frontend, port
  `FRONTEND_PORT`) et **FastAPI** (backend, port `BACKEND_PORT`). Milvus
  publie aussi ses ports (`19530`, `9091`) vers l'hôte — commodité de debug en
  développement, à retirer d'un `docker-compose.yml` de production.
- Aucun `CORSMiddleware` dans le backend : l'interface Angular n'appelle
  jamais directement `http://backend:8000` depuis le navigateur, nginx
  relaie `/api/*` vers le backend sur la **même origine** (voir
  `frontend/nginx.conf`). Le navigateur ne voit donc qu'une seule origine, ce
  qui élimine la question CORS plutôt que de la configurer.
- MongoDB, Milvus (au sein du réseau), etcd et MinIO ne sont joignables que
  depuis les autres conteneurs du réseau Docker Compose — jamais depuis
  l'hôte pour Mongo/etcd/MinIO.

## 6. Ce que l'agent ne fait pas (limites assumées)

- **Pas d'authentification utilisateur.** L'API n'a ni compte, ni session, ni
  clé d'API pour ses propres appelants — cohérent avec un POC de démonstration
  locale, mais à ajouter (ex. OAuth2 côté FFE, ou au minimum une clé d'API
  interne) avant toute exposition au-delà du poste de démo.
- **Pas de limitation de débit (rate limiting)** sur les routes de l'agent :
  un usage abusif de `/analyze` répercuterait directement la charge sur les
  quotas Lichess/YouTube. Le cache MongoDB (24 h) atténue ce risque pour des
  positions déjà vues, pas pour un balayage de positions nouvelles.
- **Pas de scan de dépendances (SCA) ni d'images automatisé** dans la CI :
  `ruff` couvre la qualité du code, pas les vulnérabilités connues des
  paquets. À ajouter (ex. `pip-audit`, `npm audit`, ou un scanner d'image
  comme Trivy) avant une mise en production.
- **Pas de gestion des secrets externalisée** (Vault, AWS Secrets Manager...) :
  les secrets vivent dans `.env`, adapté à une démo locale, pas à un
  environnement partagé.

## 7. Avant une exposition au-delà du poste de démo

Dans l'ordre de priorité :

1. Authentification/autorisation sur l'API (l'agent ne doit pas rester
   ouvert).
2. Rate limiting sur `/analyze` (le nœud le plus coûteux : Stockfish + calcul
   d'embedding à chaque appel).
3. Ne plus publier les ports Milvus (`19530`/`9091`) vers l'hôte.
4. Scan de vulnérabilités des dépendances et des images Docker dans la CI.
5. Secrets externalisés plutôt qu'un fichier `.env` sur le poste de démo.
