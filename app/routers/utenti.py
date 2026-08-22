"""
Router degli Utenti: creazione protetta.

Aggiungere un utente a un'azienda e' un'azione riservata all'ADMIN di
quell'azienda. Il nuovo utente EREDITA l'organizzazione da chi lo crea
(non la si dichiara piu' nel body). Cosi' non si possono creare utenti
in aziende altrui.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.utente import Utente
from app.schemas.utente import UtenteCreate, UtenteRead
from app.security import hash_password
from app.dependencies import get_current_user

router = APIRouter(prefix="/utenti", tags=["utenti"])


@router.post("", response_model=UtenteRead, status_code=201)
def crea_utente(dati: UtenteCreate, db: Session = Depends(get_db),
                current: Utente = Depends(get_current_user)):
    # Solo un admin puo' aggiungere utenti alla propria azienda.
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Serve essere admin")

    # Email unica.
    if db.query(Utente).filter(Utente.email == dati.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email gia' registrata")

    # Eredita l'organizzazione da chi lo crea. Nuovo utente NON admin.
    utente = Utente(
        nome=dati.nome,
        email=dati.email,
        password_hash=hash_password(dati.password),
        is_admin=False,
        organizzazione_id=current.organizzazione_id,
    )
    db.add(utente)
    db.commit()
    db.refresh(utente)
    return utente


@router.get("", response_model=list[UtenteRead])
def elenca_utenti(db: Session = Depends(get_db),
                  current: Utente = Depends(get_current_user)):
    # Solo gli utenti della MIA organizzazione.
    return (
        db.query(Utente)
        .filter(Utente.organizzazione_id == current.organizzazione_id)
        .all()
    )
