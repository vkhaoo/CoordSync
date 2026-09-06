"""
Le difese trovate facendo l'attaccante sul sito, e i buchi chiusi.

Ogni test qui nasce da un modo concreto di fare danno che ho provato:
- bloccare l'accesso a tutti falsificando l'IP condiviso del proxy;
- bombardare di email un indirizzo qualunque;
- incorniciare la pagina in un iframe;
- riempire il database con richieste enormi;
- indebolire una password lunghissima che bcrypt tronca in silenzio.
"""
from datetime import timedelta

from app import limiti
from app.routers.auth import MAX_EMAIL_PER_IP
from app.rete import ip_reale
from tests.conftest import registra


class _FintaRichiesta:
    """Una richiesta finta con le sole intestazioni che servono a ip_reale."""
    def __init__(self, headers=None, client_host="10.0.0.1"):
        self.headers = headers or {}

        class _C:
            host = client_host
        self.client = _C()


# ---------- L'IP VERO, NON QUELLO DEL PROXY ----------

def test_dietro_cloudflare_conta_l_ip_del_client_non_del_proxy():
    """Il bug grave: con l'IP del proxy tutti finiscono nello stesso contatore,
    e dieci password sbagliate bloccano l'accesso a chiunque."""
    r = _FintaRichiesta(headers={"CF-Connecting-IP": "203.0.113.7",
                                 "X-Forwarded-For": "203.0.113.7, 172.16.0.1"},
                        client_host="172.16.0.1")   # 172.16 = il proxy
    assert ip_reale(r) == "203.0.113.7"


def test_senza_proxy_vale_l_indirizzo_diretto():
    """In locale, senza intestazioni di inoltro, l'indirizzo diretto e' quello
    vero."""
    assert ip_reale(_FintaRichiesta(client_host="127.0.0.1")) == "127.0.0.1"


def test_due_utenti_diversi_non_si_bloccano_a_vicenda(client):
    """La prova che il blocco e' tornato PER UTENTE e non piu' condiviso: uno
    che sbaglia la password all'infinito non deve chiudere fuori l'altro."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    registra(client, "Azienda B", "Bruno", "bruno@b.it")
    limiti.azzera_tutto()

    # Marco (da un IP) sbaglia oltre il limite
    for _ in range(limiti.MAX_TENTATIVI + 1):
        client.post("/auth/login", json={"email": "marco@a.it", "password": "xxx"},
                    headers={"X-Forwarded-For": "1.1.1.1"})
    assert client.post("/auth/login", json={"email": "marco@a.it", "password": "password1"},
                       headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429

    # Bruno, da un altro IP, entra senza problemi
    r = client.post("/auth/login", json={"email": "bruno@b.it", "password": "password1"},
                    headers={"X-Forwarded-For": "2.2.2.2"})
    assert r.status_code == 200


# ---------- NIENTE BOMBARDAMENTO DI EMAIL ----------

def test_non_si_possono_chiedere_mille_reset(client):
    """Il reset e' un endpoint che manda email a un indirizzo qualunque: senza
    freno, e' un modo gratis per intasare la casella di qualcuno."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    limiti.azzera_tutto()

    ip = {"X-Forwarded-For": "9.9.9.9"}
    for _ in range(MAX_EMAIL_PER_IP):
        client.post("/auth/richiedi-reset", json={"email": "vittima@a.it"}, headers=ip)

    r = client.post("/auth/richiedi-reset", json={"email": "vittima@a.it"}, headers=ip)
    assert r.status_code == 429


def test_il_freno_email_e_per_ip(client):
    """Chi ha esaurito il suo giro non blocca gli altri: il freno e' per IP."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    limiti.azzera_tutto()

    for _ in range(MAX_EMAIL_PER_IP + 1):
        client.post("/auth/richiedi-reset", json={"email": "x@a.it"},
                    headers={"X-Forwarded-For": "9.9.9.9"})

    # un altro IP passa ancora
    r = client.post("/auth/richiedi-reset", json={"email": "y@a.it"},
                    headers={"X-Forwarded-For": "8.8.8.8"})
    assert r.status_code == 202


# ---------- LE INTESTAZIONI DI SICUREZZA ----------

def test_ogni_risposta_porta_le_intestazioni_di_sicurezza(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "max-age=" in r.headers["Strict-Transport-Security"]


# ---------- TETTO ALLA DIMENSIONE ----------

def test_una_richiesta_enorme_viene_rifiutata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    enorme = "x" * 2_000_000   # 2 MB, oltre il tetto di 1 MB
    r = client.post("/progetti", json={"nome": enorme}, headers=a)
    assert r.status_code == 413


# ---------- PASSWORD ----------

def test_una_password_lunghissima_viene_rifiutata(client):
    """bcrypt guarda solo i primi 72 byte: oltre, la coda verrebbe ignorata in
    silenzio e la password sembrerebbe piu' forte di quanto e'."""
    r = client.post("/auth/register", json={
        "nome": "Marco", "email": "marco@a.it", "password": "a1" + "z" * 100})
    assert r.status_code == 422


# ---------- XSS MEMORIZZATO NEI LINK ----------

def test_un_link_javascript_non_si_salva(client):
    """Il buco piu' grave del secondo giro. Gli allegati sono link liberi e
    finiscono in un <a href="...">: React NON protegge l'href, quindi un
    "javascript:..." salvato li' e' codice che parte nel browser di chi ci
    clicca — e da li' si agisce al posto suo. Il ruolo piu' basso bastava."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    for veleno in ["javascript:fetch('/utenti')",
                   "JaVaScRiPt:alert(1)",
                   "  javascript:alert(1)",
                   "data:text/html,<script>alert(1)</script>"]:
        r = client.post(f"/progetti/{p['id']}/allegati",
                        json={"url": veleno, "titolo": "Fattura"}, headers=a)
        assert r.status_code == 422, f"accettato: {veleno}"

    # e i link veri continuano a funzionare
    assert client.post(f"/progetti/{p['id']}/allegati",
                       json={"url": "https://drive.example.com/x.pdf"},
                       headers=a).status_code == 201


