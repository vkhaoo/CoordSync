"""Test su creazione utenti e permessi admin."""
from tests.conftest import registra


def test_admin_aggiunge_utente_che_eredita_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it", "password": "pw"}, headers=a)
    assert r.status_code == 201
    assert r.json()["is_admin"] is False   # un utente aggiunto NON e' admin


def test_non_admin_non_puo_aggiungere_utenti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it", "password": "pw"}, headers=a)

    # Luca (non admin) fa login e prova ad aggiungere un utente.
    tok = client.post("/auth/login", json={"email": "luca@a.it", "password": "pw"}).json()["access_token"]
    r = client.post("/utenti", json={"nome": "Y", "email": "y@a.it", "password": "pw"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
