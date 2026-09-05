"""
Sapere quando l'app si rompe, invece di scoprirlo perche' te lo dice un collega.

Due pezzi, indipendenti l'uno dall'altro:

1. **Sentry** — quando qualcosa esplode in produzione arriva un'email con la
   riga di codice esatta e il contesto. Serve una chiave (SENTRY_DSN); senza,
   questo file non fa niente e non si lamenta, cosi' in locale e nei test non
   si spedisce nulla a nessuno.

2. **Log leggibili** — una riga per richiesta con metodo, percorso, esito e
   quanto ci ha messo. Serve a capire cosa succedeva intorno a un errore, e a
   trovare le lentezze prima che diventino un problema.

Nota sulla riservatezza: negli avvisi non finiscono mai il corpo delle
richieste ne' le intestazioni di autenticazione. Un registro degli errori che
si porta dietro le password e' peggio del problema che risolve.
"""
import logging
import time

from fastapi import Request

from app.config import settings

log = logging.getLogger("coordsync")


def _togli_dati_sensibili(evento, _indizio):
    """Ripulisce l'avviso prima che parta verso Sentry.

    Sentry di suo non manda il corpo delle richieste, ma le intestazioni si':
    dentro c'e' il token di accesso, che equivale a una password. Qui viene
    tolto, insieme ai cookie.
    """
    richiesta = evento.get("request") or {}
    intestazioni = richiesta.get("headers")
    if isinstance(intestazioni, dict):
        for nome in list(intestazioni):
            if nome.lower() in ("authorization", "cookie", "x-chiave-promemoria"):
                intestazioni[nome] = "[rimosso]"
    richiesta.pop("data", None)      # il corpo non serve a capire un errore
    return evento


def prepara_sentry() -> bool:
    """Accende Sentry se c'e' la chiave. Restituisce True se e' attivo."""
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        # La libreria non c'e': meglio partire senza avvisi che non partire.
        log.warning("SENTRY_DSN impostato ma sentry-sdk non e' installato.")
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.ambiente,
        # Quota gratuita: prendo un decimo delle richieste per le prestazioni,
        # ma TUTTI gli errori. Gli errori sono quello che conta.
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=_togli_dati_sensibili,
    )
    log.info("Sentry attivo (ambiente: %s)", settings.ambiente)
    return True


def prepara_log() -> None:
    """Log a una riga, con l'ora davanti. Leggibili nel pannello di Render."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


async def traccia_richieste(richiesta: Request, prosegui):
    """Una riga per richiesta: metodo, percorso, esito, durata.

    Le richieste andate bene si registrano solo se sono LENTE: un log che
    scorre sempre non lo legge nessuno, e sul piano gratuito lo spazio dei log
    e' limitato. Gli errori invece si registrano sempre.
    """
    inizio = time.perf_counter()
    try:
        risposta = await prosegui(richiesta)
    except Exception:
        durata = (time.perf_counter() - inizio) * 1000
        log.exception("%s %s -> ESPLOSO in %.0f ms",
                      richiesta.method, richiesta.url.path, durata)
        raise

    durata = (time.perf_counter() - inizio) * 1000
    if risposta.status_code >= 500:
        log.error("%s %s -> %s in %.0f ms",
                  richiesta.method, richiesta.url.path, risposta.status_code, durata)
    elif risposta.status_code >= 400:
        log.warning("%s %s -> %s in %.0f ms",
                    richiesta.method, richiesta.url.path, risposta.status_code, durata)
    elif durata > 1000:
        log.warning("LENTA: %s %s -> %s in %.0f ms",
                    richiesta.method, richiesta.url.path, risposta.status_code, durata)

    return risposta
