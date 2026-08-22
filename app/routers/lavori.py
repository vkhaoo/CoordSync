"""Router dei Lavori: protetto da login, isolato per organizzazione.

Un lavoro appartiene a un'organizzazione attraverso il suo progetto:
quindi filtriamo/verifichiamo sempre facendo il JOIN con Progetto e
controllando che il progetto sia della MIA organizzazione.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lavoro import Lavoro, StatoLavoro
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.schemas.lavoro import LavoroCreate, LavoroRead, LavoroUpdateStato
from app.dependencies import get_current_user

router = APIRouter(prefix="/lavori", tags=["lavori"])


def _progetto_mio(db, progetto_id, current):
    """Ritorna il progetto SOLO se e' della mia organizzazione, altrimenti None."""
    return (
        db.query(Progetto)
        .filter(Progetto.id == progetto_id,
                Progetto.organizzazione_id == current.organizzazione_id)
        .first()
    )


def _lavoro_mio(db, lavoro_id, current):
    """Ritorna il lavoro SOLO se sta in un progetto della mia organizzazione."""
    return (
        db.query(Lavoro)
        .join(Progetto)
        .filter(Lavoro.id == lavoro_id,
                Progetto.organizzazione_id == current.organizzazione_id)
        .first()
    )


@router.post("", response_model=LavoroRead, status_code=201)
def crea_lavoro(dati: LavoroCreate, db: Session = Depends(get_db),
                current: Utente = Depends(get_current_user)):
    # Il progetto deve esistere ED essere della mia organizzazione.
    if _progetto_mio(db, dati.progetto_id, current) is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato")

    lavoro = Lavoro(
        titolo=dati.titolo,
        descrizione=dati.descrizione,
        priorita=dati.priorita,
        progetto_id=dati.progetto_id,
    )
    db.add(lavoro)
    db.commit()
    db.refresh(lavoro)
    return lavoro


@router.get("", response_model=list[LavoroRead])
def elenca_lavori(progetto_id: int | None = None, stato: StatoLavoro | None = None,
                  db: Session = Depends(get_db),
                  current: Utente = Depends(get_current_user)):
    # Parto SEMPRE dai soli lavori della mia organizzazione.
    query = (
        db.query(Lavoro)
        .join(Progetto)
        .filter(Progetto.organizzazione_id == current.organizzazione_id)
    )
    if progetto_id is not None:
        query = query.filter(Lavoro.progetto_id == progetto_id)
    if stato is not None:
        query = query.filter(Lavoro.stato == stato)
    return query.all()


@router.patch("/{lavoro_id}/stato", response_model=LavoroRead)
def cambia_stato(lavoro_id: int, dati: LavoroUpdateStato,
                 db: Session = Depends(get_db),
                 current: Utente = Depends(get_current_user)):
    lavoro = _lavoro_mio(db, lavoro_id, current)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    lavoro.stato = dati.stato
    db.commit()
    db.refresh(lavoro)
    return lavoro
