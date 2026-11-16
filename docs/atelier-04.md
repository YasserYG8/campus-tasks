# Atelier 4 — Pile API + PostgreSQL avec Docker Compose

Branche : `atelier-04` · Tag de fin d'atelier : `atelier-4`

## Ce qui a été livré

| Élément | Rôle |
|---|---|
| `compose.yaml` | Services `api` (construit depuis le Dockerfile) et `db` (`postgres:17-alpine`) |
| Réseau Compose | `campus-tasks_default` : `api` joint la base par le nom `db` |
| Volume nommé `pgdata` | Les données de PostgreSQL survivent à `docker compose down` |
| `healthcheck` sur `db` | `pg_isready` ; `api` attend `condition: service_healthy` |
| Profil `debug` | Service `adminer` sur le port 8081, démarré seulement à la demande |
| `app/app.py` | Au démarrage, l'API journalise si `DB_HOST:DB_PORT` est joignable ; `GET /info` donne l'état de la base |

Le port 5432 n'est **pas** publié : seule l'API peut joindre la base.
Le mot de passe `dev-password` est fictif et réservé à l'environnement local.

> Pourquoi `/info` ? L'API de l'atelier 3 ne contactait pas la base : avec `DB_HOST: localhost`,
> l'incident de l'étape 5 n'aurait laissé aucune trace. L'API tente maintenant une connexion TCP
> vers la base (bibliothèque standard, aucune dépendance ajoutée). `/health` reste indépendant de
> la base, pour que la mise en service de l'atelier 5 fonctionne sans PostgreSQL.

## Preuves

### Étape 1 et 2 — deux services, réseau privé

```
$ docker compose config --quiet && echo 'configuration valide'
configuration valide
$ docker compose exec api getent hosts db
172.20.0.2      db
$ docker compose exec db psql -U campus -d campus -c 'select now();'
 2026-11-16 09:08:52.596857+00
$ curl -s http://localhost:8080/info
{"app":"campus-tasks","db":"ok","db_detail":"db:5432 joignable","env":"dev"}
$ timeout 3 bash -c '</dev/tcp/127.0.0.1/5432'      # depuis la machine hôte
bash: connect: Connection refused                    # port non publié : voulu
```

### Étape 3 — persistance

Sans volume : après `down` puis `up`, la table a disparu.

```
$ docker compose exec db psql -U campus -d campus -c 'select * from essai;'
ERROR:  relation "essai" does not exist
```

Avec le volume `pgdata` : la table survit à `down` puis `up`.

```
$ docker compose exec db psql -U campus -d campus -c 'select * from essai;'
 id
----
  1
(1 row)
$ docker volume ls --filter name=pgdata
local     campus-tasks_pgdata
```

### Étape 4 — santé et ordre de démarrage

```
 Container campus-tasks-db-1  Waiting
 Container campus-tasks-db-1  Healthy
 Container campus-tasks-api-1  Starting
$ docker compose ps
api | Up 13 seconds (healthy) | 0.0.0.0:8080->8080/tcp
db  | Up 23 minutes (healthy) | 5432/tcp
$ docker inspect --format '{{.State.Health.Status}}' $(docker compose ps -q db)
healthy
```

## Incident de l'étape 5 — le service injoignable

```
$ docker compose logs --tail=50 api
ERROR base de données : localhost:5432 injoignable ([Errno 111] Connection refused)
$ docker compose exec api env | sort | grep DB_
DB_HOST=localhost
DB_PORT=5432
$ curl -s http://localhost:8080/info
{"db":"erreur","db_detail":"localhost:5432 injoignable ([Errno 111] Connection refused)", ...}  HTTP 503
$ docker compose exec api getent hosts localhost
::1             localhost ip6-localhost ip6-loopback
$ docker compose exec api getent hosts db
172.20.0.2      db
```

**Explication en quatre lignes :**
1. Symptôme : l'API tourne et `/health` répond, mais elle ne joint pas la base : `Connection refused` vers `localhost:5432`, `/info` renvoie 503.
2. Configuration effective (`exec env`) : `DB_HOST=localhost`, alors que l'on attendait `db`.
3. Dans le conteneur `api`, `localhost` désigne `api` lui-même ; PostgreSQL tourne dans un autre conteneur, joignable par le nom de service `db` (`getent hosts db` le prouve).
4. Correction unique : remettre `DB_HOST: db`, recréer `api` ; le journal affiche `db:5432 joignable`, `/info` renvoie 200 et `/health` répond.

## Défi final — adminer dans le profil `debug`

```
$ docker compose up -d                      # adminer ne démarre pas
api | Up 6 seconds (health: starting)
db  | Up 23 minutes (healthy)
$ docker compose --profile debug up -d      # adminer démarre
adminer | Up 3 seconds | 0.0.0.0:8081->8080/tcp
$ curl -s http://localhost:8081 | grep -o '<title>.*</title>'
<title>Login - Adminer</title>
```

## Quiz de sortie

1. **Pourquoi `db` plutôt que `localhost` ?** Sur le réseau Compose, le nom du service devient un nom de machine. Depuis `api`, `localhost` désigne `api` lui-même, pas la base.
2. **Volume nommé ou montage de dossier ?** Un volume nommé est géré par Docker (`docker volume ls`), indépendant de l'arborescence de l'hôte. Un montage de dossier relie un chemin précis de l'hôte au conteneur : pratique pour le code en développement, mais dépendant de la machine.
3. **Que fait `docker compose down -v` ?** Il supprime les conteneurs, le réseau **et** les volumes : les données sont détruites définitivement.
4. **Healthcheck et `depends_on` ?** `depends_on` seul ne règle que l'ordre de lancement ; il n'attend pas que PostgreSQL soit prêt. Le healthcheck dit quand la base répond vraiment, et `condition: service_healthy` fait attendre l'API.
5. **Pourquoi ne pas publier 5432 ?** Chaque port publié est une porte ouverte. Ici seule l'API doit joindre la base ; le réseau privé suffit.
6. **Pourquoi `docker compose config` avant de lancer ?** Il révèle les erreurs YAML et montre la configuration réellement comprise, variables développées : une erreur trouvée là coûte quelques secondes au lieu de plusieurs minutes.
