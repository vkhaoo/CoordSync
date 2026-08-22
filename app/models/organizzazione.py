"""
Modello Organizzazione: l'azienda (il "tenant", l'inquilino).

Ogni utente e ogni progetto appartengono a un'organizzazione. E' il confine
che separa i dati di un'azienda da quelli di un'altra nella stessa app.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Organizzazione(Base):
    __tablename__ = "organizzazioni"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    utenti = relationship("Utente", back_populates="organizzazione")
    progetti = relationship("Progetto", back_populates="organizzazione")
