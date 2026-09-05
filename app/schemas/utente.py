"""
Schemi Pydantic per l'Utente.

Per ora l'utente e' una semplice identita': nome + email.
La password/login arrivera' come milestone dedicata (autenticazione).
EmailStr valida che l'email abbia un formato plausibile.
"""
from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.utente import RuoloUtente
from app.schemas.validators import PasswordStr
from app.schemas.reparto import RepartoRead


class UtenteBase(BaseModel):
    nome: str
    email: EmailStr   # valida il formato: "pippo" viene rifiutato, "a@b.it" no


class UtenteCreate(UtenteBase):
    password: PasswordStr   # regole minime di robustezza + hash, mai in chiaro
    ruolo: RuoloUtente = RuoloUtente.operatore   # l'admin sceglie il ruolo (default: operatore)
    # organizzazione_id NON serve piu': ereditata da chi crea l'utente


class UtenteRead(UtenteBase):
    id: int
    # Vuoti finche' non si fa parte di nessuna azienda: e' lo stato di chi si
    # e' appena iscritto e deve ancora crearne una o accettare un invito.
    organizzazione_id: int | None = None
    ruolo: RuoloUtente | None = None
    email_verificata: bool
    deve_cambiare_password: bool   # il frontend blocca l'accesso finche' e' True
    reparti: list[RepartoRead] = []   # i reparti di cui faccio parte
    model_config = ConfigDict(from_attributes=True)
