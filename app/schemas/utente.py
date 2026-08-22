"""
Schemi Pydantic per l'Utente.

Per ora l'utente e' una semplice identita': nome + email.
La password/login arrivera' come milestone dedicata (autenticazione).
EmailStr valida che l'email abbia un formato plausibile.
"""
from pydantic import BaseModel, ConfigDict, EmailStr


class UtenteBase(BaseModel):
    nome: str
    email: EmailStr   # valida il formato: "pippo" viene rifiutato, "a@b.it" no


class UtenteCreate(UtenteBase):
    password: str   # salvata come impronta (hash), mai in chiaro
    # organizzazione_id NON serve piu': ereditata da chi crea l'utente


class UtenteRead(UtenteBase):
    id: int
    organizzazione_id: int
    is_admin: bool
    model_config = ConfigDict(from_attributes=True)
