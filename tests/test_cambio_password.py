"""Test dell'obbligo di cambio password al primo accesso."""
from tests.conftest import registra
from app.security import crea_token_scopo


def _crea_da_admin(client, headers, email="luca@a.it"):
    return client.post("/utenti", json={
        "nome": "Luca", "email": email, "password": "password1", "ruolo": "operatore",
    }, headers=headers)


def _headers_login(client, email, password):
    tok = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_creato_da_admin_deve_cambiare_password(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = _crea_da_admin(client, a)
    assert r.status_code == 201
    assert r.json()["deve_cambiare_password"] is True


def test_admin_registrato_non_deve_cambiare(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    # Chi registra l'azienda la password l'ha scelta da solo.
    assert client.get("/auth/me", headers=a).json()["deve_cambiare_password"] is False


def test_invitato_non_deve_cambiare(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/utenti/invita", json={
        "nome": "Luca", "email": "luca@a.it", "ruolo": "operatore"}, headers=a)
    # L'invitato scegliera' comunque la password da solo: niente obbligo.
    assert r.json()["deve_cambiare_password"] is False


def test_cambio_password_azzera_flag(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_da_admin(client, a)
    h = _headers_login(client, "luca@a.it", "password1")

    r = client.post("/auth/cambia-password", json={
        "vecchia_password": "password1", "nuova_password": "sceltadame1"}, headers=h)
    assert r.status_code == 200

    # La vecchia non vale piu', la nuova si', e l'obbligo e' decaduto.
    assert client.post("/auth/login", json={
        "email": "luca@a.it", "password": "password1"}).status_code == 401
    h2 = _headers_login(client, "luca@a.it", "sceltadame1")
    assert client.get("/auth/me", headers=h2).json()["deve_cambiare_password"] is False


def test_cambio_password_rifiuta_vecchia_sbagliata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_da_admin(client, a)
    h = _headers_login(client, "luca@a.it", "password1")
    r = client.post("/auth/cambia-password", json={
        "vecchia_password": "sbagliata9", "nuova_password": "sceltadame1"}, headers=h)
    assert r.status_code == 401


def test_cambio_password_rifiuta_nuova_debole(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_da_admin(client, a)
    h = _headers_login(client, "luca@a.it", "password1")
    r = client.post("/auth/cambia-password", json={
        "vecchia_password": "password1", "nuova_password": "debole"}, headers=h)
    assert r.status_code == 422


def test_reset_password_azzera_flag(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_da_admin(client, a).json()
    # Anche col reset via email la password la sceglie lui: obbligo decaduto.
    token = crea_token_scopo(luca["id"], "reset_password", 60)
    client.post("/auth/reset-password", json={"token": token, "nuova_password": "sceltadame1"})
    h = _headers_login(client, "luca@a.it", "sceltadame1")
    assert client.get("/auth/me", headers=h).json()["deve_cambiare_password"] is False
