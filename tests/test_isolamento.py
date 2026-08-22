"""Test che le aziende siano davvero separate."""
from tests.conftest import registra


def test_ogni_azienda_vede_solo_i_propri_progetti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    b = registra(client, "Azienda B", "Sara", "sara@b.it")
    client.post("/progetti", json={"nome": "Progetto A"}, headers=a)
    client.post("/progetti", json={"nome": "Progetto B"}, headers=b)

    visti_da_a = [p["nome"] for p in client.get("/progetti", headers=a).json()]
    visti_da_b = [p["nome"] for p in client.get("/progetti", headers=b).json()]
    assert visti_da_a == ["Progetto A"]
    assert visti_da_b == ["Progetto B"]


def test_senza_token_accesso_negato(client):
    r = client.get("/progetti")
    assert r.status_code in (401, 403)


def test_non_si_toccano_i_dati_di_un_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    b = registra(client, "Azienda B", "Sara", "sara@b.it")
    prog_b = client.post("/progetti", json={"nome": "Progetto B"}, headers=b).json()

    # Marco (A) prova ad aggiungere un lavoro al progetto di Sara (B): deve fallire.
    r = client.post("/lavori", json={"titolo": "intruso", "progetto_id": prog_b["id"]}, headers=a)
    assert r.status_code == 404
