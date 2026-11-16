# Atelier 3 — Conteneuriser Campus Tasks avec Docker

Branche : `atelier-03` · Tag de fin d'atelier : `atelier-3`

## Ce qui a été livré

| Fichier | Rôle |
|---|---|
| `app/app.py` | API Flask minimale, route `GET /health`, écoute sur `0.0.0.0` |
| `requirements.txt` | Dépendance figée : `Flask==3.1.0` |
| `.dockerignore` | Exclut `.git/`, `.env`, `__pycache__/`, `*.log`, `.venv/` du contexte de build |
| `Dockerfile` | Image 1.1 : base `python:3.12-slim`, utilisateur `appuser`, `HEALTHCHECK` |

Ordre du Dockerfile : `requirements.txt` est copié et installé **avant** le code.
Quand seul `app/app.py` change, les couches `WORKDIR`, `COPY requirements.txt` et
`RUN pip install` sont réutilisées (`CACHED`) ; seule la couche `COPY app/` est rejouée.

## Preuves

### Images 1.0 et 1.1

```
$ docker image ls campus-tasks
REPOSITORY     TAG       IMAGE ID       CREATED              SIZE
campus-tasks   1.1       e349ead87f53   35 seconds ago       198MB
campus-tasks   1.0       a09b056a5b84   About a minute ago   198MB
```

### Cache des couches (après modification de `app/app.py`)

```
#6 [2/5] WORKDIR /app
#6 CACHED
#7 [3/5] COPY requirements.txt .
#7 CACHED
#8 [4/5] RUN pip install --no-cache-dir -r requirements.txt
#8 CACHED
#9 [5/5] COPY app/ ./app/          <- seule étape rejouée
```

### Configuration et inspection (image 1.0)

```
$ docker run -d --name campus-api -p 8080:8080 -e APP_ENV=formation campus-tasks:1.0
$ docker exec campus-api env | sort | grep -E 'APP_ENV|PYTHON_VERSION'
APP_ENV=formation
PYTHON_VERSION=3.12.16
$ docker stats --no-stream campus-api
campus-api CPU=0.03% MEM=21.37MiB / 4.742GiB
$ docker history campus-tasks:1.0   (extrait)
15.3MB  RUN pip install --no-cache-dir -r requirements.txt   <- plus grosse couche ajoutée par nous
41.4MB  RUN ... (couche de l'image de base python:3.12-slim)
```

### Sécurité : utilisateur non root et santé (image 1.1)

```
$ docker exec campus-api whoami        # image 1.0
root
$ docker exec campus-api whoami        # image 1.1
appuser
$ docker inspect --format '{{.State.Health.Status}}' campus-api
healthy
$ curl -fsS http://localhost:8080/health
{"status":"ok"}
```

Aucun secret n'est copié dans l'image : `.env` est exclu par `.dockerignore`.

## Incident de l'étape 6

```
$ docker run -d --name campus-casse -p 8090:8080 campus-tasks:1.1 python app/inexistant.py
$ docker ps -a --filter name=campus-casse
campus-casse | Exited (2) 2 seconds ago
$ docker logs campus-casse
python: can't open file '/app/app/inexistant.py': [Errno 2] No such file or directory
```

**Explication en trois lignes :**
1. Le conteneur a démarré puis s'est arrêté aussitôt : `docker ps` ne le montre pas, `docker ps -a` affiche `Exited (2)`.
2. La première erreur utile est dans `docker logs` : la commande de démarrage demande un fichier qui n'existe pas dans l'image.
3. Un conteneur vit tant que son processus principal vit ; si la commande échoue, le conteneur s'arrête — il faut corriger la commande, pas l'image.

Deuxième situation : `docker run -p 8080:8080` alors que `campus-api` tourne déjà donne
`Bind for 0.0.0.0:8080 failed: port is already allocated` ; `docker ps` montre que `campus-api` occupe déjà le port 8080 de l'hôte.

## Défi final

### Variable `PORT` : deux conteneurs, une seule image, sans reconstruire

```
$ docker run -d --name campus-port-a -p 8081:9001 -e PORT=9001 campus-tasks:1.2
$ docker run -d --name campus-port-b -p 8082:9002 -e PORT=9002 campus-tasks:1.2
$ curl -s http://localhost:8081/health ; curl -s http://localhost:8082/health
{"status":"ok"}
{"status":"ok"}
campus-port-b | Up 15 seconds (healthy) | 0.0.0.0:8082->9002/tcp
campus-port-a | Up 16 seconds (healthy) | 0.0.0.0:8081->9001/tcp
```

Le `HEALTHCHECK` lit aussi `PORT`, donc il reste juste quel que soit le port choisi. Sans `PORT`, l'API écoute sur 8080.

### Panne de l'adresse d'écoute (démonstration non versionnée)

```
$ docker logs campus-127
 * Running on http://127.0.0.1:8080
$ docker ps --filter name=campus-127
campus-127 | Up 15 seconds (healthy)
$ curl -sS http://localhost:8083/health
curl: (56) Recv failure: Connection reset by peer
```

1. Le conteneur tourne et il est même `healthy`, car le `HEALTHCHECK` interroge `127.0.0.1` **depuis l'intérieur** du conteneur.
2. Mais l'application n'accepte que les connexions internes : la requête qui arrive de l'hôte par `-p` est refusée.
3. « Le conteneur tourne » n'est pas « le service répond » : il faut écouter sur `0.0.0.0`.

## Quiz de sortie

1. **Image et conteneur ?** L'image est un modèle immuable fait de couches ; le conteneur est une exécution de ce modèle, avec son propre processus et un système de fichiers jetable. On peut lancer plusieurs conteneurs depuis une seule image.
2. **Pourquoi un tag explicite plutôt que `latest` ?** `latest` n'est qu'un nom par défaut : il ne dit pas quelle version tourne. Un tag explicite (`1.1`) garantit que tout le monde exécute la même image.
3. **À quoi sert `.dockerignore` ?** Il retire des fichiers du contexte de build : build plus rapide, et aucun `.env` ni `.git/` copié par accident dans l'image.
4. **Pourquoi éviter root ?** Si l'application est compromise, l'attaquant n'obtient que les droits d'un compte ordinaire, et non root dans le conteneur.
5. **Que fait `-p 8080:80` ?** Il relie le port 8080 de l'hôte au port 80 du conteneur. Sans `-p`, personne à l'extérieur ne peut joindre le conteneur.
6. **Pourquoi copier `requirements.txt` avant le code ?** Les dépendances changent rarement : leur couche reste en cache, et une modification du code ne relance pas `pip install`.
