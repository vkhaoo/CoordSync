"""
Modello Impegno: una riga dell'agenda.

NON e' la scadenza di un lavoro. La scadenza dice "entro quando"; l'impegno
dice "martedi' alle 9 sono da questo cliente". Per questo qui c'e' l'ORA, che
sulle scadenze non serve (sono solo date).

Un impegno ha PIU' partecipanti, cosi' una riunione e' UNA cosa sola che
compare nell'agenda di tutti quelli che ci sono dentro. Se si sposta l'orario,
si sposta per tutti: se invece ne facessimo una copia a testa, le copie
prenderebbero strade diverse alla prima modifica.

Chi lo crea resta segnato come organizzatore: e' lui (o chi coordina) a poterlo
modificare, non chiunque sia stato invitato.
"""
from datetime import datetime, timezone

from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


# Chi partecipa a un impegno. Una riunione ne ha molti, un impegno personale uno.
partecipante_impegno = Table(
    "partecipanti_impegno",
    Base.metadata,
    Column("impegno_id", Integer, ForeignKey("impegni.id", ondelete="CASCADE"), primary_key=True),
    Column("utente_id", Integer, ForeignKey("utenti.id", ondelete="CASCADE"), primary_key=True),
)


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

    # Chi ha organizzato l'impegno. E' lui a poterlo modificare o cancellare
    # (insieme a chi coordina): un invitato non deve poter spostare la riunione
    # a tutti gli altri.
    organizzatore_id = Column(Integer, ForeignKey("utenti.id", ondelete="CASCADE"),
                              nullable=False, index=True)

    # Collegamenti facoltativi, come per il resto dell'app: si usano se servono.
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="SET NULL"), nullable=True)
    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="SET NULL"), nullable=True)

    organizzatore = relationship("Utente", foreign_keys=[organizzatore_id])
    # Nelle agende di chi compare. L'organizzatore ci sta dentro quasi sempre,
    # ma non per forza: si puo' fissare una riunione a cui non si partecipa.
    partecipanti = relationship("Utente", secondary=partecipante_impegno)
    lavoro = relationship("Lavoro")
    macchina = relationship("Macchina")
