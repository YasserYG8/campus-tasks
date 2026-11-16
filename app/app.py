
import logging
import os
import socket

from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("campus-tasks")

app = Flask(__name__)


def check_db():
    """Tente une connexion TCP vers DB_HOST:DB_PORT.

    Renvoie (None, ...) si aucune base n'est configurée,
    (True, ...) si elle est joignable, (False, ...) sinon.
    """
    host = os.environ.get("DB_HOST")
    if not host:
        return None, "DB_HOST non défini"
    port = int(os.environ.get("DB_PORT", "5432"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True, f"{host}:{port} joignable"
    except OSError as exc:
        return False, f"{host}:{port} injoignable ({exc})"


@app.get("/health")
def health():
    # Santé du processus web uniquement : ne dépend pas de la base
    return jsonify(status="ok")


@app.get("/info")
def info():
    ok, detail = check_db()
    db = "non configurée" if ok is None else ("ok" if ok else "erreur")
    body = {
        "app": "campus-tasks",
        "env": os.environ.get("APP_ENV", "dev"),
        "db": db,
        "db_detail": detail,
    }
    return jsonify(body), (503 if ok is False else 200)


if __name__ == "__main__":
    ok, detail = check_db()
    if ok:
        log.info("base de données : %s", detail)
    elif ok is False:
        log.error("base de données : %s", detail)
        
import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    # 0.0.0.0 : accepter les connexions venant de l'extérieur du conteneur
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
