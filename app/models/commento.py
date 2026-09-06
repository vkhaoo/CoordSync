"""
Modello Commento: un messaggio attaccato a un lavoro o a una voce di macchina.

E' il cuore del "coordinamento per lavoro": invece di una chat generica,
la conversazione resta legata alla cosa di cui si sta parlando.

DOVE PUO' STARE. Come per gli allegati, ogni possibile genitore ha la sua
colonna e ne e' valorizzata esattamente una: cosi' il database garantisce che
il riferimento sia valido e fa pulizia da solo quando il genitore sparisce
(ondelete CASCADE). Gli endpoint sono per-genitore, quindi la regola "uno solo"
e' rispettata per costruzione.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Commento(Base):
    __tablename__ = "commenti"

    id = Column(Integer, primary_key=True, index=True)
    testo = Column(String, nullable=False)

    # Dove sta: un lavoro di progetto, oppure una voce del taccuino di una
    # macchina. Uno dei due, mai tutti e due e mai nessuno.
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="CASCADE"),
                       nullable=True, index=True)
    voce_id = Column(Integer, ForeignKey("voci_macchina.id", ondelete="CASCADE"),
                     nullable=True, index=True)
    # Chi l'ha scritto.
    autore_id = Column(Integer, ForeignKey("utenti.id"), nullable=False)

    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Scorciatoie di navigazione: dato un commento, risali all'autore o al posto
    # in cui e' stato scritto.
    autore = relationship("Utente")
    lavoro = relationship("Lavoro")
    voce = relationship("VoceMacchina", back_populates="commenti")
