# API

## Routes
- GET /health
- GET /info

Réponse attendue pour /health : HTTP 200.

Réponse de /info : nom de l'application, environnement (APP_ENV) et état de la base
(HTTP 200 si la base est joignable, HTTP 503 sinon).
