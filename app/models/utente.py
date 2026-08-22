"""Modello Utente: tu e i colleghi."""
import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class RuoloUtente(str, enum.Enum):
    """I tre ruoli. admin > caposquadra > operatore per quello che possono fare."""
    admin = "admin"              # gestisce tutto, inclusi utenti e ruoli
    caposquadra = "caposquadra"  # crea progetti/lavori, assegna, cambia stati
    operatore = "operatore"      # esegue: aggiorna solo i lavori a lui assegnati


class Utente(Base):
    __tablename__ = "utenti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)

    # Ruolo dell'utente nella sua azienda. Default: operatore (il meno privilegiato).
    ruolo = Column(SAEnum(RuoloUtente), default=RuoloUtente.operatore, nullable=False)

    # Email verificata tramite link inviato via email. Default: non verificata.
    email_verificata = Column(Boolean, default=False, nullable=False)

    # Ogni utente appartiene a un'organizzazione (il "tenant").
    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id"), nullable=False)
    organizzazione = relationship("Organizzazione", back_populates="utenti")

    # 'lavori' NON e' una colonna: e' una scorciatoia che, dato un utente,
    # ti da' la lista dei lavori a cui e' assegnato (via tabella-ponte).
    lavori = relationship("Lavoro", secondary="assegnazioni", back_populates="assegnatari")
