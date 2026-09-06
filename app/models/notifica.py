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
                                    # o sotto una tua voce di macchina
    impegno = "impegno"             # ti hanno messo in agenda un impegno o una riunione
    menzione = "menzione"           # qualcuno ti ha nominato in un commento


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
    voce_id = Column(Integer, ForeignKey("voci_macchina.id", ondelete="SET NULL"), nullable=True)

    utente = relationship("Utente")
    voce = relationship("VoceMacchina")

    @property
    def macchina_id(self) -> int | None:
        """Su quale macchina porta questo avviso.

        Non e' una colonna: si ricava dalla voce. Salvarlo a parte vorrebbe
        dire tenere allineati due dati che dicono la stessa cosa, e un giorno
        non lo sarebbero piu'. Se la voce e' stata cancellata torna None e
        l'avviso resta leggibile ma non porta piu' da nessuna parte — la
        stessa cosa che gia' fanno lavoro_id e impegno_id.
        """
        return self.voce.macchina_id if self.voce is not None else None
