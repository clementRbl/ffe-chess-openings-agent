# Procédure de test manuel de bout en bout

POC agent IA — apprentissage des ouvertures aux échecs (FFE)

Ce document permet de vérifier, sans connaissance préalable du code, que
l'ensemble du système fonctionne. Il se déroule en une trentaine de minutes
(hors premier téléchargement des images) et couvre les six services, les six
routes de l'API, l'interface, la persistance des données et le comportement du
système en panne.

**Convention :** chaque test indique la commande à lancer et le **résultat
attendu**. Un résultat différent est un échec — les causes fréquentes sont
regroupées au § 9.

---

## 1. Prérequis

| Élément | Vérification | Attendu |
|---------|--------------|---------|
| Docker | `docker --version` | version 24 ou supérieure |
| Docker Compose v2 | `docker compose version` | version 2.x |
| Espace disque | `df -h .` | au moins 8 Go libres |
| Ports libres | `ss -tlnp \| grep -E ':(4200\|8000\|19530\|9091)'` | aucune ligne |

Deux clés sont nécessaires pour tester **toutes** les sources. Sans elles, le
système fonctionne mais deux tests seront en échec attendu (§ 8.3).

| Clé | Où l'obtenir | Variable |
|-----|--------------|----------|
| Token Lichess (gratuit, sans scope) | https://lichess.org/account/oauth/token | `LICHESS_TOKEN` |
| Clé YouTube Data v3 | Console Google Cloud, API « YouTube Data API v3 » activée | `YOUTUBE_API_KEY` |

---

## 2. Démarrage

### 2.1 Configuration

```bash
cp .env.example .env
```

Éditer `.env` et renseigner `LICHESS_TOKEN` et `YOUTUBE_API_KEY`.

### 2.2 Lancement

```bash
docker compose up --build -d
```

> Premier lancement : compter une dizaine de minutes (construction des images,
> téléchargement de MongoDB, Milvus, etcd et MinIO).

### 2.3 Test 1 — Tous les services sont sains

```bash
docker compose ps
```

**Attendu :** six services, tous `Up`. Cinq portent la mention `(healthy)` ;
`frontend` (nginx) n'a pas de sonde et affiche seulement `Up`.

```
backend    Up X minutes (healthy)
etcd       Up X minutes (healthy)
frontend   Up X minutes
milvus     Up X minutes (healthy)
minio      Up X minutes (healthy)
mongo      Up X minutes (healthy)
```

> Milvus met jusqu'à 90 secondes à devenir `healthy` : c'est normal, attendre
> avant de conclure à un échec.

### 2.4 Test 2 — Chargement du corpus dans Milvus

**Obligatoire au premier démarrage.** Sans cette étape, la recherche vectorielle
ne renvoie rien.

```bash
docker compose exec backend uv run python -m app.scripts.ingest
```

**Attendu :** deux lignes, la seconde confirmant l'insertion.

```
Loaded 34 chunks from data/wikichess
Inserted 34 chunks into 'wikichess_openings'
```

> Le modèle d'embedding (~1,2 Go) est téléchargé au premier lancement : cette
> commande peut prendre plusieurs minutes. Elle est à relancer uniquement si le
> volume `milvus_data` est supprimé.

---

## 3. Tests de l'API

### 3.1 Test 3 — Disponibilité du backend

```bash
curl http://localhost:8000/api/v1/healthcheck
```

**Attendu :** `{"status":"ok"}`

### 3.2 Test 4 — Documentation interactive

Ouvrir http://localhost:8000/docs dans un navigateur.

**Attendu :** l'interface Swagger liste les six routes (`healthcheck`, `moves`,
`evaluate`, `vector-search`, `videos`, `analyze`).

### 3.3 Test 5 — Coups théoriques (Lichess)

```bash
curl "http://localhost:8000/api/v1/moves/rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR%20w%20KQkq%20-%200%202"
```

**Attendu :** `"opening":"Sicilian Defense"` et une liste de coups commençant par
`Nf3`, `Nc3`, `c3`, chacun avec son nombre de parties de référence.

> Les espaces de la FEN doivent être encodés en `%20` dans l'URL.

### 3.4 Test 6 — Évaluation moteur (Stockfish)

```bash
curl "http://localhost:8000/api/v1/evaluate/rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201"
```

