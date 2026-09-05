"""Test di registrazione e login."""
from tests.conftest import registra


def test_registrazione_crea_azienda_e_da_un_token(client):
    r = client.post("/auth/register", json={
        "nome_azienda": "Azienda A", "nome": "Marco",
        "email": "marco@a.it", "password": "password1",
    })
    assert r.status_code == 201
    assert "access_token" in r.json()


def test_registrazione_rifiuta_email_duplicata(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/auth/register", json={
        "nome_azienda": "Azienda B", "nome": "Altro",
        "email": "marco@a.it", "password": "password1",
    })
    assert r.status_code == 409


def test_login_con_password_giusta(client):
    registra(client, "Azienda A", "Marco", "marco@a.it", password="segreta12")
    r = client.post("/auth/login", json={"email": "marco@a.it", "password": "segreta12"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_con_password_sbagliata(client):
    registra(client, "Azienda A", "Marco", "marco@a.it", password="segreta12")
    r = client.post("/auth/login", json={"email": "marco@a.it", "password": "sbagliata"})
    assert r.status_code == 401


def test_registrazione_rifiuta_password_debole(client):
    # troppo corta e senza numero -> deve fallire con 422
    r = client.post("/auth/register", json={
        "nome_azienda": "Azienda A", "nome": "Marco",
        "email": "marco@a.it", "password": "abc",
    })
    assert r.status_code == 422


def test_un_token_di_scopo_non_vale_come_accesso(client):
    """Buco chiuso il 5 settembre 2026.

    I link di invito, reset password e verifica email portano un token
    firmato con la stessa chiave dei token di accesso. Senza un controllo
    esplicito, quel token apriva l'account per intero: un invito, che vive
    sette giorni, valeva quanto una password. Ora chi ha uno "scopo" viene
    rifiutato dalla guardia.
    """
    from app.security import crea_token_scopo

    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    io = client.get("/auth/me", headers=a).json()

    for scopo in ("invito", "reset_password", "verifica_email", "attesa_2fa"):
        finto = crea_token_scopo(io["id"], scopo, 60)
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {finto}"})
        assert r.status_code == 401, f"il token di scopo '{scopo}' apre l'account"
