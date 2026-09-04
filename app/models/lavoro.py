"""Modello Lavoro: il cuore dell'app."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.database import Base


class StatoLavoro(str, enum.Enum):
    """Gli stati possibili di un lavoro. Usare un enum evita errori di battitura
    (nessuno puo' scrivere 'fattoo' o 'in corsoo': i valori sono fissi)."""
    da_fare = "da_fare"
    in_corso = "in_corso"
    in_attesa = "in_attesa"
    fatto = "fatto"


class PrioritaLavoro(str, enum.Enum):
    bassa = "bassa"
    normale = "normale"
    alta = "alta"
    urgente = "urgente"


class Lavoro(Base):
    __tablename__ = "lavori"

    id = Column(Integer, primary_key=True, index=True)
    titolo = Column(String, nullable=False)
    descrizione = Column(String, nullable=True)
    stato = Column(SAEnum(StatoLavoro), default=StatoLavoro.da_fare, nullable=False)
    priorita = Column(SAEnum(PrioritaLavoro), default=PrioritaLavoro.normale, nullable=False)

    # Foreign key: il "puntatore" al progetto di appartenenza.
    progetto_id = Column(Integer, ForeignKey("progetti.id", ondelete="CASCADE"), nullable=False)

    # Scadenza (solo data, niente ora: sul campo si ragiona a giorni). Facoltativa.
    data_scadenza = Column(Date, nullable=True)

    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    aggiornato_il = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Completamento: quando il lavoro e' passato a "fatto", e da chi.
    # Restano vuoti finche' non e' completato (e si svuotano se torna indietro).
    completato_il = Column(DateTime, nullable=True)
    completato_da_id = Column(Integer, ForeignKey("utenti.id"), nullable=True)

    # Collegamento FACOLTATIVO alla macchina su cui si interviene: cosi' la
    # scheda dell'impianto mostra anche i lavori coordinati che l'hanno toccato.
    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="SET NULL"),
                         nullable=True, index=True)

    # Le due "scorciatoie" di navigazione:
    progetto = relationship("Progetto", back_populates="lavori")
    allegati = relationship("Allegato", back_populates="lavoro", cascade="all, delete-orphan")
    assegnatari = relationship("Utente", secondary="assegnazioni", back_populates="lavori")
    completato_da = relationship("Utente", foreign_keys=[completato_da_id])
    sotto_attivita = relationship("SottoAttivita", back_populates="lavoro",
                                  cascade="all, delete-orphan")
