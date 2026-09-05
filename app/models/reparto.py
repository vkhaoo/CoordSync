"""
Modello Reparto: un sotto-gruppo dentro l'azienda (es. Digitale, Automazione).

E' il SECONDO livello di isolamento, sotto quello dell'organizzazione: serve a
non far vedere a un reparto i progetti di un altro.

Tutti e tre i legami col reparto sono molti-a-molti, perche' nella realta' le
cose si sovrappongono: una persona puo' seguire piu' reparti, e un progetto o
una macchina possono riguardarne piu' d'uno (una linea condivisa fra
Automazione e Digitale non appartiene a uno solo dei due).
"""
from datetime import datetime, timezone

from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

# Tabella-ponte utente <-> reparto: ogni riga dice "questo utente sta in questo reparto".
membro_reparto = Table(
    "membri_reparto",
    Base.metadata,
    Column("reparto_id", Integer, ForeignKey("reparti.id", ondelete="CASCADE"), primary_key=True),
    Column("utente_id", Integer, ForeignKey("utenti.id", ondelete="CASCADE"), primary_key=True),
)

# Progetto <-> reparto. Nessuna riga = progetto "generale", visto da tutta l'azienda.
progetto_reparto = Table(
    "progetti_reparto",
    Base.metadata,
    Column("progetto_id", Integer, ForeignKey("progetti.id", ondelete="CASCADE"), primary_key=True),
    Column("reparto_id", Integer, ForeignKey("reparti.id", ondelete="CASCADE"), primary_key=True),
)

# Macchina <-> reparto, stessa logica.
macchina_reparto = Table(
    "macchine_reparto",
    Base.metadata,
    Column("macchina_id", Integer, ForeignKey("macchine.id", ondelete="CASCADE"), primary_key=True),
    Column("reparto_id", Integer, ForeignKey("reparti.id", ondelete="CASCADE"), primary_key=True),
)


class Reparto(Base):
    __tablename__ = "reparti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Il reparto vive dentro un'azienda: due aziende possono avere reparti omonimi.
    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id"), nullable=False)

    membri = relationship("Utente", secondary=membro_reparto, back_populates="reparti")
    # Eliminando il reparto spariscono solo le righe delle tabelle-ponte: progetti
    # e macchine restano, e tornano "generali". Cancellare un reparto non deve
    # distruggere lavoro vero.
    progetti = relationship("Progetto", secondary=progetto_reparto, back_populates="reparti")
    macchine = relationship("Macchina", secondary=macchina_reparto, back_populates="reparti")
