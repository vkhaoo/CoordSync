"""
Modello Impegno: una riga dell'agenda.

NON e' la scadenza di un lavoro. La scadenza dice "entro quando"; l'impegno
dice "martedi' alle 9 sono da questo cliente". Per questo qui c'e' l'ORA, che
sulle scadenze non serve (sono solo date).

L'impegno appartiene a una persona: e' la SUA agenda. Un caposquadra puo'
crearne uno per un collega (serve a organizzare gli interventi), ma resta
l'impegno di quella persona.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Impegno(Base):
    __tablename__ = "impegni"

    id = Column(Integer, primary_key=True, index=True)
    titolo = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    luogo = Column(String, nullable=True)   # "Stabilimento cliente X", "officina"...

    # Data E ora: e' quello che distingue un impegno da una scadenza.
    inizio = Column(DateTime, nullable=False, index=True)
    fine = Column(DateTime, nullable=True)   # facoltativa: non tutto ha una durata

    # Quanti minuti prima avvisare. NULL = nessun promemoria.
    promemoria_minuti = Column(Integer, nullable=True)
    # Segnato quando il promemoria e' partito, per non mandarlo due volte.
    promemoria_inviato_il = Column(DateTime, nullable=True)

    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Di chi e' l'agenda.
    utente_id = Column(Integer, ForeignKey("utenti.id", ondelete="CASCADE"),
                       nullable=False, index=True)

    # Collegamenti facoltativi, come per il resto dell'app: si usano se servono.
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="SET NULL"), nullable=True)
    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="SET NULL"), nullable=True)

    utente = relationship("Utente")
    lavoro = relationship("Lavoro")
    macchina = relationship("Macchina")
