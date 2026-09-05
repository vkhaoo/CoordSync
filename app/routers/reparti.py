"""
Router dei Reparti: sotto-gruppi dentro l'azienda.

Crearli, rinominarli, eliminarli e gestirne i membri e' roba da ADMIN.
L'elenco invece lo puo' leggere chiunque sia loggato: serve al frontend per
mostrare a che reparto appartiene un progetto e per il menu di assegnazione.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.appartenenze import condizione_membro
from app.database import get_db
from app.models.reparto import Reparto
from app.models.utente import Utente, RuoloUtente
from app.schemas.reparto import RepartoCreate, RepartoRead, RepartoUpdate
from app.dependencies import richiedi_azienda, richiedi_ruolo

router = APIRouter(prefix="/reparti", tags=["reparti"])


def _reparto_mio(db: Session, reparto_id: int, current: Utente) -> Reparto | None:
    """Il reparto, ma solo se e' della MIA azienda."""
    return (
        db.query(Reparto)
        .filter(Reparto.id == reparto_id,
                Reparto.organizzazione_id == current.org_attiva_id)
        .first()
    )


@router.post("", response_model=RepartoRead, status_code=201)
def crea_reparto(dati: RepartoCreate, db: Session = Depends(get_db),
                 current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    reparto = Reparto(nome=dati.nome, organizzazione_id=current.org_attiva_id)
    db.add(reparto)
    db.commit()
    db.refresh(reparto)
    return reparto


@router.get("", response_model=list[RepartoRead])
def elenca_reparti(db: Session = Depends(get_db),
                   current: Utente = Depends(richiedi_azienda)):
    return (
        db.query(Reparto)
        .filter(Reparto.organizzazione_id == current.org_attiva_id)
        .all()
    )


@router.patch("/{reparto_id}", response_model=RepartoRead)
def rinomina_reparto(reparto_id: int, dati: RepartoUpdate, db: Session = Depends(get_db),
                     current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    reparto = _reparto_mio(db, reparto_id, current)
    if reparto is None:
        raise HTTPException(status_code=404, detail="Reparto non trovato")
    if dati.nome is not None:
        reparto.nome = dati.nome
    db.commit()
    db.refresh(reparto)
    return reparto


@router.delete("/{reparto_id}", status_code=204)
def elimina_reparto(reparto_id: int, db: Session = Depends(get_db),
                    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    reparto = _reparto_mio(db, reparto_id, current)
    if reparto is None:
        raise HTTPException(status_code=404, detail="Reparto non trovato")
    # I progetti NON spariscono: tornano "generali" (reparto_id a NULL, per via
    # dell'ondelete SET NULL). Eliminare un reparto non deve distruggere lavoro.
    db.delete(reparto)
    db.commit()


# ---------- MEMBRI ----------

class MembroRichiesta(BaseModel):
    utente_id: int


@router.post("/{reparto_id}/membri", response_model=RepartoRead, status_code=201)
def aggiungi_membro(reparto_id: int, dati: MembroRichiesta, db: Session = Depends(get_db),
                    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    reparto = _reparto_mio(db, reparto_id, current)
    if reparto is None:
        raise HTTPException(status_code=404, detail="Reparto non trovato")

    # Si possono mettere nel reparto SOLO colleghi della mia azienda.
    utente = (
        db.query(Utente)
        .filter(Utente.id == dati.utente_id,
                condizione_membro(current.org_attiva_id))
        .first()
    )
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    if utente not in reparto.membri:
        reparto.membri.append(utente)
        db.commit()
        db.refresh(reparto)
    return reparto


@router.delete("/{reparto_id}/membri/{utente_id}", response_model=RepartoRead)
def rimuovi_membro(reparto_id: int, utente_id: int, db: Session = Depends(get_db),
                   current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    reparto = _reparto_mio(db, reparto_id, current)
    if reparto is None:
        raise HTTPException(status_code=404, detail="Reparto non trovato")

    utente = db.query(Utente).filter(Utente.id == utente_id).first()
    if utente is not None and utente in reparto.membri:
        reparto.membri.remove(utente)
        db.commit()
        db.refresh(reparto)
    return reparto
