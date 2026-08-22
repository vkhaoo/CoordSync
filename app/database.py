"""
Connessione al database e gestione delle sessioni.

- 'engine' e' la connessione vera e propria al database.
- 'SessionLocal' e' una "fabbrica" di sessioni: ogni richiesta HTTP ne apre
  una, la usa per leggere/scrivere, e la chiude. Come aprire e chiudere un file.
- 'Base' e' la classe da cui erediteranno tutti i nostri modelli (le tabelle).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# connect_args serve solo a SQLite; con PostgreSQL non serve, lo togli.
connect_args = {"check_same_thread": False} if settings.db_url_normalizzato.startswith("sqlite") else {}

engine = create_engine(settings.db_url_normalizzato, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Dipendenza FastAPI: fornisce una sessione DB a un endpoint e la chiude
    automaticamente alla fine, anche se qualcosa va storto. (Il 'yield' + finally
    garantisce la chiusura pulita.)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
