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
    assert r.json()["organizzatore"]["nome"] == "Marco"


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
                                     "partecipanti_ids": [luca_id]}, headers=a)
    assert r.status_code == 201
    assert [p["nome"] for p in r.json()["partecipanti"]] == ["Luca"]
    # E Luca se lo ritrova nella SUA agenda.
    miei = client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()
    assert [i["titolo"] for i in miei["impegni"]] == ["Vai dal cliente"]


def test_operatore_non_mette_impegni_ad_altri(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    marco_id = _id_utente(client, a, "marco@a.it")
    r = client.post("/agenda", json={"titolo": "X", "inizio": _quando(),
                                     "partecipanti_ids": [marco_id]}, headers=luca)
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


# ---------- RIUNIONI: UN IMPEGNO, PIU' PARTECIPANTI ----------

def test_riunione_compare_nell_agenda_di_tutti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, a, "Anna", "anna@a.it", "caposquadra")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    ids = [_id_utente(client, a, e) for e in ("marco@a.it", "anna@a.it", "luca@a.it")]

    r = client.post("/agenda", json={
        "titolo": "Riunione di cantiere", "luogo": "Sala riunioni",
        "inizio": _quando(ora=10), "partecipanti_ids": ids,
    }, headers=a)
    assert r.status_code == 201
    assert {p["nome"] for p in r.json()["partecipanti"]} == {"Marco", "Anna", "Luca"}

    # La stessa riunione, non tre copie: stesso id per tutti.
    for chi in (a, anna, luca):
        miei = client.get(f"/agenda?{_finestra()}&ambito=miei", headers=chi).json()["impegni"]
        assert len(miei) == 1
        assert miei[0]["id"] == r.json()["id"]
        assert miei[0]["titolo"] == "Riunione di cantiere"


def test_spostare_la_riunione_la_sposta_per_tutti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    ids = [_id_utente(client, a, e) for e in ("marco@a.it", "luca@a.it")]
    riunione = client.post("/agenda", json={"titolo": "R", "inizio": _quando(ora=9),
                                            "partecipanti_ids": ids}, headers=a).json()

    client.patch(f"/agenda/{riunione['id']}", json={"inizio": _quando(ora=16)}, headers=a)
    # Luca vede il nuovo orario senza che nessuno abbia toccato una sua copia.
    suo = client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()["impegni"][0]
    assert suo["inizio"].endswith("16:00:00")


def test_un_invitato_non_sposta_la_riunione_agli_altri(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    ids = [_id_utente(client, a, e) for e in ("marco@a.it", "luca@a.it")]
    riunione = client.post("/agenda", json={"titolo": "R", "inizio": _quando(),
                                            "partecipanti_ids": ids}, headers=a).json()

    assert client.patch(f"/agenda/{riunione['id']}", json={"titolo": "X"},
                        headers=luca).status_code == 403
    assert client.delete(f"/agenda/{riunione['id']}", headers=luca).status_code == 403


def test_posso_aggiungere_e_togliere_partecipanti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_utente(client, a, "Anna", "anna@a.it", "caposquadra")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    marco_id = _id_utente(client, a, "marco@a.it")
    anna_id = _id_utente(client, a, "anna@a.it")
    luca_id = _id_utente(client, a, "luca@a.it")

    riunione = client.post("/agenda", json={"titolo": "R", "inizio": _quando(),
                                            "partecipanti_ids": [marco_id]}, headers=a).json()
    # aggiungo Anna e Luca
    r = client.patch(f"/agenda/{riunione['id']}",
                     json={"partecipanti_ids": [marco_id, anna_id, luca_id]}, headers=a)
    assert len(r.json()["partecipanti"]) == 3
    assert len(client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()["impegni"]) == 1

    # tolgo Luca: sparisce dalla sua agenda, la riunione resta agli altri
    r = client.patch(f"/agenda/{riunione['id']}",
                     json={"partecipanti_ids": [marco_id, anna_id]}, headers=a)
    assert len(r.json()["partecipanti"]) == 2
    assert client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()["impegni"] == []


def test_riunione_senza_partecipanti_rifiutata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    i = client.post("/agenda", json={"titolo": "R", "inizio": _quando()}, headers=a).json()
    assert client.patch(f"/agenda/{i['id']}", json={"partecipanti_ids": []},
                        headers=a).status_code == 422


def test_non_posso_invitare_uno_di_un_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    registra(client, "Azienda B", "Bruno", "bruno@b.it")
    tok = client.post("/auth/login", json={"email": "bruno@b.it", "password": "password1"}).json()["access_token"]
    bruno = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
    marco_id = _id_utente(client, a, "marco@a.it")

    r = client.post("/agenda", json={"titolo": "R", "inizio": _quando(),
                                     "partecipanti_ids": [marco_id, bruno["id"]]}, headers=a)
    assert r.status_code == 404
    # e non e' stata creata a meta'
    assert client.get(f"/agenda?{_finestra()}&ambito=azienda", headers=a).json()["impegni"] == []


def test_senza_indicazioni_l_impegno_e_solo_mio(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    r = client.post("/agenda", json={"titolo": "Solo mio", "inizio": _quando()}, headers=a)
    assert [p["nome"] for p in r.json()["partecipanti"]] == ["Marco"]
    assert client.get(f"/agenda?{_finestra()}&ambito=miei", headers=luca).json()["impegni"] == []
