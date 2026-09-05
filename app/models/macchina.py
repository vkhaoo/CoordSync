"""
Modelli Macchina e SezioneMacchina: lo "storico dell'impianto".

E' un mondo a se' rispetto a progetti e lavori. Un progetto e' una commessa che
prima o poi finisce; una macchina resta in fabbrica per anni e il suo valore e'
proprio la memoria che accumula. Per questo la scheda macchina ha voci proprie
invece di riusare i lavori di progetto.

Il collegamento fra i due mondi resta possibile ma facoltativo: un progetto o un
lavoro puo' puntare a una macchina (vedi Progetto.macchina_id e Lavoro.macchina_id).
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Macchina(Base):
    __tablename__ = "macchine"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    # Testo libero: qui dentro ci finiscono modello, matricola, note d'impianto.
    descrizione = Column(String, nullable=True)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id"), nullable=False)
    # Stesso meccanismo dei progetti: piu' reparti possibili, e nessun reparto
    # significa macchina visibile a tutta l'azienda.
    reparti = relationship("Reparto", secondary="macchine_reparto",
                           back_populates="macchine")

    sezioni = relationship("SezioneMacchina", back_populates="macchina",
                           cascade="all, delete-orphan",
                           order_by="SezioneMacchina.ordine")
    voci = relationship("VoceMacchina", back_populates="macchina",
                        cascade="all, delete-orphan")
    allegati = relationship("Allegato", back_populates="macchina",
                            cascade="all, delete-orphan")


class SezioneMacchina(Base):
    """Un pezzo della macchina: Confezione, Finizione, FAZ... I nomi li decide
    chi la usa, perche' cambiano da impianto a impianto."""
    __tablename__ = "sezioni_macchina"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    # Per tenerle nell'ordine in cui hanno senso sull'impianto, non alfabetico.
    ordine = Column(Integer, nullable=False, default=0)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="CASCADE"), nullable=False)
    macchina = relationship("Macchina", back_populates="sezioni")

    voci = relationship("VoceMacchina", secondary="voci_sezione", back_populates="sezioni")
    allegati = relationship("Allegato", back_populates="sezione",
                            cascade="all, delete-orphan")
