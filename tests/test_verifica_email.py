"""Test del flusso di verifica email."""
from tests.conftest import registra
from app.security import crea_token_scopo


def test_nuovo_utente_non_verificato(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    # /me deve dire email_verificata = False appena registrato
    tok = client.post("/auth/login", json={"email": "marco@a.it", "password": "password1"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me["email_verificata"] is False


def test_verifica_con_token_valido(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    tok = client.post("/auth/login", json={"email": "marco@a.it", "password": "password1"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()

    # genero un token di verifica valido per quell'utente e "clicco" il link
    token_verifica = crea_token_scopo(me["id"], "verifica_email", 60)
    r = client.get(f"/auth/verifica-email?token={token_verifica}")
    assert r.status_code == 200

    # ora /me deve dire verificata = True
    me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me2["email_verificata"] is True


def test_verifica_con_token_scopo_sbagliato(client):
    # un token di LOGIN non deve valere come verifica email
    registra(client, "Azienda A", "Marco", "marco@a.it")
    tok = client.post("/auth/login", json={"email": "marco@a.it", "password": "password1"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
    token_sbagliato = crea_token_scopo(me["id"], "scopo_diverso", 60)
    r = client.get(f"/auth/verifica-email?token={token_sbagliato}")
    assert r.status_code == 400
