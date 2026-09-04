"""Modello Progetto: il contenitore dei lavori (cliente / commessa)."""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Progetto(Base):
    __tablename__ = "progetti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descrizione = Column(String, nullable=True)
    # Link a un documento/foglio esterno (Excel, Google Sheets...) collegato al progetto.
    link_documento = Column(String, nullable=True)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Ogni progetto appartiene a un'organizzazione (il "tenant").
    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id"), nullable=False)
    organizzazione = relationship("Organizzazione", back_populates="progetti")

    # Reparto di appartenenza. NULL = progetto "generale", visibile a tutta
    # l'azienda: e' anche lo stato in cui restano i progetti gia' esistenti.
    # index=True: ogni elenco progetti filtra per reparto (l'indice esiste gia'
    # dalla migrazione dei reparti; qui il modello lo dichiara, cosi' Alembic
    # non lo vede come "di troppo" e non prova a eliminarlo).
    reparto_id = Column(Integer, ForeignKey("reparti.id", ondelete="SET NULL"),
                        nullable=True, index=True)
    reparto = relationship("Reparto", back_populates="progetti")

    # Collegamento FACOLTATIVO a una macchina: serve a chi vuole ritrovare nella
    # scheda dell'impianto anche le commesse che l'hanno toccato. Nessun obbligo:
    # i due mondi restano indipendenti.
    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="SET NULL"),
                         nullable=True, index=True)

    # Un progetto ha molti lavori. 'cascade' = se cancelli il progetto,
    # spariscono anche i suoi lavori (niente lavori "orfani").
    lavori = relationship("Lavoro", back_populates="progetto", cascade="all, delete-orphan")
    allegati = relationship("Allegato", back_populates="progetto", cascade="all, delete-orphan")
