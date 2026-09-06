"""Modello Lavoro: il cuore dell'app."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.database import Base


class StatoLavoro(str, enum.Enum):
    """Gli stati possibili di un lavoro. Usare un enum evita errori di battitura
    (nessuno puo' scrivere 'fattoo' o 'in corsoo': i valori sono fissi).

    'annullato' non e' un doppione di 'fatto' ne' di 'in_attesa': e' un lavoro
    che non si fara' PIU'. In attesa vuol dire fermo ma vivo (mancano i pezzi);
    annullato vuol dire deciso di no. Tenerli distinti serve a due cose: la
    barra di avanzamento non deve piu' contarlo — un lavoro annullato non e'
    lavoro rimasto da fare — e la sua scadenza non deve piu' suonare.

    Perche' un quinto stato invece di cancellare il lavoro: se lo si cancella
    sparisce anche il perche', e "questo l'avevamo deciso e poi tolto" e'
    un'informazione che serve sei mesi dopo.
    """
    da_fare = "da_fare"
    in_corso = "in_corso"
    in_attesa = "in_attesa"
    fatto = "fatto"
    annullato = "annullato"

    @classmethod
    def conclusi(cls) -> tuple["StatoLavoro", ...]:
        """Gli stati in cui un lavoro non chiede piu' niente a nessuno."""
        return (cls.fatto, cls.annullato)


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