**Attendu :** `"type":"cp"`, une `value` faible et positive (entre 20 et 40 : la
position de départ est très légèrement favorable aux Blancs) et un `best_move`
de quatre caractères comme `d2d4` ou `e2e4`.

> Le score est exprimé **du point de vue des Blancs** : positif = avantage aux
> Blancs, négatif = avantage aux Noirs, quel que soit le camp au trait. Les
> moteurs raisonnent nativement du point de vue du joueur qui doit jouer ;
> l'API normalise cette valeur.

### 3.5 Test 7 — Recherche vectorielle (Milvus + Wikichess)

```bash
curl "http://localhost:8000/api/v1/vector-search?query=defense%20sicilienne&top_k=2"
```

**Attendu :** deux passages, le premier de titre `Défense sicilienne` avec un
score autour de 0,58. Les scores sont des similarités cosinus : plus haut =
plus proche.

### 3.6 Test 8 — Vidéos explicatives (YouTube)

```bash
curl "http://localhost:8000/api/v1/videos/partie%20italienne"
```

**Attendu :** cinq vidéos, chacune avec `title`, `channel`, `url` (lien de
visionnage) et `embed_url` (lien d'intégration utilisé par l'interface).

### 3.7 Test 9 — Analyse complète, position dans la théorie

C'est le test central : il exerce les cinq sources en une seule requête.

```bash
curl -G "http://localhost:8000/api/v1/analyze" \
  --data-urlencode "fen=r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
```

**Attendu :**

| Champ | Valeur attendue |
|-------|-----------------|
| `opening` | `Italian Game` |
| `in_theory` | `true` |
| `theoretical_moves` | commence par `Bc5`, `Nf6`, `Be7` |
| `evaluation` | type `cp`, valeur proche de 0 |
| `context` | 3 passages Wikichess |
| `videos` | 5 vidéos |
| `sources` | les **cinq** sources (`lichess`, `stockfish`, `milvus`, `youtube`, `mongo`) à `"ok": true` |
| `summary` | `Position dans la théorie (Italian Game). Coups principaux recommandés : …` |

### 3.8 Test 10 — Analyse d'une position hors théorie

```bash
curl -G "http://localhost:8000/api/v1/analyze" \
  --data-urlencode "fen=rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2"
```

Cette position résulte de 1.f3 e5 2.g4, deux coups qui affaiblissent gravement
le roi blanc.

**Attendu :**

- `in_theory` vaut `false` et `theoretical_moves` est vide ;
- `evaluation` indique `"type":"mate"`, `"value":-1` et `"best_move":"d8h4"` —
  le moteur annonce le mat en un coup par Dh4#, délivré par les **Noirs** ;
  le score est toujours donné du point de vue des Blancs, d'où le signe négatif ;
- `sources` ne contient que **trois** entrées (`lichess`, `stockfish`, `mongo`) ;
- `summary` commence par `Position hors théorie : suivez l'évaluation du moteur.`

> **Ce n'est pas un bug.** Sans nom d'ouverture, il n'y a rien à chercher dans
> Milvus ni sur YouTube : l'agent saute ces deux étapes. C'est l'aiguillage
> conditionnel du graphe. Le même phénomène se produit sur la position de départ,
> pour laquelle Lichess ne renvoie aucun nom d'ouverture puisqu'aucun coup n'a
> encore été joué.

