"""
Router delle SottoAttivita (checklist di un lavoro).

Permessi:
- creare / eliminare una voce: admin e caposquadra (definiscono il lavoro)
- spuntare (completata) / modificare il testo: chi puo' aggiornare il lavoro
  (admin, caposquadra, oppure l'operatore SE assegnato a quel lavoro)
Tutto e' comunque isolato per organizzazione.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lavoro import Lavoro
from app.models.progetto import Progetto
from app.models.sotto_attivita import SottoAttivita
from app.models.utente import Utente, RuoloUtente
from app.schemas.sotto_attivita import (
    SottoAttivitaCreate, SottoAttivitaUpdate, SottoAttivitaRead,
)
from app.dependencies import get_current_user, richiedi_ruolo
from app.visibilita import lavoro_visibile, condizione_progetti_visibili

router = APIRouter(tags=["sotto-attivita"])


def _sotto_mia(db, sotto_id, current):
    """La voce di checklist, ma solo se posso vedere il lavoro a cui appartiene."""
    return (
        db.query(SottoAttivita).join(Lavoro).join(Progetto)
        .filter(SottoAttivita.id == sotto_id,
                Progetto.organizzazione_id == current.organizzazione_id,
                condizione_progetti_visibili(db, current))
        .first()
    )


def _puo_aggiornare(lavoro, current) -> bool:
    """Chi puo' spuntare le voci: admin/caposquadra, o l'operatore se assegnato."""
    if current.ruolo in (RuoloUtente.admin, RuoloUtente.caposquadra):
        return True
    return any(u.id == current.id for u in lavoro.assegnatari)


@router.get("/lavori/{lavoro_id}/sotto-attivita", response_model=list[SottoAttivitaRead])
def elenca(lavoro_id: int, db: Session = Depends(get_db),
           current: Utente = Depends(get_current_user)):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    return lavoro.sotto_attivita


@router.post("/lavori/{lavoro_id}/sotto-attivita", response_model=SottoAttivitaRead, status_code=201)
def crea(lavoro_id: int, dati: SottoAttivitaCreate, db: Session = Depends(get_db),
         current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    voce = SottoAttivita(testo=dati.testo, lavoro_id=lavoro_id)
    db.add(voce)
    db.commit()
    db.refresh(voce)
    return voce


@router.patch("/sotto-attivita/{sotto_id}", response_model=SottoAttivitaRead)
def modifica(sotto_id: int, dati: SottoAttivitaUpdate, db: Session = Depends(get_db),
             current: Utente = Depends(get_current_user)):
    voce = _sotto_mia(db, sotto_id, current)
    if voce is None:
        raise HTTPException(status_code=404, detail="Sotto-attivita' non trovata")

    # Spuntare o modificare richiede il permesso di aggiornare il lavoro.
    if not _puo_aggiornare(voce.lavoro, current):
        raise HTTPException(status_code=403, detail="Non puoi modificare questa voce")

    if dati.testo is not None:
        voce.testo = dati.testo
    if dati.completata is not None:
        voce.completata = dati.completata
    db.commit()
    db.refresh(voce)
    return voce


@router.delete("/sotto-attivita/{sotto_id}", status_code=204)
def elimina(sotto_id: int, db: Session = Depends(get_db),
            current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    voce = _sotto_mia(db, sotto_id, current)
    if voce is None:
        raise HTTPException(status_code=404, detail="Sotto-attivita' non trovata")
    db.delete(voce)
    db.commit()
