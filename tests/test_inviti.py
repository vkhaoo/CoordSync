"""Test del flusso di invito via email (onboarding 'da SaaS')."""
from tests.conftest import registra
from app.security import crea_token_scopo


def _invita(client, headers, nome="Luca", email="luca@a.it", ruolo="operatore"):
    return client.post("/utenti/invita", json={
        "nome": nome, "email": email, "ruolo": ruolo,
    }, headers=headers)


def test_invito_crea_utente_senza_password(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = _invita(client, a)
    assert r.status_code == 201
    assert r.json()["ruolo"] == "operatore"
    assert r.json()["email_verificata"] is False
    # Senza password il login e' impossibile, con qualunque password.
    assert client.post("/auth/login", json={
        "email": "luca@a.it", "password": "password1"}).status_code == 401


def test_accetta_invito_imposta_password_e_verifica_email(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    invitato = _invita(client, a).json()

    token = crea_token_scopo(invitato["id"], "invito", 60)
    r = client.post("/auth/accetta-invito", json={"token": token, "password": "sceltadame1"})
    assert r.status_code == 200

    # Ora il login funziona e l'email risulta verificata (l'invito la prova gia').
    login = client.post("/auth/login", json={"email": "luca@a.it", "password": "sceltadame1"})
    assert login.status_code == 200
    me = client.get("/auth/me", headers={
        "Authorization": f"Bearer {login.json()['access_token']}"}).json()
    assert me["email_verificata"] is True


def test_accetta_invito_rifiuta_token_scopo_sbagliato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    invitato = _invita(client, a).json()
    # Un token di reset password non deve valere come invito.
    token = crea_token_scopo(invitato["id"], "reset_password", 60)
    r = client.post("/auth/accetta-invito", json={"token": token, "password": "sceltadame1"})
    assert r.status_code == 400


def test_invito_non_riutilizzabile(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    invitato = _invita(client, a).json()
    token = crea_token_scopo(invitato["id"], "invito", 60)
    assert client.post("/auth/accetta-invito",
                       json={"token": token, "password": "sceltadame1"}).status_code == 200
    # Secondo uso dello stesso invito: rifiutato (la password c'e' gia').
    assert client.post("/auth/accetta-invito",
                       json={"token": token, "password": "altrapassword2"}).status_code == 400


def test_accetta_invito_rifiuta_password_debole(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    invitato = _invita(client, a).json()
    token = crea_token_scopo(invitato["id"], "invito", 60)
    r = client.post("/auth/accetta-invito", json={"token": token, "password": "debole"})
    assert r.status_code == 422


def test_operatore_non_puo_invitare(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it",
                                 "password": "password1", "ruolo": "operatore"}, headers=a)
    tok = client.post("/auth/login", json={
        "email": "luca@a.it", "password": "password1"}).json()["access_token"]
    r = _invita(client, {"Authorization": f"Bearer {tok}"}, email="y@a.it")
    assert r.status_code == 403


def test_invito_email_gia_registrata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert _invita(client, a).status_code == 201
    assert _invita(client, a).status_code == 409
