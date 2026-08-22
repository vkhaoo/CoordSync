"""Router delle Organizzazioni: crea ed elenca le aziende."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organizzazione import Organizzazione
from app.schemas.organizzazione import OrganizzazioneCreate, OrganizzazioneRead

router = APIRouter(prefix="/organizzazioni", tags=["organizzazioni"])


@router.post("", response_model=OrganizzazioneRead, status_code=201)
def crea_organizzazione(dati: OrganizzazioneCreate, db: Session = Depends(get_db)):
    org = Organizzazione(nome=dati.nome)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("", response_model=list[OrganizzazioneRead])
def elenca_organizzazioni(db: Session = Depends(get_db)):
    return db.query(Organizzazione).all()
