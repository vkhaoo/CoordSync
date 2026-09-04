"""
Allegato: un link appeso a una scheda (foto del quadro su Drive, PDF di uno
schema, un foglio di calcolo...).

Perche' solo LINK e non file veri: il piano gratuito di Render non ha uno
storage persistente, quindi un file caricato sparirebbe al riavvio. Il link
costa zero infrastruttura e risolve il bisogno vero ("mettere tutto li'").

Un allegato appartiene a UNA sola scheda. Invece di una tabella generica senza
vincoli, ogni possibile genitore ha la sua colonna: cosi' il database garantisce
che il riferimento sia valido e ripulisce da solo quando la scheda sparisce
(ondelete CASCADE). Gli endpoint sono per-genitore, quindi la regola "uno solo"
e' rispettata per costruzione.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Allegato(Base):
    __tablename__ = "allegati"

    id = Column(Integer, primary_key=True, index=True)
    # Etichetta leggibile; se non la scrivi, il frontend mostra il link.
    titolo = Column(String, nullable=True)
    url = Column(String, nullable=False)
    creato_il = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    autore_id = Column(Integer, ForeignKey("utenti.id", ondelete="SET NULL"), nullable=True)

    # I possibili genitori: esattamente uno valorizzato.
    macchina_id = Column(Integer, ForeignKey("macchine.id", ondelete="CASCADE"), nullable=True, index=True)
    sezione_id = Column(Integer, ForeignKey("sezioni_macchina.id", ondelete="CASCADE"), nullable=True, index=True)
    voce_id = Column(Integer, ForeignKey("voci_macchina.id", ondelete="CASCADE"), nullable=True, index=True)
    progetto_id = Column(Integer, ForeignKey("progetti.id", ondelete="CASCADE"), nullable=True, index=True)
    lavoro_id = Column(Integer, ForeignKey("lavori.id", ondelete="CASCADE"), nullable=True, index=True)

    autore = relationship("Utente")
    macchina = relationship("Macchina", back_populates="allegati")
    sezione = relationship("SezioneMacchina", back_populates="allegati")
    voce = relationship("VoceMacchina", back_populates="allegati")
    progetto = relationship("Progetto", back_populates="allegati")
    lavoro = relationship("Lavoro", back_populates="allegati")
