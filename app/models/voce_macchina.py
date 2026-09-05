"""
VoceMacchina: una riga del taccuino di una macchina.

Un'unica struttura per tutti i tipi di annotazione (lavoro, modifica, analisi,
informazione utile) invece di quattro entita' separate: hanno tutte la stessa
forma — titolo, testo, data, autore, dove sta — e cambiano solo per l'etichetta
e per il fatto che i "lavori" hanno anche uno stato. Cosi' c'e' una schermata
sola per scrivere, e aggiungere un tipo domani e' una riga.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (Table, Column, Integer, String, Text, DateTime,
                        Boolean, ForeignKey, Enum as SAEnum)
from sqlalchemy.orm import relationship

from app.database import Base


class TipoVoce(str, enum.Enum):
    lavoro = "lavoro"              # qualcosa da fare / in corso / fatto
    modifica = "modifica"          # una modifica applicata all'impianto
    analisi = "analisi"            # un'analisi o una diagnosi
    informazione = "informazione"  # sapere di riferimento (modello PLC, tarature...)


class StatoVoce(str, enum.Enum):
    """Solo per le voci di tipo 'lavoro'. Sulle altre resta vuoto."""
    da_fare = "da_fare"
    in_corso = "in_corso"
    fatto = "fatto"


# Una voce puo' stare in piu' sezioni della stessa macchina.
voce_sezione = Table(
    "voci_sezione",
    Base.metadata,
    Column("voce_id", Integer, ForeignKey("voci_macchina.id", ondelete="CASCADE"), primary_key=True),
    Column("sezione_id", Integer, ForeignKey("sezioni_macchina.id", ondelete="CASCADE"), primary_key=True),
)


class VoceMacchina(Base):
    __tablename__ = "voci_macchina"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(SAEnum(TipoVoce), nullable=False)
    # Valorizzato solo sui 'lavoro'; sugli altri tipi resta NULL.
    stato = Column(SAEnum(StatoVoce), nullable=True)

    titolo = Column(String, nullable=False)
    testo = Column(Text, nullable=True)

    # Dove si vede la voce: nella parte generale della macchina, in una o piu'
    # sezioni, o in entrambe. Le due cose non si escludono.
    in_generale = Column(Boolean, nullable=False, default=True)

    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    autore_id = Column(Integer, ForeignKey("utenti.id", ondelete="SET NULL"), nullable=True)

    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="CASCADE"),
                         nullable=False, index=True)

    # Raggruppamento per argomento: una voce puo' stare SOTTO un'altra, come i
    # lavori stanno sotto un progetto. "Perdita d'aria sulla FAZ" diventa
    # l'argomento, e sotto ci finiscono l'analisi, la modifica e il lavoro che
    # l'hanno risolta, invece di tre righe sciolte che non si sanno collegate.
    #
    # UN SOLO LIVELLO: chi ha un genitore non puo' farne da genitore a sua
    # volta. Lo impone il router, non il database. E' la stessa forma di
    # progetto/lavoro, che Nik gia' conosce, e evita alberi profondi in cui
    # non si ritrova piu' niente.
    #
    # SET NULL e non CASCADE: cancellando l'argomento le voci sotto NON si
    # perdono, tornano sciolte. In una scheda che vive per anni buttare via lo
    # storico per un gesto solo sarebbe il danno peggiore possibile.
    genitore_id = Column(Integer, ForeignKey("voci_macchina.id", ondelete="SET NULL"),
                         nullable=True, index=True)

    macchina = relationship("Macchina", back_populates="voci")
    autore = relationship("Utente")
    sezioni = relationship("SezioneMacchina", secondary=voce_sezione, back_populates="voci")
    # remote_side sull'id: dice a SQLAlchemy da che parte sta il "padre"
    # nella relazione di una tabella con se stessa.
    genitore = relationship("VoceMacchina", remote_side=[id], back_populates="figlie")
    figlie = relationship("VoceMacchina", back_populates="genitore",
                          order_by="VoceMacchina.creato_il")
    allegati = relationship("Allegato", back_populates="voce", cascade="all, delete-orphan")