### 3.9 Test 11 — Rejet des positions invalides

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/v1/evaluate/pas-une-position"
curl -s -o /dev/null -w "%{http_code}\n" -G "http://localhost:8000/api/v1/analyze" --data-urlencode "fen=8/8/8/8/8/8/8/8 w - - 0 1"
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/v1/vector-search"
```

**Attendu :** `400`, `400`, `422`.

Le deuxième cas est un échiquier vide : syntaxiquement correct, mais illégal
(aucun roi). Il doit être refusé avant tout appel à Lichess ou Stockfish.

---

## 4. Tests de l'interface

### 4.1 Test 12 — L'interface est servie et la visite guidée démarre

Ouvrir http://localhost:4200 **dans une fenêtre de navigation privée** (la
visite guidée ne se déclenche seule qu'au premier passage, l'information étant
mémorisée dans le navigateur).

**Attendu :** l'en-tête « Ouvertures » avec sa pastille cavalier, un échiquier
en position de départ à gauche, et à droite le bandeau de verdict (badge « Dans
la théorie » puis le nom de l'ouverture en gros). La **visite guidée** s'ouvre
sur la première étape (« Ton échiquier ») ; la parcourir jusqu'au bout avec
« Suivant ».

> Sur la position de départ, Lichess ne nomme aucune ouverture — aucun coup
> n'a été joué, il n'y a donc rien à identifier. Le bandeau affiche « À toi
> d'ouvrir » et invite à jouer le premier coup ; les cartes « Comprendre cette
> ouverture » et « Vidéos » n'apparaissent qu'à partir de là. Ce n'est pas un
> échec d'identification : dès **1.e4**, le bandeau annonce « King's Pawn
> Game » et les deux cartes se remplissent.

> Le nombre d'étapes s'adapte à ce qui est affiché : sur la position de départ,
> les cartes « Comprendre cette ouverture » et « Vidéos explicatives » sont
> absentes, la visite compte donc 7 étapes au lieu de 9.

Cliquer ensuite sur **Revoir la visite guidée**, le bouton vert en haut à
droite.

**Attendu :** la visite se relance à la demande.

### 4.2 Test 13 — Synchronisation de la position

Jouer **1.e4** en glissant le pion, puis **1…c5** pour les Noirs.

**Attendu à chaque coup :**

1. la pastille sous l'échiquier bascule : rond blanc et « Aux Blancs de jouer »,
   puis rond noir et « Aux Noirs de jouer » ;
2. la mention « Analyse de la position en cours… » apparaît brièvement ;
3. après 1…c5, le panneau affiche l'ouverture **Sicilian Defense**, une **barre
   d'évaluation** penchant très légèrement du côté des Blancs avec sa traduction
   en clair (« La position est équilibrée. »), les coups joués par les maîtres
   avec leur nombre de parties, des explications sur l'ouverture et la carte
   « Vidéos sur Sicilian Defense » ;
4. déplier « Détails techniques » : la FEN affichée correspond à la position.

> **Notation.** L'interface affiche les coups en notation **française** (`Cf3`
> le cavalier, `Fc4` le fou, `Td1` la tour, `Dh5` la dame, `Rg1` le roi), et le
> coup du moteur sous la forme « case de départ → case d'arrivée ». L'API, elle,
> conserve la notation anglaise standard de Lichess (`Nf3`) et la notation UCI
> (`g1f3`) : la traduction est faite à l'affichage.

### 4.3 Test 14 — Annuler un coup resynchronise tout l'écran

Après 1.e4 c5, cliquer sur **Annuler**.

**Attendu :** l'écran revient exactement à l'état d'après 1.e4 — la pièce
retourne sur sa case, la pastille repasse « Aux Noirs de jouer », le bandeau
réaffiche « King's Pawn Game », les coups de maîtres redeviennent c5, e5, e6 et
l'évaluation reprend sa valeur précédente. Aucun élément ne reste sur la
position abandonnée.

Cliquer une seconde fois.

**Attendu :** retour à la position de départ, et le bouton **se désactive** — il
n'y a plus rien à annuler. Sur la position de départ, il est grisé dès le
chargement.

### 4.4 Test 15 — Les coups conseillés sont tracés sur l'échiquier

Jouer 1.e4 c5.

**Attendu :** trois traits en pointillé se dessinent sur le plateau, animés du
départ vers l'arrivée. Chacun part de la pièce à déplacer et se termine par une
pastille verte numérotée **1**, **2** ou **3** — le même rang que dans la liste
« Ce que jouent les maîtres ». Sur cette position, la pastille 1 est en f3 (le
cavalier du roi), et les pastilles 2 et 3 sont **côte à côte** en c3, où
aboutissent le cavalier de la dame et le pion. Le trajet du cavalier passe par
un coude, comme son déplacement réel : jamais une ligne droite en diagonale.

Une pastille **orange étoilée** apparaît lorsque le moteur recommande un coup
absent des trois premiers ; s'il rejoint l'un d'eux, aucune quatrième flèche
n'est tracée. La légende sous le plateau rappelle ce code.

Survoler le deuxième coup de la liste.

**Attendu :** sa flèche seule reste nette, les autres s'effacent presque
entièrement, et la ligne survolée prend un fond vert pâle.

Cliquer sur le bouton **Flèches**.

**Attendu :** le plateau redevient nu et le bouton perd sa teinte verte. Un
second clic les rétablit.

Déplacer une pièce en passant par-dessus une flèche.

**Attendu :** le coup se joue normalement — le calque des flèches n'intercepte
aucun clic.

### 4.5 Test 16 — La barre d'évaluation se lit sans ambiguïté

Observer la carte « Qui est mieux ? » sur la position de départ.

**Attendu :** un nombre signé en écriture française (`+0,31` et non `+0.31`),
gris, suivi d'une pastille grise **« Équilibre »** et de la phrase « Écart trop
faible pour départager les deux camps ». La barre est légèrement décalée vers
la droite du centre, mais la frontière reste **dans la bande claire du milieu**,
celle qui matérialise la zone d'égalité (un demi-pion de part et d'autre).

> **Pourquoi pas 0,00 au départ ?** Les Blancs jouent en premier ; tous les
> moteurs leur accordent un léger avantage initial, de l'ordre de deux à trois
> dixièmes de pion. C'est le comportement attendu, pas un défaut de réglage.

Prendre une pièce adverse pour créer un vrai déséquilibre.

**Attendu :** le nombre passe au **vert** avec la pastille « Blancs » si ce sont
les Blancs qui mènent, à l'**orange** avec la pastille « Noirs » dans le cas
contraire, la phrase devient « Léger avantage », « Avantage net » ou « Position
gagnante pour … », et la frontière de la barre sort de la bande d'égalité.

> **Convention de signe.** Le score est toujours donné du point de vue des
> Blancs, quel que soit le camp au trait : positif = avantage aux Blancs.

### 4.6 Test 17 — Les infobulles expliquent le vocabulaire

Survoler les marqueurs `?` des cartes, ainsi que le badge « Dans la théorie ».

**Attendu :** une infobulle explique en langage courant la lecture du score et
de la bande d'égalité, la notation UCI du coup suggéré, l'origine des coups de
maîtres et la correspondance des initiales de pièces, le périmètre des vidéos
et le sens de « dans la théorie ».

Relancer la visite guidée depuis le bouton de l'en-tête.

**Attendu :** neuf étapes s'enchaînent, dont une pointe les flèches du plateau
et une autre la carte d'évaluation. Les étapes visant une carte absente de
l'écran (contexte, vidéos) sont passées sans erreur.

### 4.7 Test 18 — Les extraits portent tous sur la même ouverture

Jouer 1.e4 c5 et lire la carte « Comprendre cette ouverture ».

**Attendu :** une ligne annonce « Extraits de la fiche **Défense sicilienne** »,
puis deux paragraphes, tous deux sur la sicilienne. **Aucun paragraphe ne porte
sur une autre ouverture.**

Rejouer depuis le départ 1.e4 e6 (française), puis 1.e4 c6 (Caro-Kann), puis
l'italienne (1.e4 e5 2.Cf3 Cc6 3.Fc4).

**Attendu :** à chaque fois, la fiche annoncée correspond à l'ouverture jouée et
tous les extraits en proviennent. Le nombre d'extraits varie de un à trois selon
ce que la fiche contient — c'est normal, la carte ne complète pas avec du
remplissage.

> **Pourquoi ce test.** La recherche documentaire classe les passages par
> proximité et en renvoyait toujours trois, même quand le troisième portait sur
> une ouverture voisine : sur la sicilienne, un extrait sur la Caro-Kann
> s'affichait sans avertissement. L'agent ne retient plus que les passages
> d'une seule fiche.

Jouer enfin 1.e4 d5 (défense scandinave), qui n'est pas couverte par le corpus.

**Attendu :** la carte annonce une fiche portant un autre nom que l'ouverture
jouée. Ce n'est pas une erreur : le corpus ne contient que sept fiches, et le
bandeau nomme toujours l'ouverture réellement jouée. L'important est que la
provenance soit affichée, pour que le lecteur ne prenne pas ces extraits pour
une explication de son ouverture.

### 4.8 Test 19 — Les vidéos ne se chargent qu'à la demande

**Attendu avant tout clic :** le titre de la carte reprend le nom de l'ouverture
(« Vidéos sur Sicilian Defense ») et précise que ces vidéos portent sur
l'ouverture entière et non sur le coup joué. Aucune vidéo n'est lancée, seules
cinq vignettes sont proposées sous la mention « Choisissez une vidéo pour la
regarder ici — rien ne se charge avant ce clic ».

Cliquer sur une vignette.

**Attendu :** le lecteur apparaît au-dessus de la liste et la vidéo se lit dans
la page. Le bouton « Fermer la vidéo » la retire.

### 4.9 Test 20 — La vidéo ne redémarre pas toute seule

Lancer une vidéo, la laisser tourner quelques secondes, puis **cliquer plusieurs
fois n'importe où dans la page** (sur un titre, dans le vide, sur une infobulle).

**Attendu :** la lecture se poursuit sans jamais repartir du début.

Jouer ensuite un coup sur l'échiquier.

**Attendu :** si la même vidéo est encore proposée pour la nouvelle position, la
lecture continue sans coupure ; sinon le lecteur se ferme et la nouvelle liste
de vignettes s'affiche.

### 4.10 Test 21 — Position hors théorie depuis l'interface

Cliquer sur « Réinitialiser la partie », puis jouer **1.f3 e5 2.g4**.

**Attendu :** le panneau bascule sur le discours moteur — la position est
signalée hors théorie, l'évaluation annonce « Mat en 1 » et le coup suggéré est
`d8h4`. Les cartes « Comprendre cette ouverture » et « Vidéos explicatives »
disparaissent, et la carte des coups de maîtres invite à s'appuyer sur le
moteur.

### 4.11 Test 22 — Les appels passent bien par le proxy

```bash
curl http://localhost:4200/api/v1/healthcheck
```

**Attendu :** `{"status":"ok"}`. C'est nginx qui relaie vers le backend ; ce test
vérifie le chemin exact qu'emprunte l'application Angular, et donc l'absence de
problème de CORS.

---

## 5. Tests du cache et de l'historique (MongoDB)

### 5.1 Test 23 — Les analyses sont historisées

```bash
docker compose exec mongo mongosh ffe_chess --quiet \
  --eval "db.analyses.find().sort({created_at:-1}).limit(3)"
