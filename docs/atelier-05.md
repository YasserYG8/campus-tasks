# Atelier 5 — Chaîne CI/CD et mise en service

Branche : `atelier-05` · Version livrée : `v1.0.0` · Tag de fin d'atelier : `atelier-5`

> Les blocs marqués **À COMPLÉTER** doivent recevoir la sortie réelle des commandes
> (pipeline GitHub, registre, staging, incident). Ne rien inventer : copier les journaux.

## Ce qui a été livré

| Fichier | Rôle |
|---|---|
| `requirements-dev.txt` | Dépendances de test : `-r requirements.txt` + `pytest==8.3.5` (le runner ne connaît que ce qui est déclaré) |
| `pytest.ini` | Ajoute `app/` au chemin d'import, limite la recherche à `tests/` |
| `tests/test_smoke.py` | Test minimal de l'étape 1 |
| `tests/test_app.py` | `/health` répond 200 même si la base est injoignable ; `/info` renvoie 200 sans base, 200 base joignable, 503 base injoignable |
| `.github/workflows/ci.yml` | Jobs `test` → `docker-build` → `deploy-staging` (voir ci-dessous) |
| `compose.staging.yaml` | Staging : image publiée `ghcr.io/yasseryg8/campus-tasks:${IMAGE_TAG}`, aucune reconstruction |
| `.env.staging.example` | Modèle de `.env.staging` (le vrai fichier est ignoré par Git) |
| `scripts/wait-healthy.sh` | 12 essais × 5 s sur `/health` ; code 0 « staging sain », code 1 « staging non sain » |
| `.gitignore` | Ajoute `.env.staging`, `.env.deploy`, `report.xml`, `.pytest_cache/`, `*:Zone.Identifier` |

### Le workflow `ci.yml`

| Déclencheur | `test` | `docker-build` | `deploy-staging` |
|---|---|---|---|
| `pull_request` | ✔ | construit `campus-tasks:ci`, sans publier | — |
| `push` sur `main` | ✔ | construit `campus-tasks:ci`, sans publier | — |
| `push` d'un tag `v*` | ✔ | publie `ghcr.io/<propriétaire>/campus-tasks:<tag>` | met en service puis contrôle la santé |

Choix techniques :

- `needs: test` : l'image n'est construite que si les tests sont verts ; `needs: docker-build` : on ne met en service qu'une image publiée.
- Le rapport est produit par la même commande que les tests (`pytest -q --junitxml=report.xml`) au lieu de lancer pytest deux fois :
  si un test échoue, `report.xml` existe quand même, et `if: always()` le conserve en artefact `rapport-tests`.
- `permissions: contents: read` au niveau du workflow ; `packages: write` seulement pour `docker-build`, `packages: read` pour `deploy-staging`.
- Connexion au registre avec `secrets.GITHUB_TOKEN` (jeton temporaire fourni par GitHub) : aucun identifiant dans le dépôt.
- `ghcr.io` refuse les majuscules : le nom est calculé avec `${GITHUB_REPOSITORY_OWNER,,}` (`YasserYG8` → `yasseryg8`).

## Preuves

### Étape 1 — tests en local

```
$ python3 -m venv .venv && . .venv/bin/activate
$ pip install -r requirements-dev.txt
$ pytest -q --junitxml=report.xml
......                                                                   [100%]
- generated xml file: /home/yasser/devops-l3/atelier-02/campus-tasks/report.xml -
6 passed in 0.37s
$ git check-ignore -v .venv
```

### Étape 2 et 3 — pipeline sur la merge request

**À COMPLÉTER** :
- URL de la merge request : `https://github.com/YasserYG8/campus-tasks/pull/...`
- URL de l'exécution du pipeline : `https://github.com/YasserYG8/campus-tasks/actions/runs/...`
- Capture : job `test` vert, puis `docker-build` vert, artefact `rapport-tests` téléchargeable.
- Journal d'un échec volontaire (par exemple `assert False`), première erreur utile surlignée :

```
(coller ici)
```

### Étape 4 — version immuable v1.0.0

**À COMPLÉTER** :

```
$ ./scripts/check-project.sh
$ git tag -a v1.0.0 -m "Release 1.0.0"
$ git show v1.0.0
$ git push origin v1.0.0
(coller les sorties, puis l'URL du paquet ghcr.io/yasseryg8/campus-tasks:v1.0.0)
```

> Un paquet publié sur `ghcr.io` depuis un compte personnel est **privé** par défaut.
> Pour le tirer en local : le rendre public (Package settings → Change visibility),
> ou `docker login ghcr.io -u YasserYG8` avec un jeton personnel `read:packages` (jamais versionné).

### Étape 5 — mise en service et contrôle de santé

Le script a été vérifié en local contre l'API Flask (sans Docker) :

