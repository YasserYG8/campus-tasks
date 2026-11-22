# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Campus Tasks is a teaching project for a series of DevOps workshops ("ateliers", L3 course). The app itself is deliberately tiny; the real deliverables are the Git workflow, Docker image, Compose stack and (next) CI/CD. All docs, code comments and commit messages are written in **French**.

Workshop flow (see `git log`):
- Each workshop is done on a branch `atelier-NN`, merged into `main` by pull request, and tagged `atelier-N` at the end.
- Each workshop has a report `docs/atelier-NN.md` with the same structure: "Ce qui a été livré" table, "Preuves" (real command output), the incident explanation, the "Défi final", and the "Quiz de sortie" answers.
- Workshop PDFs live in `sujets/`, which is git-ignored on purpose (course material, never versioned).
- Commit messages use Conventional Commits prefixes with a French description, e.g. `feat: lire le port d écoute dans la variable PORT`, `chore: ...`, `docs: ...`, `fix: ...`.

## Commands

There is no linter.

```bash
# Tests (pytest.ini adds app/ to the import path, so tests do `import app as campus`)
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
pytest -q tests/test_app.py::test_health_repond_ok   # single test

# Staging (atelier 5): pull the published image and check health — never rebuild
cp .env.staging.example .env.staging
printf 'IMAGE_TAG=v1.0.0\n' > .env.deploy
docker compose --env-file .env.deploy -f compose.staging.yaml up -d
./scripts/wait-healthy.sh   # exit 0 "staging sain", exit 1 "staging non sain"
# Rollback = put the previous IMAGE_TAG back in .env.deploy and run `up -d` again

# Repository hygiene check (required files exist, no tracked .env, clean working tree)
bash scripts/check-project.sh

# Run the API locally (Flask dev server, 0.0.0.0:$PORT, default 8080)
pip install -r requirements.txt
python app/app.py

# Docker image only
docker build -t campus-tasks:<version> .
docker run -d -p 8080:8080 -e PORT=8080 campus-tasks:<version>

# Full stack (api + PostgreSQL)
docker compose config --quiet          # validate before starting
docker compose up -d --build
docker compose --profile debug up -d   # also starts adminer on :8081
docker compose down                    # keeps the pgdata volume; `down -v` deletes data
```

Quick checks: `curl http://localhost:8080/health` and `curl http://localhost:8080/info`.

`scripts/check-project.sh` fails if the working tree has any uncommitted or untracked file, so commit (or ignore) everything before running it.

## Architecture

- `app/app.py` — the whole Flask app (only dependency: `Flask==3.1.0`).
  - `GET /health` always returns `{"status":"ok"}` and must **not** depend on the database (the Docker `HEALTHCHECK` and the upcoming CI/CD deployment rely on this).
  - `GET /info` reports `APP_ENV` and DB reachability; returns 503 if the DB is configured but unreachable.
  - DB "check" is only a TCP connection to `DB_HOST:DB_PORT` using the standard library — there is no real Postgres driver or ORM. If `DB_HOST` is unset, the DB is reported as "non configurée".
  - The server must listen on `0.0.0.0` (not `127.0.0.1`) or it will be unreachable through `-p` port mapping.
- Environment variables: `PORT` (default 8080), `APP_ENV` (default `dev`), `DB_HOST`, `DB_PORT` (default 5432). `.env` is git-ignored and docker-ignored; `.env.example` is the template.
- `Dockerfile` — `python:3.12-slim`; copies `requirements.txt` and installs it **before** copying `app/` to keep the pip layer cached; runs as non-root `appuser`; `HEALTHCHECK` calls `/health` on `$PORT`. Keep this order and these properties when editing.
- `.github/workflows/ci.yml` — `test` (pytest + `report.xml` artifact) → `docker-build` (`needs: test`; builds `campus-tasks:ci`, and only on a `v*` tag pushes `ghcr.io/<owner lowercased>/campus-tasks:<tag>`) → `deploy-staging` (tags only; pulls the published image, runs `compose.staging.yaml` and `wait-healthy.sh`). Release tags are immutable: a bad release gets a new tag (`v1.0.1`), never a moved one.
- `compose.staging.yaml` — staging uses the published image chosen by `IMAGE_TAG` from `.env.deploy`; `.env.staging` and `.env.deploy` are git-ignored. It also uses host port 8080, so stop the `compose.yaml` stack first.
- `compose.yaml` — `api` reaches Postgres by service name `db` (never `localhost` inside a container). Port 5432 is intentionally not published. `api` waits for `db` to be healthy (`pg_isready`). `adminer` is only in the `debug` profile. The DB password is a fake, local-only value.

## Environment note

The repo lives in WSL and may be accessed from Windows via `\\wsl.localhost\...`. In that case Git reports "dubious ownership"; use `git -c safe.directory='*' <cmd>` for one command instead of changing the global Git config.