```

**Attendu :** les trois dernières analyses, chacune avec `fen`, `opening`,
`in_theory`, `theoretical_moves`, `evaluation`, `summary` et `created_at`. Les
positions jouées au § 4 doivent y figurer.

### 5.2 Test 24 — Les appels externes sont mis en cache

```bash
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.api_cache.countDocuments()"
```

Noter le nombre, rejouer **exactement la même position** qu'au test 9, puis
recompter.

**Attendu :** le nombre **n'augmente pas**. La réponse vient du cache, aucun
appel n'a été consommé sur le quota YouTube.

> Le temps de réponse, lui, ne change pas de façon spectaculaire : l'essentiel du
> délai vient de Stockfish et du calcul d'embedding, qui ne sont pas mis en
> cache. Le cache protège les quotas, pas la latence.

### 5.3 Test 25 — L'expiration automatique est configurée

```bash
docker compose exec mongo mongosh ffe_chess --quiet \
  --eval "db.api_cache.getIndexes()"
```

**Attendu :** trois index, dont `expires_at_1` portant `expireAfterSeconds: 0`.
C'est lui qui fait purger par MongoDB les entrées de plus de 24 heures.

---

## 6. Test de persistance

### Test 26 — Les données survivent à la recréation des conteneurs

```bash
# 1. Relever les compteurs
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.analyses.countDocuments()"
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.api_cache.countDocuments()"

