"""
Router degli Utenti: creazione e gestione ruoli, riservate all'ADMIN.

L'admin aggiunge utenti (scegliendone il ruolo) e puo' cambiare il ruolo
degli utenti della sua azienda. Il nuovo utente eredita l'organizzazione
da chi lo crea.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.utente import Utente, RuoloUtente
from app.schemas.utente import UtenteCreate, UtenteRead
from app.security import hash_password, crea_token_scopo
from app.dependencies import get_current_user, richiedi_ruolo
from app.notifiche import invia_email
from app.email_templates import invito as email_invito_template
from app.routers.auth import SCOPO_INVITO

router = APIRouter(prefix="/utenti", tags=["utenti"])


@router.post("", response_model=UtenteRead, status_code=201)
def crea_utente(dati: UtenteCreate, db: Session = Depends(get_db),
                current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    if db.query(Utente).filter(Utente.email == dati.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email gia' registrata")

    utente = Utente(
        nome=dati.nome,
        email=dati.email,
        password_hash=hash_password(dati.password),
        ruolo=dati.ruolo,
        organizzazione_id=current.organizzazione_id,
    )
    db.add(utente)
    db.commit()
    db.refresh(utente)
    return utente


class InvitoRichiesta(BaseModel):
    nome: str
    email: EmailStr
    ruolo: RuoloUtente = RuoloUtente.operatore


@router.post("/invita", response_model=UtenteRead, status_code=201)
def invita_utente(dati: InvitoRichiesta, db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    """L'admin invita con solo nome + email: l'utente nasce SENZA password
    (la scegliera' lui dal link email). Onboarding 'da SaaS'."""
    if db.query(Utente).filter(Utente.email == dati.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email gia' registrata")

    utente = Utente(
        nome=dati.nome,
        email=dati.email,
        password_hash=None,   # niente password: la imposta l'invitato
        ruolo=dati.ruolo,
        organizzazione_id=current.organizzazione_id,
    )
    db.add(utente)
    db.commit()
    db.refresh(utente)

    # 7 giorni di validita': un invito puo' restare qualche giorno nella casella.
    token = crea_token_scopo(utente.id, SCOPO_INVITO, durata_minuti=60 * 24 * 7)
    link = f"{settings.frontend_url}/?invito_token={token}"
    oggetto, testo, html = email_invito_template(
        utente.nome, current.organizzazione.nome, link)
    invia_email(destinatario=utente.email, oggetto=oggetto, corpo=testo, corpo_html=html)
    return utente


@router.get("", response_model=list[UtenteRead])
def elenca_utenti(db: Session = Depends(get_db),
                  current: Utente = Depends(get_current_user)):
    return (
        db.query(Utente)
        .filter(Utente.organizzazione_id == current.organizzazione_id)
        .all()
    )


class CambioRuolo(BaseModel):
    ruolo: RuoloUtente


@router.patch("/{utente_id}/ruolo", response_model=UtenteRead)
def cambia_ruolo(utente_id: int, dati: CambioRuolo, db: Session = Depends(get_db),
                 current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    # Solo utenti della MIA azienda.
    utente = (
        db.query(Utente)
        .filter(Utente.id == utente_id,
                Utente.organizzazione_id == current.organizzazione_id)
        .first()
    )
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    utente.ruolo = dati.ruolo
    db.commit()
    db.refresh(utente)
    return utente