```
$ ./scripts/wait-healthy.sh        # API arrêtée (version courte : 2 essais)
curl: (7) Failed to connect to localhost port 8080 after 0 ms: Couldn't connect to server
curl: (7) Failed to connect to localhost port 8080 after 0 ms: Couldn't connect to server
staging non sain                   # code de sortie 1
$ ./scripts/wait-healthy.sh        # API démarrée
{"status":"ok"}
staging sain                       # code de sortie 0
$ git check-ignore -v .env.staging
.gitignore:9:.env.staging	.env.staging
```

**À COMPLÉTER** avec la vraie mise en service (arrêter d'abord la pile de l'atelier 4, sinon `port is already allocated`) :

```
$ docker compose down
$ cp .env.staging.example .env.staging
$ printf 'IMAGE_TAG=v1.0.0\n' > .env.deploy
$ docker compose --env-file .env.deploy -f compose.staging.yaml pull
$ docker compose --env-file .env.deploy -f compose.staging.yaml up -d
$ docker compose --env-file .env.deploy -f compose.staging.yaml ps
$ ./scripts/wait-healthy.sh
(coller les sorties)
```

## Étape 6 — Incident : v0.9.0 défectueuse et retour arrière

**À COMPLÉTER** avec l'image `v0.9.0` fournie par l'enseignant :

```
$ printf 'IMAGE_TAG=v0.9.0\n' > .env.deploy
$ docker compose --env-file .env.deploy -f compose.staging.yaml pull
$ docker compose --env-file .env.deploy -f compose.staging.yaml up -d
$ ./scripts/wait-healthy.sh              # doit échouer
$ docker compose --env-file .env.deploy -f compose.staging.yaml logs --tail=50 api
(coller ; recopier la première erreur utile)

$ printf 'IMAGE_TAG=v1.0.0\n' > .env.deploy   # retour arrière : image déjà validée, aucune reconstruction
$ docker compose --env-file .env.deploy -f compose.staging.yaml up -d
$ ./scripts/wait-healthy.sh              # doit réussir
(coller)
```

### Compte rendu d'incident (cinq lignes)

**À COMPLÉTER** à partir des observations réelles :

1. **Ce qui s'est passé :** …
2. **Quand nous l'avons su :** …
3. **Ce que nous avons fait :** …
4. **Durée d'indisponibilité :** …
5. **Ce qui empêcherait que cela se reproduise :** …

## Défi final — job `deploy-staging`

Choix : un job `deploy-staging` déclenché **uniquement sur les tags** `v*`
(`if: startsWith(github.ref, 'refs/tags/v')`), après `docker-build`. Il tire l'image publiée,
la met en service avec `compose.staging.yaml`, puis exécute `scripts/wait-healthy.sh` :
si le service ne répond pas, le job devient rouge. Les 50 dernières lignes du journal de l'API
sont affichées dans tous les cas (`if: always()`), pour garder la preuve.

**À COMPLÉTER** : URL de l'exécution du tag `v1.0.0` montrant `deploy-staging` vert.

## Quiz de sortie

1. **Différence entre un job et une étape ?** Un job est un ensemble d'étapes exécuté sur un runner neuf ; deux jobs sont indépendants par défaut et peuvent tourner en parallèle. Une étape (step) est une commande ou une action à l'intérieur d'un job ; les étapes s'exécutent dans l'ordre, sur la même machine, et une étape rouge arrête le job.
2. **Pourquoi les tests avant l'image ?** Une image construite à partir d'un code qui échoue aux tests ne doit jamais pouvoir être publiée ni mise en service. Les tests sont aussi plus rapides : l'erreur est signalée plus tôt, sans gaspiller une construction.
3. **À quoi sert `needs` ?** À créer une dépendance entre jobs : `docker-build` attend la fin de `test` et ne démarre que s'il est vert. Sans `needs`, les deux jobs démarrent en parallèle.
4. **Livraison continue ou déploiement continu ?** En livraison continue, le pipeline produit automatiquement une version prête (tag + image publiée), mais un humain décide de la mise en service. En déploiement continu, la mise en service est elle aussi automatique, sans décision humaine.
5. **Pourquoi ne jamais reconstruire une image de version ?** Une reconstruction peut donner un contenu différent (image de base ou dépendances mises à jour). La version `v1.0.0` ne désignerait plus ce qui a été testé, et un retour arrière vers elle ne serait plus sûr. Si la version est mauvaise, on publie `v1.0.1`.
6. **Pourquoi un contrôle de santé après une mise en service réussie ?** `docker compose up -d` réussit dès que le conteneur démarre, pas quand l'application répond. Le conteneur peut tourner avec un service inutilisable (mauvaise adresse d'écoute, plantage au démarrage). Seul `/health` prouve que le service répond, et c'est lui qui décide d'un retour arrière.