# 2. Détruire puis recréer les conteneurs (SANS -v, qui supprimerait les volumes)
docker compose down
docker compose up -d

# 3. Attendre que les services soient sains, puis recompter
docker compose ps
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.analyses.countDocuments()"
docker compose exec mongo mongosh ffe_chess --quiet --eval "db.api_cache.countDocuments()"

# 4. Vérifier que l'index Milvus est intact (sans réingestion)
curl "http://localhost:8000/api/v1/vector-search?query=sicilienne&top_k=1"
```

**Attendu :** les compteurs sont **identiques** avant et après, et la recherche
vectorielle répond toujours sans avoir relancé l'ingestion.

```bash
docker volume ls | grep echecs
```

**Attendu :** cinq volumes — `mongo_data`, `milvus_data`, `etcd_data`,
`minio_data`, `hf_cache`.

---

## 7. Tests automatisés

### Test 27 — Suite de tests du backend

```bash
cd backend && uv run pytest
```

**Attendu :** 53 tests passent. Ils s'exécutent sans réseau ni service externe
(toutes les dépendances sont remplacées par des doublures) et couvrent la
validation FEN, l'aiguillage du graphe, la dégradation gracieuse, le cache, la
sélection des extraits documentaires, la reconnexion à Milvus et le contrat
HTTP.

### Test 28 — Suite de tests du frontend

```bash
cd frontend && npx ng test --watch=false --browsers=ChromeHeadless
```

**Attendu :** 46 tests passent. Ils couvrent le lecteur vidéo (ouverture à la
demande, stabilité de l'URL d'intégration, fermeture), les flèches de
recommandation sur l'échiquier, la lisibilité de l'évaluation et l'annulation
d'un coup.

### Test 29 — Qualité du code

```bash
cd backend && uv run ruff check . && uv run ruff format --check app tests
```

**Attendu :** `All checks passed!` puis `41 files already formatted`.

---

## 8. Tests de résistance aux pannes

Ces tests vérifient la promesse centrale de l'architecture : **la panne d'une
source ne doit jamais interrompre l'analyse**. Ils se lisent dans le champ
`sources` de la réponse.

### 8.1 Test 30 — Panne de MongoDB

```bash
docker compose stop mongo
curl -G "http://localhost:8000/api/v1/analyze" \
  --data-urlencode "fen=rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
