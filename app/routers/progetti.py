"""Router dei Progetti: protetto da login, filtrato per organizzazione."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.schemas.progetto import ProgettoCreate, ProgettoRead, ProgettoUpdate
from app.models.utente import RuoloUtente
from app.dependencies import get_current_user, richiedi_ruolo
from app.visibilita import (progetti_visibili, progetto_visibile,
                            reparti_assegnabili, carica_reparti, macchina_visibile)
from app.models.allegato import Allegato
from app.schemas.allegato import AllegatoCreate, AllegatoRead

router = APIRouter(prefix="/progetti", tags=["progetti"])


def _macchina_collegabile(db, current, forniti: dict) -> None:
    """Se si vuole collegare una macchina, dev'essere una che posso vedere.
    None e' sempre ammesso: significa "nessuna macchina collegata"."""
    if "macchina_id" not in forniti or forniti["macchina_id"] is None:
        return
    if macchina_visibile(db, current, forniti["macchina_id"]) is None:
        raise HTTPException(status_code=404, detail="Macchina non trovata")


@router.post("", response_model=ProgettoRead, status_code=201)
def crea_progetto(
    dati: ProgettoCreate,
    db: Session = Depends(get_db),
    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)),
):
    # Non si puo' piazzare un progetto in reparti che non sono miei.
    if not reparti_assegnabili(db, current, dati.reparti_ids):
        raise HTTPException(status_code=404, detail="Reparto non trovato")
    _macchina_collegabile(db, current, {"macchina_id": dati.macchina_id})

    # L'organizzazione la prende dall'utente loggato, NON dal client.
    progetto = Progetto(
        nome=dati.nome,
        descrizione=dati.descrizione,
        link_documento=dati.link_documento,
        organizzazione_id=current.org_attiva_id,
        macchina_id=dati.macchina_id,
    )
    progetto.reparti = carica_reparti(db, current, dati.reparti_ids)
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
    reparti_ids = dati_forniti.pop("reparti_ids", None)
    if reparti_ids is not None and not reparti_assegnabili(db, current, reparti_ids):
        raise HTTPException(status_code=404, detail="Reparto non trovato")
    _macchina_collegabile(db, current, dati_forniti)

    # Aggiorno solo i campi effettivamente forniti (gli altri restano invariati).
    for campo, valore in dati_forniti.items():
        setattr(progetto, campo, valore)
    if reparti_ids is not None:
        progetto.reparti = carica_reparti(db, current, reparti_ids)
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


@router.post("/{progetto_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_progetto(progetto_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                      current: Utente = Depends(get_current_user)):
    """Un link appeso al progetto (foglio, cartella, documentazione)."""
    if progetto_visibile(db, current, progetto_id) is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    allegato = Allegato(url=dati.url, titolo=dati.titolo,
                        progetto_id=progetto_id, autore_id=current.id)
    db.add(allegato)
    db.commit()
    db.refresh(allegato)
    return allegato
