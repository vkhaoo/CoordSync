"""Router dei Progetti: protetto da login, filtrato per organizzazione."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.schemas.progetto import ProgettoCreate, ProgettoRead, ProgettoUpdate
from app.models.utente import RuoloUtente
from app.dependencies import get_current_user, richiedi_ruolo
from app.visibilita import progetti_visibili, progetto_visibile, reparto_assegnabile

router = APIRouter(prefix="/progetti", tags=["progetti"])


@router.post("", response_model=ProgettoRead, status_code=201)
def crea_progetto(
    dati: ProgettoCreate,
    db: Session = Depends(get_db),
    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)),
):
    # Non si puo' piazzare un progetto in un reparto che non e' mio.
    if not reparto_assegnabile(db, current, dati.reparto_id):
        raise HTTPException(status_code=404, detail="Reparto non trovato")

    # L'organizzazione la prende dall'utente loggato, NON dal client.
    progetto = Progetto(
        nome=dati.nome,
        descrizione=dati.descrizione,
        link_documento=dati.link_documento,
        organizzazione_id=current.organizzazione_id,
        reparto_id=dati.reparto_id,
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
    progetto = progetto_visibile(db, current, progetto_id)
    if progetto is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato")

    dati_forniti = dati.model_dump(exclude_unset=True)
    # Spostare un progetto in un altro reparto: vale la stessa regola della creazione.
    if "reparto_id" in dati_forniti and not reparto_assegnabile(db, current, dati_forniti["reparto_id"]):
        raise HTTPException(status_code=404, detail="Reparto non trovato")

    # Aggiorno solo i campi effettivamente forniti (gli altri restano invariati).
    for campo, valore in dati_forniti.items():
        setattr(progetto, campo, valore)
    db.commit()
    db.refresh(progetto)
    return progetto


@router.delete("/{progetto_id}", status_code=204)
def elimina_progetto(
    progetto_id: int,
    db: Session = Depends(get_db),
    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)),
):
    progetto = progetto_visibile(db, current, progetto_id)
    if progetto is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    # Cancellando il progetto spariscono in cascata i suoi lavori
    # (e a loro volta sotto-attivita' e commenti).
    db.delete(progetto)
    db.commit()


@router.get("", response_model=list[ProgettoRead])
def elenca_progetti(
    db: Session = Depends(get_db),
    current: Utente = Depends(get_current_user),
):
    # Azienda + reparto: la regola sta tutta in visibilita.py.
    return progetti_visibili(db, current).all()
