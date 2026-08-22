"""
Router di autenticazione: registrazione e login.

- /auth/register : crea AZIENDA + primo utente (admin) insieme. E' l'unico
  modo legittimo di far nascere un'azienda. Ritorna subito un token (auto-login).
- /auth/login    : email + password -> token JWT.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.organizzazione import Organizzazione
from app.models.utente import Utente, RuoloUtente
from app.schemas.utente import UtenteRead
from app.security import (
    verifica_password, crea_token, hash_password,
    crea_token_scopo, leggi_token_scopo,
)
from app.schemas.validators import PasswordStr
from app.dependencies import get_current_user
from app.notifiche import invia_email

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPO_VERIFICA = "verifica_email"


def _invia_verifica(utente: Utente) -> None:
    """Genera il link di verifica e lo 'invia' (in sviluppo: log)."""
    token = crea_token_scopo(utente.id, SCOPO_VERIFICA, durata_minuti=60 * 24)
    # Il link punta a questo backend; l'utente ci clicca e l'email risulta verificata.
    link = f"{settings.base_url}/auth/verifica-email?token={token}"
    invia_email(
        destinatario=utente.email,
        oggetto="Conferma la tua email - CoordSync",
        corpo=f"Ciao {utente.nome},\nconferma la tua email cliccando qui:\n{link}\n\nIl link scade tra 24 ore.",
    )


# ---------- REGISTRAZIONE ----------

class RegisterRichiesta(BaseModel):
    nome_azienda: str
    nome: str
    email: EmailStr
    password: PasswordStr


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
        ruolo=RuoloUtente.admin,
        organizzazione_id=org.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Invio l'email di verifica (in sviluppo: link nei log).
    _invia_verifica(admin)

    # Lo loggo subito: gli restituisco un token.
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


@router.get("/me", response_model=UtenteRead)
def leggi_me(current: Utente = Depends(get_current_user)):
    """Restituisce l'utente attualmente loggato (nome, email, ruolo, azienda).
    Serve al frontend per sapere che ruolo ho e adattare l'interfaccia."""
    return current


@router.get("/verifica-email", response_class=HTMLResponse)
def verifica_email(token: str, db: Session = Depends(get_db)):
    """L'utente arriva qui cliccando il link nell'email. Se il token e' valido,
    segna l'email come verificata."""
    utente_id = leggi_token_scopo(token, SCOPO_VERIFICA)
    if utente_id is None:
        return HTMLResponse("<h2>Link non valido o scaduto.</h2>", status_code=400)

    utente = db.query(Utente).filter(Utente.id == int(utente_id)).first()
    if utente is None:
        return HTMLResponse("<h2>Utente non trovato.</h2>", status_code=404)

    utente.email_verificata = True
    db.commit()
    return HTMLResponse("<h2>Email verificata. Puoi tornare all'app e accedere.</h2>")


@router.post("/reinvia-verifica", status_code=202)
def reinvia_verifica(current: Utente = Depends(get_current_user)):
    """Reinvia il link di verifica all'utente loggato (se non gia' verificato)."""
    if current.email_verificata:
        return {"messaggio": "Email gia' verificata"}
    _invia_verifica(current)
    return {"messaggio": "Email di verifica inviata"}
