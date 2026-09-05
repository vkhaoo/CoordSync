"""
Appartenenza: la tessera che dice "questa persona lavora in questa azienda,
con questo ruolo".

PERCHE' ESISTE. Finora un utente apparteneva a UNA azienda, scritta sulla sua
riga (`utenti.organizzazione_id`). Va bene finche' ognuno lavora in un posto
solo, ma non regge il caso vero di Nik: chi fa consulenza segue piu' aziende, e
oggi deve tenere due account separati con due password e due caselle di posta.

COSA CAMBIA E COSA NO. Il ruolo sta sulla tessera e non piu' sulla persona:
si puo' essere amministratori da una parte e operatori dall'altra, che e'
esattamente come funziona nella realta'. La riga dell'utente conserva la sua
azienda "di casa" — quella dove e' nato l'account — che resta il punto di
partenza quando entra e non ha ancora scelto niente.

L'ISOLAMENTO NON SI TOCCA. Ogni richiesta continua a lavorare dentro UNA
azienda sola, quella attiva in quel momento: cambia solo il modo di sapere
qual e' (prima la riga dell'utente, adesso il token, verificato contro le
tessere). Nessuna query vede due aziende insieme, mai.
"""
from sqlalchemy import Column, Integer, ForeignKey, Enum as SAEnum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base
from app.models.utente import RuoloUtente


class Appartenenza(Base):
    __tablename__ = "appartenenze"

    # La coppia (persona, azienda) e' la chiave: non si puo' appartenere due
    # volte alla stessa azienda, e non serve un id inventato.
    utente_id = Column(Integer, ForeignKey("utenti.id", ondelete="CASCADE"),
                       primary_key=True)
    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id", ondelete="CASCADE"),
                               primary_key=True)

    # Il ruolo vale QUI: si puo' essere admin in un'azienda e operatore in
    # un'altra.
    ruolo = Column(SAEnum(RuoloUtente), nullable=False,
                   default=RuoloUtente.operatore)

    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    utente = relationship("Utente", back_populates="appartenenze")
    organizzazione = relationship("Organizzazione")
