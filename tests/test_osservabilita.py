"""
Avvisi sugli errori e log.

Il punto piu' importante: senza chiave configurata NON deve partire niente
verso l'esterno, e quando parte non deve portarsi dietro il token di accesso.
Un registro degli errori che si porta via le credenziali e' peggio del
problema che risolve.
"""
import logging

from app.config import settings
from app import osservabilita
from tests.conftest import registra


def test_senza_chiave_sentry_resta_spento():
    """In locale e nei test non si spedisce niente a nessuno."""
    prima = settings.sentry_dsn
    settings.sentry_dsn = ""
    try:
        assert osservabilita.prepara_sentry() is False
    finally:
        settings.sentry_dsn = prima


def test_il_token_di_accesso_non_finisce_negli_avvisi():
    """Nelle intestazioni c'e' il token, che equivale a una password."""
    evento = {
        "request": {
            "headers": {
                "Authorization": "Bearer un-token-vero-e-segreto",
                "Cookie": "sessione=abc",
                "X-Chiave-Promemoria": "la-chiave-dei-promemoria",
                "User-Agent": "Mozilla/5.0",
            },
            "data": {"password": "quella-vera"},
        }
    }
    ripulito = osservabilita._togli_dati_sensibili(evento, None)
    intestazioni = ripulito["request"]["headers"]

    assert intestazioni["Authorization"] == "[rimosso]"
    assert intestazioni["Cookie"] == "[rimosso]"
    assert intestazioni["X-Chiave-Promemoria"] == "[rimosso]"
    # quello che non e' segreto resta, altrimenti l'avviso non serve a capire
    assert intestazioni["User-Agent"] == "Mozilla/5.0"
    # e il corpo della richiesta non parte proprio
    assert "data" not in ripulito["request"]


def test_la_ripulitura_regge_anche_su_avvisi_strani():
    """Sentry non garantisce la forma dell'evento: non deve esplodere."""
    for evento in ({}, {"request": {}}, {"request": {"headers": "non-un-dizionario"}}):
        assert osservabilita._togli_dati_sensibili(evento, None) is not None


class _Ascoltatore(logging.Handler):
    """Raccoglie le righe scritte dal registro, per poterle controllare.

    Uso questo invece di caplog: caplog si aggancia al registro radice e
    dipende da come sono impostati i livelli altrove, e qui il middleware
    scrive da dentro la catena delle richieste. Un ascoltatore attaccato
    direttamente al registro che ci interessa e' piu' prevedibile."""

    def __init__(self):
        super().__init__()
        self.righe = []

    def emit(self, record):
        self.righe.append(record.getMessage())


def _in_ascolto():
    """Attacca l'ascoltatore al registro delle richieste e lo restituisce."""
    import contextlib

    @contextlib.contextmanager
    def gestore():
        ascoltatore = _Ascoltatore()
        registro = logging.getLogger("coordsync")
        livello = registro.level
        registro.addHandler(ascoltatore)
        registro.setLevel(logging.DEBUG)
        try:
            yield ascoltatore
        finally:
            registro.removeHandler(ascoltatore)
            registro.setLevel(livello)

    return gestore()


def test_le_richieste_riuscite_non_sporcano_i_log(client):
    """Un log che scorre sempre non lo legge nessuno (e lo spazio e' poco)."""
    with _in_ascolto() as ascoltatore:
        assert client.get("/health").status_code == 200

    richieste = [r for r in ascoltatore.righe if "/health" in r]
    assert richieste == [], richieste


def test_gli_errori_finiscono_nei_log(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")

    with _in_ascolto() as ascoltatore:
        # una macchina che non esiste: 404
        assert client.get("/macchine/999999", headers=a).status_code == 404

    righe = [r for r in ascoltatore.righe if "/macchine/999999" in r]
    assert righe, ascoltatore.righe
    assert "404" in righe[0]


def test_anche_chi_non_ha_il_permesso_finisce_nei_log(client):
    """Senza token e' 403: va registrato, perche' un 403 improvviso e
    ripetuto e' il sintomo di qualcosa che non va."""
    with _in_ascolto() as ascoltatore:
        assert client.get("/progetti").status_code == 403

    assert any("/progetti" in r and "403" in r for r in ascoltatore.righe), ascoltatore.righe


def test_health_risponde(client):
    """L'endpoint che dice se l'app e' viva: banale ma e' quello che guarda
    chi controlla il servizio da fuori."""
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"stato": "ok"}
