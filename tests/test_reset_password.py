"""Test del flusso di recupero password."""
from tests.conftest import registra
from app.security import crea_token_scopo


def test_richiedi_reset_sempre_ok(client):
    # anche con email inesistente, rispondiamo 202 (no email enumeration)
    r = client.post("/auth/richiedi-reset", json={"email": "nessuno@x.it"})
    assert r.status_code == 202


def test_reset_password_completo(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    me = client.get("/auth/me", headers=login_headers(client, "marco@a.it", "password1")).json()

    # genero un token di reset valido e imposto una nuova password
    token = crea_token_scopo(me["id"], "reset_password", 60)
    r = client.post("/auth/reset-password", json={"token": token, "nuova_password": "nuovapass9"})
    assert r.status_code == 200

    # la vecchia password non funziona piu', la nuova si'
    assert client.post("/auth/login", json={"email": "marco@a.it", "password": "password1"}).status_code == 401
    assert client.post("/auth/login", json={"email": "marco@a.it", "password": "nuovapass9"}).status_code == 200


def test_reset_rifiuta_password_debole(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    me = client.get("/auth/me", headers=login_headers(client, "marco@a.it", "password1")).json()
    token = crea_token_scopo(me["id"], "reset_password", 60)
    r = client.post("/auth/reset-password", json={"token": token, "nuova_password": "debole"})
    assert r.status_code == 422


def test_reset_rifiuta_token_scopo_sbagliato(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    me = client.get("/auth/me", headers=login_headers(client, "marco@a.it", "password1")).json()
    # un token con scopo diverso non deve valere per il reset
    token = crea_token_scopo(me["id"], "verifica_email", 60)
    r = client.post("/auth/reset-password", json={"token": token, "nuova_password": "nuovapass9"})
    assert r.status_code == 400


def login_headers(client, email, password):
    tok = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}
