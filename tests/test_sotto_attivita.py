"""Test delle sotto-attivita' (checklist)."""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_crea_ed_elenca(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    r = client.post(f"/lavori/{l['id']}/sotto-attivita", json={"testo": "Passo 1"}, headers=a)
    assert r.status_code == 201
    assert r.json()["completata"] is False

    lista = client.get(f"/lavori/{l['id']}/sotto-attivita", headers=a).json()
    assert len(lista) == 1


def test_spunta_e_elimina(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    voce = client.post(f"/lavori/{l['id']}/sotto-attivita", json={"testo": "X"}, headers=a).json()

    # spunto
    r = client.patch(f"/sotto-attivita/{voce['id']}", json={"completata": True}, headers=a)
    assert r.status_code == 200 and r.json()["completata"] is True

    # elimino
    assert client.delete(f"/sotto-attivita/{voce['id']}", headers=a).status_code == 204
    assert client.get(f"/lavori/{l['id']}/sotto-attivita", headers=a).json() == []


def test_operatore_non_crea_ma_spunta_se_assegnato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Op", "email": "op@a.it", "password": "password1",
                                 "ruolo": "operatore"}, headers=a)
    op = _login(client, "op@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    voce = client.post(f"/lavori/{l['id']}/sotto-attivita", json={"testo": "X"}, headers=a).json()

    # operatore NON puo' creare
    assert client.post(f"/lavori/{l['id']}/sotto-attivita", json={"testo": "Y"}, headers=op).status_code == 403
    # operatore NON assegnato non puo' spuntare
    assert client.patch(f"/sotto-attivita/{voce['id']}", json={"completata": True}, headers=op).status_code == 403
    # assegno l'operatore, ora puo' spuntare
    op_id = [u for u in client.get("/utenti", headers=a).json() if u["email"] == "op@a.it"][0]["id"]
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": op_id}, headers=a)
    assert client.patch(f"/sotto-attivita/{voce['id']}", json={"completata": True}, headers=op).status_code == 200
