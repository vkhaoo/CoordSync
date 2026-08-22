"""
Router delle Assegnazioni: chi lavora su un lavoro (molti-a-molti).

Usa la tabella-ponte 'assegnazioni' predisposta all'inizio.
Regola di sicurezza: puoi assegnare SOLO colleghi della tua stessa azienda,
e solo su lavori della tua azienda.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lavoro import Lavoro
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.schemas.lavoro import LavoroRead
from app.models.utente import RuoloUtente
from app.dependencies import get_current_user, richiedi_ruolo

router = APIRouter(prefix="/lavori/{lavoro_id}/assegnati", tags=["assegnazioni"])


class AssegnaRichiesta(BaseModel):
    utente_id: int


def _lavoro_mio(db, lavoro_id, current):
    return (
        db.query(Lavoro).join(Progetto)
        .filter(Lavoro.id == lavoro_id,
                Progetto.organizzazione_id == current.organizzazione_id)
        .first()
    )


@router.post("", response_model=LavoroRead, status_code=201)
def assegna(lavoro_id: int, dati: AssegnaRichiesta, db: Session = Depends(get_db),
            current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    lavoro = _lavoro_mio(db, lavoro_id, current)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    # L'utente da assegnare deve essere della MIA azienda.
    utente = (
        db.query(Utente)
        .filter(Utente.id == dati.utente_id,
                Utente.organizzazione_id == current.organizzazione_id)
        .first()
    )
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Evito doppioni: se e' gia' assegnato, non lo aggiungo di nuovo.
    if utente not in lavoro.assegnatari:
        lavoro.assegnatari.append(utente)   # <- aggiunge una riga nella tabella-ponte
        db.commit()
        db.refresh(lavoro)
    return lavoro


@router.delete("/{utente_id}", response_model=LavoroRead)
def rimuovi(lavoro_id: int, utente_id: int, db: Session = Depends(get_db),
            current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    lavoro = _lavoro_mio(db, lavoro_id, current)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    utente = db.query(Utente).filter(Utente.id == utente_id).first()
    if utente is not None and utente in lavoro.assegnatari:
        lavoro.assegnatari.remove(utente)   # <- toglie la riga dalla tabella-ponte
        db.commit()
        db.refresh(lavoro)
    return lavoro
