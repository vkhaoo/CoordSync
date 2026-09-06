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
