"""Test su creazione utenti e permessi per ruolo."""
from tests.conftest import registra


def test_admin_aggiunge_utente_con_ruolo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/utenti", json={
        "nome": "Luca", "email": "luca@a.it", "password": "password1", "ruolo": "operatore",
    }, headers=a)
    assert r.status_code == 201
    assert r.json()["ruolo"] == "operatore"


def test_operatore_non_puo_aggiungere_utenti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it", "password": "password1",
                                 "ruolo": "operatore"}, headers=a)
    tok = client.post("/auth/login", json={"email": "luca@a.it", "password": "password1"}).json()["access_token"]
    r = client.post("/utenti", json={"nome": "Y", "email": "y@a.it", "password": "password1"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_admin_cambia_ruolo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it", "password": "password1",
                                        "ruolo": "operatore"}, headers=a).json()
    r = client.patch(f"/utenti/{luca['id']}/ruolo", json={"ruolo": "caposquadra"}, headers=a)
    assert r.status_code == 200
    assert r.json()["ruolo"] == "caposquadra"
