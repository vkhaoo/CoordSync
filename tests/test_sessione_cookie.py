"""
La sessione in un cookie che JavaScript non puo' leggere.

Prima il token stava in localStorage, dove qualunque codice che gira nella
pagina se lo puo' portare via e riusarlo comodamente altrove. Con HttpOnly il
browser lo tiene per se'.

Il prezzo sono i CSRF: un cookie il browser lo allega DA SOLO, anche a
richieste che partono da un altro sito. Meta' di questo file protegge la
contromisura; l'altra meta' protegge il fatto che chi era gia' collegato non
venga buttato fuori dal cambio.
"""
from app.sessione import HEADER_CSRF, NOME_COOKIE, NOME_COOKIE_CSRF
from tests.conftest import registra


def _accedi(client, email="marco@a.it", password="password1"):
    return client.post("/auth/login", json={"email": email, "password": password})


# ---------- IL COOKIE ARRIVA, ED E' CHIUSO A CHIAVE ----------

def test_entrando_si_riceve_il_cookie_della_sessione(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()

    r = _accedi(client)
    assert r.status_code == 200

    biscotto = r.cookies.get(NOME_COOKIE)
    assert biscotto, "manca il cookie della sessione"
    # l'attributo che conta: JavaScript non deve poterlo leggere
    intestazione = r.headers["set-cookie"]
    assert "httponly" in intestazione.lower()


def test_col_solo_cookie_si_lavora(client):
    """Nessun header Authorization: il browser allega il cookie da solo."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()
    _accedi(client)

    r = client.get("/auth/me")     # niente headers
    assert r.status_code == 200
    assert r.json()["email"] == "marco@a.it"


def test_senza_niente_non_si_entra(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()

    r = client.get("/auth/me")
    assert r.status_code == 401


def test_uscendo_il_cookie_viene_cancellato(client):
    """Il cookie e' HttpOnly: il frontend non puo' cancellarlo da solo, puo'
    solo chiedere al server di farlo."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()
    _accedi(client)
    assert client.get("/auth/me").status_code == 200

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


# ---------- LA PROTEZIONE CSRF ----------

def test_una_scrittura_col_cookie_vuole_la_prova(client):
    """Il cuore della cosa. Un sito estraneo puo' far partire una richiesta
    col nostro cookie attaccato, ma NON puo' leggere il cookie anti-CSRF per
    rimetterlo nell'header: e' questo che lo ferma."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()
    _accedi(client)

    # senza l'header: rifiutata
    r = client.post("/progetti", json={"nome": "Di nascosto"})
    assert r.status_code == 403
    assert "ricarica" in r.json()["detail"].lower()

    # con l'header giusto: passa
    prova = client.cookies.get(NOME_COOKIE_CSRF)
    r = client.post("/progetti", json={"nome": "Alla luce del sole"},
                    headers={HEADER_CSRF: prova})
    assert r.status_code == 201


def test_un_valore_inventato_non_basta(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()
    _accedi(client)

    r = client.post("/progetti", json={"nome": "Tentativo"},
                    headers={HEADER_CSRF: "me-lo-sono-inventato"})
    assert r.status_code == 403


def test_le_letture_non_chiedono_niente(client):
    """Le richieste che non cambiano niente non hanno bisogno della prova: al
    massimo leggono, e la risposta un sito estraneo non la vede comunque."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/progetti", json={"nome": "Linea 3"}, headers=a)
    client.cookies.clear()
    _accedi(client)

    r = client.get("/progetti")    # nessun header CSRF
    assert r.status_code == 200
    assert [p["nome"] for p in r.json()] == ["Linea 3"]


# ---------- CHI ERA GIA' COLLEGATO NON VIENE BUTTATO FUORI ----------

def test_l_header_authorization_funziona_ancora(client):
    """Chi aveva il token in tasca quando e' cambiato il modo deve poter
    continuare a lavorare finche' non scade."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()

    assert client.get("/auth/me", headers=a).status_code == 200
    # e con l'header non serve la prova anti-CSRF: li' il browser non allega
    # niente da solo, quindi il problema non esiste
    assert client.post("/progetti", json={"nome": "Vecchia maniera"},
                       headers=a).status_code == 201


def test_l_header_ha_la_precedenza_sul_cookie(client):
    """Durante il passaggio qualcuno avra' tutti e due: comanda l'header, che
    e' quello che il frontend vecchio sta ancora mandando."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    b = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    client.cookies.clear()
    _accedi(client, "bruno@b.it")          # cookie di Bruno

    r = client.get("/auth/me", headers=a)  # header di Marco
    assert r.json()["email"] == "marco@a.it"


# ---------- IN PRODUZIONE IL COOKIE E' PROTETTO ----------

def test_in_produzione_il_cookie_viaggia_solo_su_https():
    """Nei test si parla in http, quindi il cookie e' impostato non-secure: e'
    l'unico modo perche' il client dei test lo rimandi indietro. Questo test
    guarda la configurazione VERA, quella che vale online, senza passare da
    una richiesta: con secure=True e samesite=none il cookie viaggia solo su
    HTTPS ed e' accettato anche quando frontend e backend stanno su due
    indirizzi diversi, che e' esattamente il caso in produzione."""
    from fastapi import Response

    from app import sessione
    from app.config import Settings

    vere = Settings(cookie_secure=True, cookie_samesite="none")
    originali = sessione.settings
    sessione.settings = vere
    try:
        risposta = Response()
        sessione.imposta(risposta, "un-token-qualunque")
        intestazioni = [v for k, v in risposta.raw_headers]
        testo = b" ".join(intestazioni).decode().lower()
    finally:
        sessione.settings = originali

    assert "httponly" in testo
    assert "secure" in testo
    assert "samesite=none" in testo


# ---------- LA PROVA ANTI-CSRF SI PUO' CHIEDERE AL SERVER ----------

def test_il_valore_anti_csrf_si_chiede_e_coincide_col_cookie(client):
    """Il frontend non puo' leggere quel cookie: le pagine stanno su un host e
    il backend su un altro, e un documento vede solo i cookie del PROPRIO
    host. Quindi il valore si consegna nel corpo di questa risposta."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()
    _accedi(client)

    r = client.get("/auth/csrf")
    assert r.status_code == 200
    assert r.json()["csrf"] == client.cookies.get(NOME_COOKIE_CSRF)


def test_col_valore_chiesto_al_server_la_scrittura_passa(client):
    """Il giro completo come lo fa il frontend in produzione."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()
    _accedi(client)

    prova = client.get("/auth/csrf").json()["csrf"]
    r = client.post("/progetti", json={"nome": "Linea 3"},
                    headers={HEADER_CSRF: prova})
    assert r.status_code == 201


def test_la_prova_si_ottiene_anche_prima_di_entrare(client):
    """Anche l'accesso e' una POST: deve poter portare la sua prova."""
    client.cookies.clear()
    r = client.get("/auth/csrf")
    assert r.status_code == 200
    assert r.json()["csrf"]
