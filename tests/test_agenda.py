"""
Test dell'agenda: impegni con data e ora, piu' le scadenze in sovrapposizione.

Il punto da proteggere: l'agenda e' personale, e non deve diventare una
scorciatoia per vedere lavori di reparti che altrimenti non vedrei.
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


OGGI = date.today()
DOMANI = OGGI + timedelta(days=1)


def _quando(giorno=DOMANI, ora=9):
    return datetime.combine(giorno, datetime.min.time()).replace(hour=ora).isoformat()


def _finestra(giorni=30):
    return f"dal={OGGI - timedelta(days=1)}&al={OGGI + timedelta(days=giorni)}"


# ---------- IMPEGNI ----------

def test_creo_un_impegno_con_ora(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/agenda", json={
        "titolo": "Intervento cliente Rossi", "luogo": "Stabilimento Rossi",
        "inizio": _quando(ora=9), "fine": _quando(ora=12),
    }, headers=a)
    assert r.status_code == 201
    assert r.json()["titolo"] == "Intervento cliente Rossi"
    assert r.json()["inizio"].startswith(str(DOMANI))
    assert r.json()["utente"]["nome"] == "Marco"


def test_fine_prima_dell_inizio_rifiutata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/agenda", json={"titolo": "X", "inizio": _quando(ora=14),
                                     "fine": _quando(ora=9)}, headers=a)
    assert r.status_code == 422


def test_vedo_solo_i_miei_impegni(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    client.post("/agenda", json={"titolo": "Mio di Marco", "inizio": _quando()}, headers=a)
    client.post("/agenda", json={"titolo": "Mio di Luca", "inizio": _quando()}, headers=luca)

    miei = client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()
    assert [i["titolo"] for i in miei["impegni"]] == ["Mio di Luca"]


def test_ambito_reparto_mostra_i_colleghi_del_reparto(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, a, "Anna", "anna@a.it", "caposquadra")
    dino = _crea_utente(client, a, "Dino", "dino@a.it", "caposquadra")
    rep = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    for email in ["anna@a.it", "dino@a.it"]:
        client.post(f"/reparti/{rep['id']}/membri",
                    json={"utente_id": _id_utente(client, a, email)}, headers=a)

    client.post("/agenda", json={"titolo": "Di Dino", "inizio": _quando()}, headers=dino)
    client.post("/agenda", json={"titolo": "Di Marco", "inizio": _quando()}, headers=a)

    # Anna divide il reparto con Dino, non con Marco (che non e' nel reparto).
    titoli = {i["titolo"] for i in
              client.get(f"/agenda?{_finestra()}&ambito=reparto", headers=anna).json()["impegni"]}
    assert "Di Dino" in titoli and "Di Marco" not in titoli


def test_caposquadra_mette_un_impegno_a_un_collega(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    luca_id = _id_utente(client, a, "luca@a.it")

    r = client.post("/agenda", json={"titolo": "Vai dal cliente", "inizio": _quando(),
                                     "utente_id": luca_id}, headers=a)
    assert r.status_code == 201 and r.json()["utente"]["nome"] == "Luca"
    # E Luca se lo ritrova nella SUA agenda.
    miei = client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()
    assert [i["titolo"] for i in miei["impegni"]] == ["Vai dal cliente"]


def test_operatore_non_mette_impegni_ad_altri(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    marco_id = _id_utente(client, a, "marco@a.it")
    r = client.post("/agenda", json={"titolo": "X", "inizio": _quando(),
                                     "utente_id": marco_id}, headers=luca)
    assert r.status_code == 403


def test_non_modifico_l_impegno_di_un_collega(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    mio = client.post("/agenda", json={"titolo": "Mio", "inizio": _quando()}, headers=a).json()

    assert client.patch(f"/agenda/{mio['id']}", json={"titolo": "X"}, headers=luca).status_code == 403
    assert client.delete(f"/agenda/{mio['id']}", headers=luca).status_code == 403


def test_impegni_isolati_fra_aziende(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    mio = client.post("/agenda", json={"titolo": "Mio", "inizio": _quando()}, headers=a).json()
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    assert client.get(f"/agenda?{_finestra()}&ambito=azienda", headers=altra).json()["impegni"] == []
    assert client.patch(f"/agenda/{mio['id']}", json={"titolo": "X"}, headers=altra).status_code == 404


def test_prossimi_impegni(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/agenda", json={"titolo": "Vicino", "inizio": _quando(DOMANI)}, headers=a)
    client.post("/agenda", json={"titolo": "Lontano",
                                 "inizio": _quando(OGGI + timedelta(days=40))}, headers=a)
    prossimi = client.get("/agenda/prossimi?giorni=7", headers=a).json()
    assert [i["titolo"] for i in prossimi] == ["Vicino"]


def test_cambiare_orario_riarma_il_promemoria(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    i = client.post("/agenda", json={"titolo": "X", "inizio": _quando(),
                                     "promemoria_minuti": 60}, headers=a).json()
    assert i["promemoria_minuti"] == 60
    r = client.patch(f"/agenda/{i['id']}", json={"inizio": _quando(ora=15)}, headers=a)
    assert r.status_code == 200


# ---------- SCADENZE IN SOVRAPPOSIZIONE ----------

def test_le_scadenze_compaiono_nell_agenda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p["id"],
                                 "data_scadenza": str(DOMANI)}, headers=a)

    agenda = client.get(f"/agenda?{_finestra()}&ambito=azienda", headers=a).json()
    assert [s["titolo"] for s in agenda["scadenze"]] == ["Cablaggio"]
    assert agenda["scadenze"][0]["progetto"] == "P"


def test_i_lavori_conclusi_non_ingombrano_l_agenda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Fatto", "progetto_id": p["id"],
                                     "data_scadenza": str(DOMANI)}, headers=a).json()
    client.patch(f"/lavori/{l['id']}/stato", json={"stato": "fatto"}, headers=a)

    agenda = client.get(f"/agenda?{_finestra()}&ambito=azienda", headers=a).json()
    assert agenda["scadenze"] == []


def test_ambito_miei_mostra_solo_le_scadenze_a_me_assegnate(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    mio = client.post("/lavori", json={"titolo": "Assegnato a Luca", "progetto_id": p["id"],
                                       "data_scadenza": str(DOMANI)}, headers=a).json()
    client.post("/lavori", json={"titolo": "Di nessuno", "progetto_id": p["id"],
                                 "data_scadenza": str(DOMANI)}, headers=a)
    client.post(f"/lavori/{mio['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "luca@a.it")}, headers=a)

    miei = client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()
    assert [s["titolo"] for s in miei["scadenze"]] == ["Assegnato a Luca"]
    assert miei["scadenze"][0]["mia"] is True


def test_l_agenda_non_aggira_i_reparti(client):
    """Il punto piu' importante: le scadenze in agenda sono solo quelle dei
    lavori che gia' potrei vedere altrove."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    dino = _crea_utente(client, a, "Dino", "dino@a.it", "caposquadra")
    rep = client.post("/reparti", json={"nome": "Riservato"}, headers=a).json()
    p = client.post("/progetti", json={"nome": "Segreto", "reparti_ids": [rep["id"]]},
                    headers=a).json()
    client.post("/lavori", json={"titolo": "Non deve vedersi", "progetto_id": p["id"],
                                 "data_scadenza": str(DOMANI)}, headers=a)

    # Dino non e' nel reparto: nemmeno chiedendo "tutta l'azienda".
    agenda = client.get(f"/agenda?{_finestra()}&ambito=azienda", headers=dino).json()
    assert agenda["scadenze"] == []


