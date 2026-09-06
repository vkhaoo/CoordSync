"""
Test degli impegni che si ripetono.

Le occorrenze sono impegni VERI, uno per data, legati da un numero di serie:
non una regola salvata da qualche parte. Quindi qui si verifica soprattutto
che ognuna sia una cosa a se' — si sposta da sola, si cancella da sola — e che
il tetto al numero di righe regga davvero.
"""
from datetime import datetime, timedelta

from tests.conftest import registra
from app.ricorrenze import date_successive, MASSIMO


def _quando(giorno=10, mese=3, ora=9):
    return datetime(2026, mese, giorno, ora, 0)


def _crea(client, headers, **extra):
    corpo = {"titolo": "Manutenzione settimanale",
             "inizio": _quando().isoformat(), **extra}
    return client.post("/agenda", json=corpo, headers=headers)


def _agenda(client, headers, dal, al):
    return client.get(f"/agenda?dal={dal}&al={al}&ambito=miei", headers=headers).json()


# ---------- IL CALCOLO DELLE DATE (senza database) ----------

def test_settimanale_conta_di_sette_in_sette():
    date = date_successive(_quando(), "settimanale", _quando() + timedelta(days=21))
    assert [d.day for d in date] == [17, 24, 31]


def test_l_ora_non_si_muove():
    date = date_successive(_quando(ora=14), "quindicinale", _quando(ora=14) + timedelta(days=30))
    assert all(d.hour == 14 for d in date)


def test_il_mensile_tiene_il_giorno_del_mese():
    date = date_successive(datetime(2026, 1, 15, 9), "mensile", datetime(2026, 4, 30, 9))
    assert [(d.month, d.day) for d in date] == [(2, 15), (3, 15), (4, 15)]


def test_il_31_in_un_mese_corto_diventa_l_ultimo_giorno():
    """Saltarlo farebbe sparire una manutenzione senza dirlo a nessuno;
    spostarla di un giorno si vede, e chi la guarda capisce."""
    date = date_successive(datetime(2026, 1, 31, 9), "mensile", datetime(2026, 4, 30, 9))
    assert [(d.month, d.day) for d in date] == [(2, 28), (3, 31), (4, 30)]


def test_c_e_un_tetto_al_numero_di_occorrenze():
    """Senza, una ripetizione settimanale fino al 2093 riempirebbe il database."""
    date = date_successive(_quando(), "settimanale", _quando() + timedelta(days=365 * 50))
    assert len(date) == MASSIMO


def test_una_fine_prima_dell_inizio_non_genera_niente():
    assert date_successive(_quando(), "settimanale", _quando() - timedelta(days=1)) == []


# ---------- DENTRO L'APP ----------

def test_creare_una_ripetizione_crea_impegni_veri(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = _crea(client, a, ripeti="settimanale",
              ripeti_fino=(_quando() + timedelta(days=21)).isoformat())
    assert r.status_code == 201
    primo = r.json()
    # Il primo della serie porta il proprio numero: e' lui a fondarla.
    assert primo["serie_id"] == primo["id"]

    agenda = _agenda(client, a, "2026-03-01", "2026-03-31")
    assert len(agenda["impegni"]) == 4
    assert [i["serie_id"] for i in agenda["impegni"]] == [primo["id"]] * 4


def test_la_durata_si_sposta_insieme(client):
    """Un impegno di due ore resta di due ore anche fra sei settimane."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea(client, a, fine=_quando(ora=11).isoformat(), ripeti="settimanale",
          ripeti_fino=(_quando() + timedelta(days=7)).isoformat())

    agenda = _agenda(client, a, "2026-03-01", "2026-03-31")
    for i in agenda["impegni"]:
        inizio = datetime.fromisoformat(i["inizio"])
        fine = datetime.fromisoformat(i["fine"])
        assert (fine - inizio) == timedelta(hours=2)


def test_ogni_occorrenza_si_sposta_da_sola(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea(client, a, ripeti="settimanale",
          ripeti_fino=(_quando() + timedelta(days=14)).isoformat())
    agenda = _agenda(client, a, "2026-03-01", "2026-03-31")
    seconda = agenda["impegni"][1]

    client.patch(f"/agenda/{seconda['id']}",
                 json={"inizio": "2026-03-18T09:00:00"}, headers=a)

    dopo = _agenda(client, a, "2026-03-01", "2026-03-31")
    giorni = sorted(datetime.fromisoformat(i["inizio"]).day for i in dopo["impegni"])
    # Solo quella si e' mossa: le altre due sono dove erano.
    assert giorni == [10, 18, 24]


def test_si_cancella_una_sola_occorrenza(client):
    """E' il valore predefinito: annullare per sbaglio sei mesi di
    manutenzioni volendo spostare quella di giovedi' non si rimedia."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea(client, a, ripeti="settimanale",
          ripeti_fino=(_quando() + timedelta(days=14)).isoformat())
    agenda = _agenda(client, a, "2026-03-01", "2026-03-31")

    client.delete(f"/agenda/{agenda['impegni'][1]['id']}", headers=a)
    assert len(_agenda(client, a, "2026-03-01", "2026-03-31")["impegni"]) == 2


