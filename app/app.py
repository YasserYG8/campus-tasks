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
