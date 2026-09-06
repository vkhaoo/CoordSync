"""
Test della paginazione sugli elenchi che crescono senza limite: i lavori di un
progetto e lo storico di una macchina.

Il rischio non e' tanto sbagliare a contare, e' che una pagina si porti dietro
piu' di quello che dovrebbe: il taglio si applica DOPO i filtri e DOPO la
visibilita', mai prima. Se si applicasse prima, chiedere la seconda pagina
mostrerebbe roba di altri reparti.
"""
from tests.conftest import registra
from app.pagine import PAGINA, MASSIMO_PAGINA


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _utente(client, admin, nome, email, ruolo="caposquadra"):
    r = client.post("/utenti", json={"nome": nome, "email": email,
                                     "password": "password1", "ruolo": ruolo}, headers=admin)
    return r.json()["id"], _login(client, email)


def _tanti_lavori(client, headers, quanti):
    p = client.post("/progetti", json={"nome": "P"}, headers=headers).json()
    for n in range(quanti):
        client.post("/lavori", json={"titolo": f"Lavoro {n:03d}",
                                     "progetto_id": p["id"]}, headers=headers)
    return p


# ---------- LAVORI ----------

def test_arrivano_a_pagine_e_il_totale_e_nell_intestazione(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _tanti_lavori(client, a, 7)

    r = client.get(f"/lavori?progetto_id={p['id']}&limite=3", headers=a)
    assert r.status_code == 200
    assert len(r.json()) == 3
    # Il totale e' quello VERO, non quello della pagina: serve a sapere se ha
    # senso chiedere il resto.
    assert r.headers["X-Totale"] == "7"


def test_la_seconda_pagina_prosegue_senza_ripetere_ne_saltare(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _tanti_lavori(client, a, 5)

    prima = client.get(f"/lavori?progetto_id={p['id']}&limite=2&salta=0", headers=a).json()
    seconda = client.get(f"/lavori?progetto_id={p['id']}&limite=2&salta=2", headers=a).json()
    terza = client.get(f"/lavori?progetto_id={p['id']}&limite=2&salta=4", headers=a).json()

    ids = [l["id"] for l in prima + seconda + terza]
    assert len(ids) == 5
    assert len(set(ids)) == 5      # nessun doppione
    tutti = {l["id"] for l in client.get(f"/lavori?progetto_id={p['id']}&limite=200",
                                         headers=a).json()}
    assert set(ids) == tutti       # e nessuno perso per strada


def test_oltre_la_fine_si_ottiene_una_pagina_vuota(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _tanti_lavori(client, a, 3)
    r = client.get(f"/lavori?progetto_id={p['id']}&limite=10&salta=50", headers=a)
    assert r.json() == [] and r.headers["X-Totale"] == "3"


def test_il_taglio_viene_dopo_i_filtri(client):
    """Se si tagliasse prima, la prima pagina filtrata potrebbe uscire vuota
    pur essendoci risultati piu' in fondo."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _tanti_lavori(client, a, 6)
    tutti = client.get(f"/lavori?progetto_id={p['id']}&limite=200", headers=a).json()
    ultimo = tutti[-1]
    client.patch(f"/lavori/{ultimo['id']}/stato", json={"stato": "in_corso"}, headers=a)

    r = client.get(f"/lavori?progetto_id={p['id']}&stato=in_corso&limite=2", headers=a)
    assert [l["id"] for l in r.json()] == [ultimo["id"]]
    assert r.headers["X-Totale"] == "1"


def test_il_taglio_viene_dopo_la_visibilita(client):
    """Il totale che si legge e' il totale di quello che POSSO vedere, non di
    quello che esiste: se no direbbe a un estraneo quanti lavori ci sono."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, dino = _utente(client, a, "Dino", "dino@a.it")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    p = client.post("/progetti", json={"nome": "Riservato",
                                       "reparti_ids": [reparto["id"]]}, headers=a).json()
    for n in range(4):
        client.post("/lavori", json={"titolo": f"L{n}", "progetto_id": p["id"]}, headers=a)

    r = client.get("/lavori?limite=10", headers=dino)
    assert r.json() == [] and r.headers["X-Totale"] == "0"


def test_non_si_puo_chiedere_una_pagina_enorme(client):
    """Senza un massimo basterebbe limite=100000 per riportare il problema
    esattamente dov'era."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.get(f"/lavori?limite={MASSIMO_PAGINA + 1}", headers=a).status_code == 422
    assert client.get("/lavori?limite=0", headers=a).status_code == 422
    assert client.get("/lavori?salta=-1", headers=a).status_code == 422


def test_senza_chiedere_niente_arriva_la_pagina_predefinita(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _tanti_lavori(client, a, 3)
    r = client.get(f"/lavori?progetto_id={p['id']}", headers=a)
    assert len(r.json()) == 3          # ce ne sono meno di una pagina
    assert PAGINA >= 3


# ---------- STORICO MACCHINA ----------

def test_anche_lo_storico_arriva_a_pagine(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = client.post("/macchine", json={"nome": "Pressa 1"}, headers=a).json()
    for n in range(6):
        client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": f"Voce {n}"}, headers=a)

    r = client.get(f"/macchine/{m['id']}/voci?limite=4", headers=a)
    assert len(r.json()) == 4
    assert r.headers["X-Totale"] == "6"

    resto = client.get(f"/macchine/{m['id']}/voci?limite=4&salta=4", headers=a).json()
    assert len(resto) == 2


def test_lo_storico_resta_in_ordine_di_tempo_fra_le_pagine(client):
    """Dalla piu' recente: se l'ordine cambiasse fra una pagina e l'altra si
    vedrebbero doppioni e buchi."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = client.post("/macchine", json={"nome": "Pressa 1"}, headers=a).json()
    for n in range(5):
        client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": f"Voce {n}"}, headers=a)

    a_pezzi = []
    for salta in (0, 2, 4):
        a_pezzi += [v["id"] for v in client.get(
            f"/macchine/{m['id']}/voci?limite=2&salta={salta}", headers=a).json()]
    intero = [v["id"] for v in client.get(
        f"/macchine/{m['id']}/voci?limite=200", headers=a).json()]
    assert a_pezzi == intero


def test_la_ricerca_nello_storico_conta_solo_quello_che_trova(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = client.post("/macchine", json={"nome": "Pressa 1"}, headers=a).json()
    for n in range(5):
        client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": f"Voce {n}"}, headers=a)
    client.post(f"/macchine/{m['id']}/voci",
                json={"tipo": "analisi", "titolo": "Valvola bloccata"}, headers=a)

    r = client.get(f"/macchine/{m['id']}/voci?q=valvola&limite=10", headers=a)
    assert len(r.json()) == 1 and r.headers["X-Totale"] == "1"


def test_il_totale_e_leggibile_anche_da_un_altro_host(client):
    """Un'intestazione personalizzata il browser NON la fa leggere al codice
    della pagina se il server non lo dichiara. Senza, X-Totale arriverebbe e
    resterebbe invisibile solo in produzione — dove le pagine e il backend
    stanno su due host diversi — mentre in locale funzionerebbe benissimo.
    E' la stessa forma del guaio del cookie anti-CSRF, ed e' il motivo per cui
    questo test esiste."""
    from app.config import settings
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    origine = settings.lista_cors[0]

    r = client.get("/lavori", headers={**a, "Origin": origine})
    esposte = r.headers.get("access-control-expose-headers", "")
    assert "X-Totale" in esposte
