"""
Esportazione dei propri dati (portabilita').

Il punto da proteggere: l'export contiene la roba di CHI LO CHIEDE, e non
diventa una scorciatoia per portarsi via i dati dei colleghi o dell'azienda.
"""
from datetime import date, datetime, timedelta

from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


def _id_utente(client, admin, email):
    return [u for u in client.get("/utenti", headers=admin).json() if u["email"] == email][0]["id"]


def test_serve_essere_loggati(client):
    assert client.get("/auth/me/export").status_code == 403


def test_l_export_contiene_il_profilo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    rep = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    client.post(f"/reparti/{rep['id']}/membri",
                json={"utente_id": _id_utente(client, a, "marco@a.it")}, headers=a)

    dati = client.get("/auth/me/export", headers=a).json()
    assert dati["profilo"]["nome"] == "Marco"
    assert dati["profilo"]["email"] == "marco@a.it"
    assert dati["profilo"]["azienda"] == "Azienda A"
    assert dati["profilo"]["reparti"] == ["Automazione"]
    assert "esportato_il" in dati


def test_la_password_non_esce_mai(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    grezzo = client.get("/auth/me/export", headers=a).text.lower()
    assert "password" not in grezzo
    assert "hash" not in grezzo


def test_ci_sono_i_miei_lavori_commenti_e_agenda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Quadro"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p["id"],
                                     "data_scadenza": str(date.today())}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "marco@a.it")}, headers=a)
    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "nota mia"}, headers=a)

    quando = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
    client.post("/agenda", json={"titolo": "Intervento", "inizio": quando}, headers=a)

    m = client.post("/macchine", json={"nome": "Pressa"}, headers=a).json()
    client.post(f"/macchine/{m['id']}/voci", json={"tipo": "modifica",
                                                   "titolo": "Sostituito sensore"}, headers=a)
    client.post(f"/macchine/{m['id']}/allegati", json={"url": "https://x.it",
                                                       "titolo": "Schema"}, headers=a)

    dati = client.get("/auth/me/export", headers=a).json()
    assert [x["titolo"] for x in dati["lavori_assegnati"]] == ["Cablaggio"]
    assert dati["lavori_assegnati"][0]["progetto"] == "Quadro"
    assert [c["testo"] for c in dati["commenti_scritti"]] == ["nota mia"]
    assert [v["titolo"] for v in dati["voci_di_storico_scritte"]] == ["Sostituito sensore"]
    assert [x["titolo"] for x in dati["link_aggiunti"]] == ["Schema"]
    assert [i["titolo"] for i in dati["agenda"]] == ["Intervento"]


def test_non_mi_porto_via_la_roba_dei_colleghi(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Non mio", "progetto_id": p["id"]},
                    headers=a).json()
    # il lavoro e' assegnato a Marco, il commento lo scrive Marco
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "marco@a.it")}, headers=a)
    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "roba di Marco"}, headers=a)

    dati = client.get("/auth/me/export", headers=luca).json()
    assert dati["lavori_assegnati"] == []
    assert dati["commenti_scritti"] == []
    assert "roba di Marco" not in client.get("/auth/me/export", headers=luca).text


def test_ci_sono_gli_avvisi_ricevuti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "luca@a.it")}, headers=a)

    dati = client.get("/auth/me/export", headers=luca).json()
    assert len(dati["avvisi_ricevuti"]) == 1
    assert "assegnato" in dati["avvisi_ricevuti"][0]["testo"]


def test_una_riunione_compare_a_tutti_i_partecipanti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    quando = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
    ids = [_id_utente(client, a, e) for e in ("marco@a.it", "luca@a.it")]
    client.post("/agenda", json={"titolo": "Riunione", "inizio": quando,
                                 "partecipanti_ids": ids}, headers=a)

    for chi in (a, luca):
        dati = client.get("/auth/me/export", headers=chi).json()
        assert [i["titolo"] for i in dati["agenda"]] == ["Riunione"]
        assert set(dati["agenda"][0]["partecipanti"]) == {"Marco", "Luca"}
