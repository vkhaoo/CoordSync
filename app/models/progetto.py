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

    # Reparti a cui il progetto appartiene: puo' essere piu' d'uno (una linea
    # condivisa fra due reparti). NESSUN reparto = progetto "generale", visibile
    # a tutta l'azienda, ed e' lo stato in cui restano i progetti esistenti.
    reparti = relationship("Reparto", secondary="progetti_reparto",
                           back_populates="progetti")

    # Collegamento FACOLTATIVO a una macchina: serve a chi vuole ritrovare nella
    # scheda dell'impianto anche le commesse che l'hanno toccato. Nessun obbligo:
    # i due mondi restano indipendenti.
    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="SET NULL"),
                         nullable=True, index=True)

    # Un progetto ha molti lavori. 'cascade' = se cancelli il progetto,
    # spariscono anche i suoi lavori (niente lavori "orfani").
    lavori = relationship("Lavoro", back_populates="progetto", cascade="all, delete-orphan")
    allegati = relationship("Allegato", back_populates="progetto", cascade="all, delete-orphan")
