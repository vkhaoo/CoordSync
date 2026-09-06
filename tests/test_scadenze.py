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


# ---------- ANNULLATO ----------

def _base(client):
    from tests.conftest import registra
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    return a, p


def test_un_lavoro_si_puo_annullare(client):
    a, p = _base(client)
    l = client.post("/lavori", json={"titolo": "Sostituire il quadro",
                                     "progetto_id": p["id"]}, headers=a).json()

    r = client.patch(f"/lavori/{l['id']}/stato", json={"stato": "annullato"}, headers=a)
    assert r.status_code == 200 and r.json()["stato"] == "annullato"
    # Non e' "fatto": non deve risultare completato da nessuno.
    assert r.json()["completato_il"] is None and r.json()["completato_da"] is None


def test_annullare_un_lavoro_gia_fatto_toglie_il_completamento(client):
    a, p = _base(client)
    l = client.post("/lavori", json={"titolo": "X", "progetto_id": p["id"]}, headers=a).json()
    client.patch(f"/lavori/{l['id']}/stato", json={"stato": "fatto"}, headers=a)

    r = client.patch(f"/lavori/{l['id']}/stato", json={"stato": "annullato"}, headers=a)
    assert r.json()["completato_il"] is None


def test_la_scadenza_di_un_lavoro_annullato_non_suona_piu(client):
    """Un lavoro che si e' deciso di non fare non deve continuare a comparire
    in agenda come una cosa in ritardo."""
    from datetime import date, timedelta
    a, p = _base(client)
    domani = (date.today() + timedelta(days=1)).isoformat()
    l = client.post("/lavori", json={"titolo": "Da annullare", "progetto_id": p["id"],
                                     "data_scadenza": domani}, headers=a).json()

    dal = date.today().isoformat()
    al = (date.today() + timedelta(days=7)).isoformat()
    prima = client.get(f"/agenda?dal={dal}&al={al}&ambito=azienda", headers=a).json()
    assert [s["titolo"] for s in prima["scadenze"]] == ["Da annullare"]

    client.patch(f"/lavori/{l['id']}/stato", json={"stato": "annullato"}, headers=a)
    dopo = client.get(f"/agenda?dal={dal}&al={al}&ambito=azienda", headers=a).json()
    assert dopo["scadenze"] == []


def test_in_attesa_invece_la_scadenza_la_tiene(client):
    """Controprova: "in attesa" e' fermo ma vivo, e la sua scadenza conta."""
    from datetime import date, timedelta
    a, p = _base(client)
    domani = (date.today() + timedelta(days=1)).isoformat()
    l = client.post("/lavori", json={"titolo": "Ferma per pezzi", "progetto_id": p["id"],
                                     "data_scadenza": domani}, headers=a).json()
    client.patch(f"/lavori/{l['id']}/stato", json={"stato": "in_attesa"}, headers=a)

    dal = date.today().isoformat()
    al = (date.today() + timedelta(days=7)).isoformat()
    agenda = client.get(f"/agenda?dal={dal}&al={al}&ambito=azienda", headers=a).json()
    assert [s["titolo"] for s in agenda["scadenze"]] == ["Ferma per pezzi"]
