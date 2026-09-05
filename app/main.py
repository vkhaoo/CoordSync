"""
Punto d'ingresso dell'applicazione FastAPI: mette insieme i pezzi.

Qui si accendono anche i log e gli avvisi sugli errori (vedi osservabilita.py),
prima di tutto il resto: se qualcosa esplode durante l'avvio, si vuole saperlo.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.osservabilita import prepara_log, prepara_sentry, traccia_richieste
from app.config import controlla_configurazione

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

app = FastAPI(title="CoordSync", version="0.1.0")

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


@app.get("/health")
def health():
    """Endpoint di salute: se risponde, l'app e' viva."""
    return {"stato": "ok"}
