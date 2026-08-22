"""Test dell'assegnazione lavori a piu' persone (molti-a-molti)."""
from tests.conftest import registra


def _setup_lavoro(client, headers):
    prog = client.post("/progetti", json={"nome": "P"}, headers=headers).json()
    return client.post("/lavori", json={"titolo": "L", "progetto_id": prog["id"]},
                       headers=headers).json()


def test_assegna_e_rimuovi(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it", "password": "pw"}, headers=a).json()
    lav = _setup_lavoro(client, a)

    # assegno
    r = client.post(f"/lavori/{lav['id']}/assegnati", json={"utente_id": luca["id"]}, headers=a)
    assert r.status_code == 201
    assert [u["nome"] for u in r.json()["assegnatari"]] == ["Luca"]

    # rimuovo
    r = client.delete(f"/lavori/{lav['id']}/assegnati/{luca['id']}", headers=a)
    assert r.json()["assegnatari"] == []


def test_non_si_assegna_utente_di_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    b = registra(client, "Azienda B", "Sara", "sara@b.it")
    sara = client.get("/utenti", headers=b).json()[0]
    lav = _setup_lavoro(client, a)

    r = client.post(f"/lavori/{lav['id']}/assegnati", json={"utente_id": sara["id"]}, headers=a)
    assert r.status_code == 404
