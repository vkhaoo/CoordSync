"""Modello Utente: tu e i colleghi."""
import enum

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SAEnum, Boolean
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

    # True per gli utenti creati dall'admin con password: al primo accesso devono
    # sceglierne una loro (l'admin non deve conoscere la password di nessuno).
    deve_cambiare_password = Column(Boolean, default=False, nullable=False)

    # --- Secondo fattore (facoltativo, spento di default) --------------------
    # Il segreto condiviso col telefono. NULL = non l'ha mai preparato.
    totp_segreto = Column(String, nullable=True)
    # Acceso solo dopo che l'utente ha dimostrato di saper generare un codice
    # giusto: cosi' non ci si chiude fuori da soli configurandolo male.
    totp_attivo = Column(Boolean, default=False, nullable=False)
    # I codici di recupero, come impronte separate da virgola. Sono l'unica via
    # d'uscita se il telefono si perde.
    totp_recupero = Column(Text, nullable=True)

    # L'azienda "di casa": quella dove l'account e' nato. Resta il punto di
    # partenza quando si entra, ma non e' piu' l'unica a cui si puo'
    # appartenere: le altre stanno nelle appartenenze qui sotto.
    organizzazione_id = Column(Integer, ForeignKey("organizzazioni.id"), nullable=False)
    organizzazione = relationship("Organizzazione", back_populates="utenti")

    # Tutte le aziende di cui faccio parte, con il ruolo che ho in ognuna.
    appartenenze = relationship("Appartenenza", back_populates="utente",
                                cascade="all, delete-orphan")

    # 'lavori' NON e' una colonna: e' una scorciatoia che, dato un utente,
    # ti da' la lista dei lavori a cui e' assegnato (via tabella-ponte).
    lavori = relationship("Lavoro", secondary="assegnazioni", back_populates="assegnatari")

    # I reparti di cui faccio parte (un utente puo' starne in piu' d'uno).
    reparti = relationship("Reparto", secondary="membri_reparto", back_populates="membri")

    # --- L'azienda attiva in QUESTA richiesta ---------------------------------
    # Non sono colonne: le riempie get_current_user leggendo il token, e
    # spariscono alla fine della richiesta. Devono restare fuori dal database,
    # se no due dispositivi collegati su due aziende diverse si darebbero
    # fastidio a vicenda (l'ultimo che cambia deciderebbe per tutti).
    _org_attiva_id = None
    _ruolo_attivo = None

    @property
    def org_attiva_id(self) -> int:
        """L'azienda dentro cui sto lavorando adesso.

        Ogni query che filtra per azienda deve usare QUESTA, non
        organizzazione_id: quella dice solo dov'e' nato l'account."""
        return self._org_attiva_id or self.organizzazione_id

    @property
    def ruolo_attivo(self) -> RuoloUtente:
        """Il ruolo che ho NELL'AZIENDA ATTIVA: si puo' essere amministratori
        da una parte e operatori dall'altra."""
        return self._ruolo_attivo or self.ruolo
