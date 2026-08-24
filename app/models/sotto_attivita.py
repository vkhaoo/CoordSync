"""Modello SottoAttivita: una voce della checklist di un lavoro."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SottoAttivita(Base):
    __tablename__ = "sotto_attivita"

    id = Column(Integer, primary_key=True, index=True)
    testo = Column(String, nullable=False)
    completata = Column(Boolean, default=False, nullable=False)

    # Ogni sotto-attivita' appartiene a un lavoro. Se il lavoro viene cancellato,
    # spariscono anche le sue sotto-attivita' (ondelete CASCADE).
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="CASCADE"), nullable=False)
    lavoro = relationship("Lavoro", back_populates="sotto_attivita")
