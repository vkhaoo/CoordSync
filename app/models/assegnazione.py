"""
Tabella-ponte per il molti-a-molti Lavoro <-> Utente.

E' il tuo "array di slot": ogni riga e' un collegamento
"questo utente sta su questo lavoro". Non e' una classe piena come gli altri
modelli, ma una semplice Table, perche' contiene solo i due riferimenti.
"""
from sqlalchemy import Table, Column, Integer, ForeignKey

from app.database import Base

assegnazione = Table(
    "assegnazioni",
    Base.metadata,
    Column("lavoro_id", Integer, ForeignKey("lavori.id", ondelete="CASCADE"), primary_key=True),
    Column("utente_id", Integer, ForeignKey("utenti.id", ondelete="CASCADE"), primary_key=True),
)