def test_nemmeno_come_documento_del_progetto(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    r = client.patch(f"/progetti/{p['id']}",
                     json={"link_documento": "javascript:alert(1)"}, headers=a)
    assert r.status_code == 422


# ---------- HTML INIETTATO NELLE EMAIL ----------

def test_il_nome_di_un_progetto_non_inietta_html_nelle_email():
    """Titolo del lavoro e nome del progetto finiscono nell'HTML di un'email
    che arriva a un COLLEGA: senza escape, si infila un link finto nella sua
    posta. Non e' codice che gira, ma e' un ottimo aggancio per una truffa."""
    from app.email_templates import assegnazione_lavoro

    _, _, html = assegnazione_lavoro(
        nome="Luca", chi_assegna="Marco",
        titolo='<a href="http://truffa.example">Clicca per il rimborso</a>',
        progetto="Linea 3", scadenza=None, link="http://app.example")

    assert 'href="http://truffa.example"' not in html
    assert "&lt;a href=" in html


# ---------- REVOCA DELLE SESSIONI ----------

def _con_csrf(client):
    """Gli header che manda il frontend quando la sessione e' nel cookie."""
    from app.sessione import HEADER_CSRF, NOME_COOKIE_CSRF
    return {HEADER_CSRF: client.cookies.get(NOME_COOKIE_CSRF)}

def test_cambiando_password_le_altre_sessioni_cadono(client):
    """Chiunque cambi la password si aspetta che chi era dentro esca. Prima
    non succedeva: un token rubato restava buono fino a 24 ore dopo."""
    ladro = registra(client, "Azienda A", "Marco", "marco@a.it")
    # (stessa sessione, nel ruolo del token rubato)
    assert client.get("/auth/me", headers=ladro).status_code == 200

    # Marco cambia la password da un'altra parte
    client.cookies.clear()
    fresca = client.post("/auth/login",
                         json={"email": "marco@a.it", "password": "password1"})
    assert fresca.status_code == 200
    r = client.post("/auth/cambia-password",
                    json={"vecchia_password": "password1",
                          "nuova_password": "nuovaPassword9"},
                    headers=_con_csrf(client))
    assert r.status_code == 200

    # la sessione vecchia non vale piu'
    dopo = client.get("/auth/me", headers=ladro)
    assert dopo.status_code == 401
    assert "non piu' valida" in dopo.json()["detail"]


def test_chi_cambia_la_password_resta_dentro(client):
    """Non deve buttare fuori anche se stesso: sarebbe scomodo e basta."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    client.cookies.clear()
    client.post("/auth/login", json={"email": "marco@a.it", "password": "password1"})

    client.post("/auth/cambia-password",
                json={"vecchia_password": "password1", "nuova_password": "nuovaPassword9"},
                headers=_con_csrf(client))

    # il cookie e' stato rinnovato con la generazione nuova
    assert client.get("/auth/me").status_code == 200


def test_anche_il_reset_dal_link_butta_fuori_tutti(client):
    """Chi reimposta la password quasi sempre lo fa perche' teme che qualcuno
    sia entrato."""
    from app.routers.auth import SCOPO_RESET
    from app.security import crea_token_scopo

    ladro = registra(client, "Azienda A", "Marco", "marco@a.it")
    io = client.get("/auth/me", headers=ladro).json()

    token = crea_token_scopo(io["id"], SCOPO_RESET, 60)
    assert client.post("/auth/reset-password",
                       json={"token": token,
                             "nuova_password": "nuovaPassword9"}).status_code == 200

    assert client.get("/auth/me", headers=ladro).status_code == 401


# ---------- CONFRONTO DEI SEGRETI A TEMPO COSTANTE ----------

def test_la_chiave_dei_promemoria_si_confronta_a_tempo_costante():
    """Con "!=" il confronto si ferma al primo carattere diverso, e il tempo
    di risposta racconta quanti caratteri iniziali erano giusti: su un
    endpoint senza freno, che si puo' martellare per fare la media, la chiave
    si indovina un pezzo alla volta. Qui si verifica che il codice usi
    compare_digest, che ci mette sempre lo stesso tempo."""
    import inspect

    from app.routers import agenda

    sorgente = inspect.getsource(agenda)
    assert "compare_digest" in sorgente
    assert 'headers.get("X-Chiave-Promemoria") != chiave' not in sorgente


def test_la_chiave_sbagliata_resta_rifiutata(client, monkeypatch):
    """La correzione non deve aver cambiato il comportamento."""
    from app.config import settings

    monkeypatch.setattr(settings, "chiave_promemoria", "la-chiave-giusta")

    assert client.post("/agenda/promemoria/invia",
                       headers={"X-Chiave-Promemoria": "sbagliata"}).status_code == 401
    assert client.post("/agenda/promemoria/invia",
                       headers={"X-Chiave-Promemoria": "la-chiave-giusta"}).status_code == 200
