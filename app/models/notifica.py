"""
Modello Notifica: un avviso dentro l'app, per la campanella in alto.

NB: da non confondere con app/notifiche.py, che manda le EMAIL. Questo e' il
cugino interno all'app, quello che non esce da CoordSync.

Il testo viene salvato gia' composto, e non ricostruito ogni volta dai dati
collegati. Sembra contro la regola "i dati derivati si calcolano", ma qui non
e' un dato derivato: e' la fotografia di un fatto avvenuto. Se il lavoro viene
rinominato o cancellato, l'avviso deve continuare a raccontare cosa e'
successo quel giorno, non cambiare sotto gli occhi di chi lo legge.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.database import Base


class TipoAvviso(str, enum.Enum):
    assegnazione = "assegnazione"   # ti hanno messo su un lavoro
    commento = "commento"           # qualcuno ha scritto su un tuo lavoro
    impegno = "impegno"             # ti hanno messo in agenda un impegno o una riunione


class Notifica(Base):
    __tablename__ = "notifiche"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(SAEnum(TipoAvviso), nullable=False)
    testo = Column(String, nullable=False)
    letta = Column(Boolean, nullable=False, default=False)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # A chi e' destinato l'avviso.
    utente_id = Column(Integer, ForeignKey("utenti.id", ondelete="CASCADE"),
                       nullable=False, index=True)

    # Dove porta, se il posto esiste ancora. SET NULL e non CASCADE: cancellato
    # il lavoro, l'avviso resta leggibile, semplicemente non porta piu' da
    # nessuna parte.
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="SET NULL"), nullable=True)
    impegno_id = Column(Integer, ForeignKey("impegni.id", ondelete="SET NULL"), nullable=True)

    utente = relationship("Utente")
