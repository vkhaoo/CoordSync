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
