"""Router dei Progetti: protetto da login, filtrato per organizzazione."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.schemas.progetto import ProgettoCreate, ProgettoRead, ProgettoUpdate
from app.models.utente import RuoloUtente
from app.dependencies import get_current_user, richiedi_ruolo

router = APIRouter(prefix="/progetti", tags=["progetti"])


@router.post("", response_model=ProgettoRead, status_code=201)
def crea_progetto(
    dati: ProgettoCreate,
    db: Session = Depends(get_db),
    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)),
):
    # L'organizzazione la prende dall'utente loggato, NON dal client.
    progetto = Progetto(
        nome=dati.nome,
        descrizione=dati.descrizione,
        link_documento=dati.link_documento,
        organizzazione_id=current.organizzazione_id,
    )
    db.add(progetto)
    db.commit()
    db.refresh(progetto)
    return progetto


@router.patch("/{progetto_id}", response_model=ProgettoRead)
def modifica_progetto(
    progetto_id: int,
    dati: ProgettoUpdate,
    db: Session = Depends(get_db),
    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)),
):
    progetto = (
        db.query(Progetto)
        .filter(Progetto.id == progetto_id,
                Progetto.organizzazione_id == current.organizzazione_id)
        .first()
    )
    if progetto is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Progetto non trovato")

    # Aggiorno solo i campi effettivamente forniti (gli altri restano invariati).
    for campo, valore in dati.model_dump(exclude_unset=True).items():
        setattr(progetto, campo, valore)
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