def test_si_cancella_tutta_la_serie_se_lo_si_chiede(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea(client, a, ripeti="settimanale",
          ripeti_fino=(_quando() + timedelta(days=14)).isoformat())
    agenda = _agenda(client, a, "2026-03-01", "2026-03-31")

    r = client.delete(f"/agenda/{agenda['impegni'][1]['id']}?tutta_la_serie=true", headers=a)
    assert r.status_code == 204
    assert _agenda(client, a, "2026-03-01", "2026-03-31")["impegni"] == []


def test_cancellare_la_serie_non_tocca_gli_impegni_singoli(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/agenda", json={"titolo": "Da solo",
                                 "inizio": _quando(giorno=12).isoformat()}, headers=a)
    _crea(client, a, ripeti="settimanale",
          ripeti_fino=(_quando() + timedelta(days=14)).isoformat())
    agenda = _agenda(client, a, "2026-03-01", "2026-03-31")
    della_serie = [i for i in agenda["impegni"] if i["serie_id"]][0]

    client.delete(f"/agenda/{della_serie['id']}?tutta_la_serie=true", headers=a)
    rimasti = _agenda(client, a, "2026-03-01", "2026-03-31")["impegni"]
    assert [i["titolo"] for i in rimasti] == ["Da solo"]


def test_ripetere_senza_dire_fino_a_quando_viene_rifiutato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = _crea(client, a, ripeti="settimanale")
    assert r.status_code == 422


def test_una_ripetizione_inventata_viene_rifiutata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = _crea(client, a, ripeti="ogni_luna_piena",
              ripeti_fino=(_quando() + timedelta(days=30)).isoformat())
    assert r.status_code == 422


def test_un_solo_avviso_per_tutta_la_serie(client):
    """Una campanella per ognuna delle cinquanta occorrenze sarebbe solo un
    modo per far spegnere gli avvisi a tutti."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/utenti", json={"nome": "Gino", "email": "gino@a.it",
                                     "password": "password1", "ruolo": "operatore"},
                    headers=a)
    id_gino = r.json()["id"]
    tok = client.post("/auth/login", json={"email": "gino@a.it",
                                           "password": "password1"}).json()["access_token"]
    gino = {"Authorization": f"Bearer {tok}"}

    _crea(client, a, partecipanti_ids=[id_gino], ripeti="settimanale",
          ripeti_fino=(_quando() + timedelta(days=28)).isoformat())

    avvisi = client.get("/notifiche", headers=gino).json()["notifiche"]
    assert len([n for n in avvisi if n["tipo"] == "impegno"]) == 1


def test_un_estraneo_non_cancella_la_serie_di_un_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea(client, a, ripeti="settimanale",
          ripeti_fino=(_quando() + timedelta(days=14)).isoformat())
    agenda = _agenda(client, a, "2026-03-01", "2026-03-31")

    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    r = client.delete(f"/agenda/{agenda['impegni'][0]['id']}?tutta_la_serie=true",
                      headers=altra)
    assert r.status_code == 404
    assert len(_agenda(client, a, "2026-03-01", "2026-03-31")["impegni"]) == 3
