"""
Router di autenticazione: registrazione e login.

- /auth/register : crea AZIENDA + primo utente (admin) insieme. E' l'unico
  modo legittimo di far nascere un'azienda. Ritorna subito un token (auto-login).
- /auth/login    : email + password -> token JWT.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organizzazione import Organizzazione
from app.models.utente import Utente
from app.security import verifica_password, crea_token, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- REGISTRAZIONE ----------

class RegisterRichiesta(BaseModel):
    nome_azienda: str
    nome: str
    email: EmailStr
    password: str


class TokenRisposta(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenRisposta, status_code=201)
def register(dati: RegisterRichiesta, db: Session = Depends(get_db)):
    # L'email non deve essere gia' in uso.
    if db.query(Utente).filter(Utente.email == dati.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email gia' registrata")

    # 1) Creo l'azienda.
    org = Organizzazione(nome=dati.nome_azienda)
    db.add(org)
    db.flush()   # assegna un id a org senza chiudere la transazione

    # 2) Creo il primo utente, che diventa ADMIN dell'azienda.
    admin = Utente(
        nome=dati.nome,
        email=dati.email,
        password_hash=hash_password(dati.password),
        is_admin=True,
        organizzazione_id=org.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # 3) Lo loggo subito: gli restituisco un token.
    return TokenRisposta(access_token=crea_token(admin.id))


# ---------- LOGIN ----------

class LoginRichiesta(BaseModel):
    email: EmailStr
    password: str


@router.post("/login", response_model=TokenRisposta)
def login(dati: LoginRichiesta, db: Session = Depends(get_db)):
    utente = db.query(Utente).filter(Utente.email == dati.email).first()
    # Stesso errore generico se l'utente non c'e' o la password e' sbagliata.
    if utente is None or utente.password_hash is None:
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    if not verifica_password(dati.password, utente.password_hash):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    return TokenRisposta(access_token=crea_token(utente.id))
