"""
Punto d'ingresso dell'applicazione FastAPI.

Per ora fa due cose:
1. Crea le tabelle nel database all'avvio (dai modelli che abbiamo definito).
2. Espone un endpoint /health per verificare che tutto giri.

Gli endpoint veri (progetti, lavori, utenti) li agganciamo al prossimo passo.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401  (importa i modelli cosi' vengono registrati)
from app.routers import auth
from app.routers import progetti
from app.routers import lavori
from app.routers import utenti
from app.routers import commenti
from app.routers import assegnazioni
from app.routers import sotto_attivita
from app.routers import reparti

# Lo schema del database e' gestito dalle MIGRAZIONI Alembic
# (comando: alembic upgrade head), non piu' creato "al volo" qui.
# Questo tiene locale e produzione allineati e permette di evolvere le tabelle
# senza perdere i dati.

app = FastAPI(title="CoordSync", version="0.1.0")

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


@app.get("/health")
def health():
    """Endpoint di salute: se risponde, l'app e' viva."""
    return {"stato": "ok"}