docker compose start mongo
```

**Attendu :** l'analyse aboutit normalement (coups, évaluation, contexte,
vidéos), et seul `sources.mongo` passe à `"ok": false` avec un message
d'explication. Le cache et l'historique sont perdus le temps de la panne, rien
d'autre.

### 8.2 Test 31 — Panne de Milvus

```bash
docker compose stop milvus
curl -G "http://localhost:8000/api/v1/analyze" \
  --data-urlencode "fen=rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
docker compose start milvus
```

**Attendu :** `context` est vide et `sources.milvus` passe à `"ok": false`, mais
les coups théoriques, l'évaluation et les vidéos sont bien là.

Puis, **une fois Milvus redevenu `healthy`** (jusqu'à 90 secondes), rejouer la
même requête **sans redémarrer le backend** :

```bash
curl "http://localhost:8000/api/v1/vector-search?query=defense%20sicilienne&top_k=1"
```

**Attendu :** la recherche fonctionne de nouveau et `sources.milvus` repasse à
`"ok": true`. Vérifier au passage que le backend n'a pas redémarré :

```bash
docker inspect ffe-chess-backend --format 'RestartCount={{.RestartCount}}'
```

**Attendu :** `RestartCount=0`.

> **Pourquoi ce contrôle.** Le client `pymilvus` mutualise ses canaux gRPC dans
> un registre interne. Après une panne, ce registre pouvait resservir
> indéfiniment un canal fermé : la recherche documentaire restait cassée jusqu'au
> redémarrage du backend, alors que Milvus était déclaré sain. Le dépôt demande
> désormais une connexion dédiée, hors de ce registre, et retente une fois après
> reconnexion.

### 8.3 Test 32 — Clés d'API absentes

Plutôt que de modifier `.env`, lancer un backend jetable sans clés sur le port
8001 — la démonstration reste ainsi utilisable pendant le test :

```bash
docker compose run --rm -d --name ffe-test-nokeys \
  -e LICHESS_TOKEN= -e YOUTUBE_API_KEY= -p 8001:8000 backend
```

**Attendu :** des erreurs **explicites**, jamais silencieuses.

```bash
curl "http://localhost:8001/api/v1/moves/rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR%20w%20KQkq%20-%200%202"
curl "http://localhost:8001/api/v1/videos/sicilienne"
```

| Appel | Code | Message |
|-------|------|---------|
| `/api/v1/moves/{fen}` | 502 | l'explorateur Lichess exige une authentification, avec l'adresse où générer un token |
| `/api/v1/videos/{opening}` | 503 | `YOUTUBE_API_KEY` n'est pas configurée |

Pour `/analyze`, le résultat dépend de ce que contient déjà le cache — et c'est
le meilleur moment pour constater son utilité.

**Sur une position déjà analysée** (par exemple celle du test 9) :

```bash
curl -G "http://localhost:8001/api/v1/analyze" \
  --data-urlencode "fen=rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
