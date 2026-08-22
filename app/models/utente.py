"""Modello Utente: tu e i colleghi."""
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Utente(Base):
    __tablename__ = "utenti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)

    # is_admin: il primo utente di un'azienda (chi la registra) e' admin.
    # Solo un admin puo' aggiungere altri utenti alla propria azienda.
    is_admin = Column(Boolean, default=False, nullable=False)

    # Ogni utente appartiene a un'organizzazione (il "tenant").
    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id"), nullable=False)
    organizzazione = relationship("Organizzazione", back_populates="utenti")

    # 'lavori' NON e' una colonna: e' una scorciatoia che, dato un utente,
    # ti da' la lista dei lavori a cui e' assegnato (via tabella-ponte).
    lavori = relationship("Lavoro", secondary="assegnazioni", back_populates="assegnatari")
