"""
Punto d'ingresso dell'applicazione FastAPI: mette insieme i pezzi.

Qui si accendono anche i log e gli avvisi sugli errori (vedi osservabilita.py),
prima di tutto il resto: se qualcosa esplode durante l'avvio, si vuole saperlo.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.osservabilita import prepara_log, prepara_sentry, traccia_richieste
from app.config import controlla_configurazione, settings as _settings

from app import models  # noqa: F401  (importa i modelli cosi' vengono registrati)
from app.routers import auth
from app.routers import progetti
from app.routers import lavori
from app.routers import utenti
from app.routers import commenti
from app.routers import assegnazioni
from app.routers import sotto_attivita
from app.routers import reparti
from app.routers import macchine
from app.routers import agenda
from app.routers import notifiche_app
from app.routers import ricerca_globale

# Lo schema del database e' gestito dalle MIGRAZIONI Alembic
# (comando: alembic upgrade head), non piu' creato "al volo" qui.
# Questo tiene locale e produzione allineati e permette di evolvere le tabelle
# senza perdere i dati.

# Prima di costruire l'app: log leggibili e avvisi sugli errori.
prepara_log()
prepara_sentry()   # senza SENTRY_DSN non fa niente e non si lamenta

# Poi il controllo di sicurezza: se la produzione gira con la chiave di
# esempio, qui l'avvio si ferma. Meglio un deploy fallito e visibile che
# un'app in piedi con i token falsificabili.
controlla_configurazione()

# La documentazione interattiva (/docs, /openapi.json) e' comodissima mentre si
# sviluppa, ma in produzione e' la mappa completa dell'API servita a chiunque:
# la si spegne quando l'ambiente e' "produzione".
_in_produzione = _settings.ambiente.lower().startswith("produzione")
app = FastAPI(
    title="CoordSync",
    version="0.1.0",
    docs_url=None if _in_produzione else "/docs",
    redoc_url=None if _in_produzione else "/redoc",
    openapi_url=None if _in_produzione else "/openapi.json",
)

# Tetto alla dimensione delle richieste. Il database gratuito ha poco spazio e
# viene cancellato a 90 giorni: riempirlo e' un modo concreto di far danno.
# 1 MB e' enorme per del testo (gli allegati sono solo link), e taglia sul
# nascere sia i corpi assurdi sia certi tentativi di esaurire la memoria.
MAX_CORPO = 1_000_000


@app.middleware("http")
async def limita_dimensione(richiesta: Request, prosegui):
    lunghezza = richiesta.headers.get("content-length")
    if lunghezza is not None and lunghezza.isdigit() and int(lunghezza) > MAX_CORPO:
        return JSONResponse(status_code=413,
                            content={"detail": "Richiesta troppo grande."})
    return await prosegui(richiesta)


@app.middleware("http")
async def intestazioni_sicurezza(richiesta: Request, prosegui):
    """Le intestazioni che dicono al browser di stare all'erta.

    - nosniff: non indovinare il tipo di un contenuto, fidati di quello che dico
      (evita che un file venga eseguito come script);
    - DENY / frame-ancestors none: la pagina non si puo' incorniciare in un
      iframe, cosi' nessuno la nasconde sotto una trappola (clickjacking);
    - HSTS: da adesso parla con me solo via HTTPS, per due anni;
    - Referrer-Policy: non spifferare a siti terzi l'indirizzo completo da cui
      si arriva.
    """
    risposta = await prosegui(richiesta)
    risposta.headers["X-Content-Type-Options"] = "nosniff"
    risposta.headers["X-Frame-Options"] = "DENY"
    risposta.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    risposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    risposta.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return risposta


# Una riga di log per richiesta: gli errori sempre, quelle riuscite solo se lente.
app.middleware("http")(traccia_richieste)

# CORS: permette al frontend (server di sviluppo) di chiamare questa API.
# In produzione, qui andra' l'indirizzo vero del sito, non localhost.
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.lista_cors,   # da variabile d'ambiente (locale o produzione)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aggancia gli endpoint dei progetti all'app.
app.include_router(auth.router)
app.include_router(progetti.router)
app.include_router(lavori.router)
app.include_router(utenti.router)
app.include_router(commenti.router)
app.include_router(assegnazioni.router)
app.include_router(sotto_attivita.router)
app.include_router(reparti.router)
app.include_router(macchine.router)
app.include_router(agenda.router)
app.include_router(notifiche_app.router)
app.include_router(ricerca_globale.router)


@app.get("/health")
def health():
    """Endpoint di salute: se risponde, l'app e' viva."""
    return {"stato": "ok"}
