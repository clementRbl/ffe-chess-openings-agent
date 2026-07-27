# Interface Angular — agent ouvertures FFE

Interface du POC : un échiquier interactif dont chaque coup joué déclenche
l'analyse de la position par l'agent, et un panneau affichant ses
recommandations (coups théoriques, évaluation moteur, contexte d'ouverture,
vidéos explicatives).

Le mode d'emploi complet du projet (démarrage via Docker Compose, configuration,
positions de démonstration) se trouve dans le [README racine](../README.md).

## Organisation

| Dossier | Contenu |
|---------|---------|
| `src/app/` | Composant racine (échiquier + panneau) et service d'appel à l'API |
| `projects/ngx-chess-board/` | Librairie de l'échiquier, intégrée en source locale (voir README racine) |

## Développement hors Docker

Le backend doit tourner par ailleurs (`docker compose up -d backend`).

```bash
npm install
npm run build ngx-chess-board   # compiler la librairie de l'échiquier d'abord
npm start                       # http://localhost:4200
```

> En développement, `ng serve` sert l'application sur le port 4200 mais ne
> reproduit pas le proxy nginx utilisé en conteneur : les appels à `/api` doivent
> être redirigés vers `http://localhost:8000` (option `--proxy-config`).