```

**Attendu :** l'analyse est **complète**, les cinq sources à `"ok": true`, alors
même qu'aucune clé n'est configurée. Les réponses Lichess et YouTube proviennent
du cache MongoDB.

**Sur une position jamais analysée** (ici 1.d4 Cf6 2.c4 g6 3.Cc3 Fg7) :

```bash
curl -G "http://localhost:8001/api/v1/analyze" \
  --data-urlencode "fen=rnbqk2r/ppppppbp/5np1/8/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 2 4"
```

**Attendu :** l'analyse aboutit quand même, sur la seule évaluation du moteur —
`sources.lichess` passe à `"ok": false` avec le message d'authentification,
`theoretical_moves` est vide et le résumé bascule sur Stockfish. `youtube`
n'apparaît pas dans `sources` : faute de réponse de Lichess, aucune ouverture
n'est nommée, donc l'agent ne cherche ni contexte ni vidéo (même aiguillage
qu'au test 10).

Supprimer ensuite le backend jetable :

```bash
docker rm -f ffe-test-nokeys
```

---

## 9. En cas d'échec

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| `milvus` reste `unhealthy` | Démarrage encore en cours | Attendre 90 s, puis `docker compose logs milvus` |
| `milvus` redémarre en boucle | `etcd` ou `minio` sont arrêtés | `docker compose up -d etcd minio` |
| `vector-search` ne renvoie rien | Corpus non chargé | Relancer le test 2 (ingestion) |
| `/moves` renvoie 502 | Token Lichess absent ou invalide | Renseigner `LICHESS_TOKEN` dans `.env`, puis `docker compose up -d backend` |
| `/videos` renvoie 503 | Clé YouTube absente ou quota dépassé | Vérifier `YOUTUBE_API_KEY` et le quota dans la console Google Cloud |
| `/evaluate` renvoie 503 | Moteur introuvable | `docker compose exec backend ls /usr/games/stockfish` |
| L'interface reste vide | Backend non démarré | `docker compose ps`, puis `docker compose logs backend` |
| Port déjà utilisé au démarrage | Conflit avec un autre service | Modifier `BACKEND_PORT` ou `FRONTEND_PORT` dans `.env` |
| Seules 3 sources dans `analyze` | Position sans nom d'ouverture | Comportement normal, voir test 10 |

Consulter les journaux d'un service :

```bash
docker compose logs backend --tail 50
docker compose logs -f backend      # en continu
```

---

## 10. Récapitulatif

| # | Test | Résultat |
|---|------|----------|
| 1 | Six services sains | ☐ |
| 2 | Corpus chargé dans Milvus | ☐ |
| 3 | Disponibilité du backend | ☐ |
| 4 | Documentation Swagger | ☐ |
| 5 | Coups théoriques (Lichess) | ☐ |
| 6 | Évaluation moteur (Stockfish) | ☐ |
| 7 | Recherche vectorielle (Milvus) | ☐ |
| 8 | Vidéos explicatives (YouTube) | ☐ |
| 9 | Analyse complète, cinq sources | ☐ |
| 10 | Analyse hors théorie | ☐ |
| 11 | Rejet des positions invalides | ☐ |
| 12 | Interface servie et visite guidée | ☐ |
| 13 | Synchronisation de la position | ☐ |
| 14 | Annulation d'un coup | ☐ |
| 15 | Flèches des coups conseillés | ☐ |
| 16 | Lecture de la barre d'évaluation | ☐ |
| 17 | Infobulles du vocabulaire | ☐ |
| 18 | Extraits d'une seule fiche | ☐ |
| 19 | Vidéos chargées à la demande | ☐ |
| 20 | La vidéo ne redémarre pas seule | ☐ |
| 21 | Position hors théorie depuis l'interface | ☐ |
| 22 | Proxy nginx | ☐ |
| 23 | Historique des analyses | ☐ |
| 24 | Mise en cache des appels externes | ☐ |
| 25 | Expiration automatique du cache | ☐ |
| 26 | Persistance des volumes | ☐ |
| 27 | Tests automatisés du backend | ☐ |
| 28 | Tests automatisés du frontend | ☐ |
| 29 | Qualité du code | ☐ |
| 30 | Panne de MongoDB | ☐ |
| 31 | Panne de Milvus | ☐ |
| 32 | Clés d'API absentes | ☐ |

Pour arrêter le système en conservant les données :

```bash
docker compose down
```

Pour tout supprimer, volumes compris (remise à zéro complète) :

```bash
docker compose down -v
```
