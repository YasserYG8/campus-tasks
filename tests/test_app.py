import pytest

import app as campus


@pytest.fixture
def client():
    return campus.app.test_client()


def test_health_repond_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_health_ne_depend_pas_de_la_base(client, monkeypatch):
    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setattr(campus, "check_db", lambda: (False, "db:5432 injoignable"))
    assert client.get("/health").status_code == 200


def test_info_sans_base_configuree(client, monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    resp = client.get("/info")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["app"] == "campus-tasks"
    assert body["env"] == "test"
    assert body["db"] == "non configurée"


def test_info_base_injoignable_renvoie_503(client, monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError(111, "Connection refused")

    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setattr(campus.socket, "create_connection", refuse)
    resp = client.get("/info")
    assert resp.status_code == 503
    assert resp.get_json()["db"] == "erreur"


def test_info_base_joignable(client, monkeypatch):
    class FausseConnexion:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setattr(campus.socket, "create_connection", lambda *a, **k: FausseConnexion())
    resp = client.get("/info")
    assert resp.status_code == 200
    assert resp.get_json()["db"] == "ok"
