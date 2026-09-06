"""Modello SottoAttivita: una voce di checklist.

Sta sotto un lavoro di progetto oppure sotto una voce del taccuino di una
macchina — uno dei due, mai tutti e due. Stessa forma degli allegati e dei
commenti: una colonna per ogni possibile genitore, cosi' il database garantisce
il riferimento e fa pulizia da solo (ondelete CASCADE).
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SottoAttivita(Base):
    __tablename__ = "sotto_attivita"

    id = Column(Integer, primary_key=True, index=True)
    testo = Column(String, nullable=False)
    completata = Column(Boolean, default=False, nullable=False)

    # Il genitore: un lavoro, oppure una voce di macchina. Se sparisce lui,
    # spariscono anche le sue voci di checklist (ondelete CASCADE).
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="CASCADE"),
                       nullable=True, index=True)
    voce_id = Column(Integer, ForeignKey("voci_macchina.id", ondelete="CASCADE"),
                     nullable=True, index=True)

    lavoro = relationship("Lavoro", back_populates="sotto_attivita")
    voce = relationship("VoceMacchina", back_populates="sotto_attivita")
