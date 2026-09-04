"""
Modello Reparto: un sotto-gruppo dentro l'azienda (es. Digitale, Automazione).

E' il SECONDO livello di isolamento, sotto quello dell'organizzazione: serve a
non far vedere a un reparto i progetti di un altro. Un utente puo' appartenere
a piu' reparti (un capo puo' seguirne due), quindi il legame e' molti-a-molti.
"""
from datetime import datetime, timezone

from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

# Tabella-ponte utente <-> reparto: ogni riga dice "questo utente sta in questo reparto".
membro_reparto = Table(
    "membri_reparto",
    Base.metadata,
    Column("reparto_id", Integer, ForeignKey("reparti.id", ondelete="CASCADE"), primary_key=True),
    Column("utente_id", Integer, ForeignKey("utenti.id", ondelete="CASCADE"), primary_key=True),
)


class Reparto(Base):
    __tablename__ = "reparti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Il reparto vive dentro un'azienda: due aziende possono avere reparti omonimi.
    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id"), nullable=False)

    membri = relationship("Utente", secondary=membro_reparto, back_populates="reparti")
    # Se elimino il reparto i progetti NON spariscono: tornano "generali"
    # (reparto_id a NULL). Cancellare un reparto non deve distruggere lavoro vero.
    progetti = relationship("Progetto", back_populates="reparto")
