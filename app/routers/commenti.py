"""Router dei Commenti: protetto, autore = utente loggato, isolato per org."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.commento import Commento
from app.models.lavoro import Lavoro
from app.models.progetto import Progetto
from app.models.utente import Utente, RuoloUtente
from app.schemas.commento import CommentoCreate, CommentoRead
from app.dependencies import get_current_user

router = APIRouter(prefix="/lavori/{lavoro_id}/commenti", tags=["commenti"])


def _lavoro_mio(db, lavoro_id, current):
    return (
        db.query(Lavoro)
        .join(Progetto)
        .filter(Lavoro.id == lavoro_id,
                Progetto.organizzazione_id == current.organizzazione_id)
        .first()
    )


@router.post("", response_model=CommentoRead, status_code=201)
def aggiungi_commento(lavoro_id: int, dati: CommentoCreate,
                      db: Session = Depends(get_db),
                      current: Utente = Depends(get_current_user)):
    lavoro = _lavoro_mio(db, lavoro_id, current)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    # L'operatore puo' commentare SOLO i lavori a lui assegnati.
    if current.ruolo == RuoloUtente.operatore:
        assegnato = any(u.id == current.id for u in lavoro.assegnatari)
        if not assegnato:
            raise HTTPException(status_code=403, detail="Puoi commentare solo i lavori a te assegnati")

    # L'autore e' chi e' loggato: non si puo' commentare "a nome di" un altro.
    commento = Commento(testo=dati.testo, lavoro_id=lavoro_id, autore_id=current.id)
    db.add(commento)
    db.commit()
    db.refresh(commento)
    return commento


@router.get("", response_model=list[CommentoRead])
def elenca_commenti(lavoro_id: int, db: Session = Depends(get_db),
                    current: Utente = Depends(get_current_user)):
    if _lavoro_mio(db, lavoro_id, current) is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    return (
        db.query(Commento)
        .filter(Commento.lavoro_id == lavoro_id)
        .order_by(Commento.creato_il)
        .all()
    )
