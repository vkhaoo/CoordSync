"""Test della data di scadenza sui lavori."""
from tests.conftest import registra


def _progetto(client, headers):
    return client.post("/progetti", json={"nome": "Quadro A"}, headers=headers).json()


def test_crea_lavoro_con_scadenza(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto(client, a)
    r = client.post("/lavori", json={
        "titolo": "Cablaggio", "progetto_id": p["id"], "data_scadenza": "2026-09-15",
    }, headers=a)
    assert r.status_code == 201
    assert r.json()["data_scadenza"] == "2026-09-15"
    # E il campo torna anche in lettura dall'elenco.
    lavori = client.get(f"/lavori?progetto_id={p['id']}", headers=a).json()
    assert lavori[0]["data_scadenza"] == "2026-09-15"


def test_lavoro_senza_scadenza(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto(client, a)
    r = client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p["id"]}, headers=a)
    assert r.status_code == 201
    assert r.json()["data_scadenza"] is None


def test_modifica_imposta_e_toglie_scadenza(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto(client, a)
    lavoro = client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p["id"]},
                         headers=a).json()

    r = client.patch(f"/lavori/{lavoro['id']}", json={"data_scadenza": "2026-10-01"}, headers=a)
    assert r.status_code == 200
    assert r.json()["data_scadenza"] == "2026-10-01"

    # Inviare esplicitamente null toglie la scadenza.
    r = client.patch(f"/lavori/{lavoro['id']}", json={"data_scadenza": None}, headers=a)
    assert r.status_code == 200
    assert r.json()["data_scadenza"] is None


def test_scadenza_data_invalida(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto(client, a)
    r = client.post("/lavori", json={
        "titolo": "Cablaggio", "progetto_id": p["id"], "data_scadenza": "non-una-data",
    }, headers=a)
    assert r.status_code == 422
