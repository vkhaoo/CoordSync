"""
Modello Commento: un messaggio attaccato a un lavoro, scritto da un utente.

E' il cuore del "coordinamento per lavoro": invece di una chat generica,
la conversazione resta legata al lavoro specifico.
Ha DUE foreign key: punta al lavoro (dove sta) e all'autore (chi l'ha scritto).
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Commento(Base):
    __tablename__ = "commenti"

    id = Column(Integer, primary_key=True, index=True)
    testo = Column(String, nullable=False)

    # Le due "coordinate" del commento:
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="CASCADE"), nullable=False)
    autore_id = Column(Integer, ForeignKey("utenti.id"), nullable=False)

    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Scorciatoie di navigazione: dato un commento, risali all'autore o al lavoro.
    autore = relationship("Utente")
    lavoro = relationship("Lavoro")