def test_intervallo_rispettato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/agenda", json={"titolo": "Dentro", "inizio": _quando(DOMANI)}, headers=a)
    client.post("/agenda", json={"titolo": "Fuori",
                                 "inizio": _quando(OGGI + timedelta(days=20))}, headers=a)

    stretta = client.get(f"dal={OGGI}&al={OGGI + timedelta(days=2)}".join(["/agenda?", ""]),
                         headers=a).json()
    assert [i["titolo"] for i in stretta["impegni"]] == ["Dentro"]


def test_intervallo_invertito_rifiutato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.get(f"/agenda?dal={OGGI}&al={OGGI - timedelta(days=5)}", headers=a)
    assert r.status_code == 422


def test_collegamenti_solo_a_cose_che_vedo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = client.post("/macchine", json={"nome": "Pressa"}, headers=a).json()
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    # Collegare la macchina di un'altra azienda non si puo'.
    r = client.post("/agenda", json={"titolo": "X", "inizio": _quando(),
                                     "macchina_id": m["id"]}, headers=altra)
    assert r.status_code == 404
    # Ma nella mia azienda funziona.
    ok = client.post("/agenda", json={"titolo": "Intervento sulla pressa",
                                      "inizio": _quando(), "macchina_id": m["id"]}, headers=a)
    assert ok.status_code == 201 and ok.json()["macchina_id"] == m["id"]
