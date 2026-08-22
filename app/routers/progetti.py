"""Router dei Progetti: protetto da login, filtrato per organizzazione."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.schemas.progetto import ProgettoCreate, ProgettoRead
from app.dependencies import get_current_user

router = APIRouter(prefix="/progetti", tags=["progetti"])


@router.post("", response_model=ProgettoRead, status_code=201)
def crea_progetto(
    dati: ProgettoCreate,
    db: Session = Depends(get_db),
    current: Utente = Depends(get_current_user),
):
    # L'organizzazione la prende dall'utente loggato, NON dal client.
    progetto = Progetto(
        nome=dati.nome,
        descrizione=dati.descrizione,
        organizzazione_id=current.organizzazione_id,
    )
    db.add(progetto)
    db.commit()
    db.refresh(progetto)
    return progetto


@router.get("", response_model=list[ProgettoRead])
def elenca_progetti(
    db: Session = Depends(get_db),
    current: Utente = Depends(get_current_user),
):
    # Solo i progetti della MIA organizzazione.
    return (
        db.query(Progetto)
        .filter(Progetto.organizzazione_id == current.organizzazione_id)
        .all()
    )
