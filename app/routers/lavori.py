"""Router dei Lavori: protetto, isolato per organizzazione, con permessi per ruolo."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lavoro import Lavoro, StatoLavoro
from app.models.progetto import Progetto
from app.models.utente import Utente, RuoloUtente
from app.schemas.lavoro import LavoroCreate, LavoroRead, LavoroUpdateStato, LavoroUpdate
from app.dependencies import get_current_user, richiedi_ruolo
from app.visibilita import (lavori_visibili, lavoro_visibile, progetto_visibile,
                            macchina_visibile)
from app.ricerca import condizione_testo
from app.models.commento import Commento
from app.models.sotto_attivita import SottoAttivita
from sqlalchemy import or_
from app.models.allegato import Allegato
from app.schemas.allegato import AllegatoCreate, AllegatoRead

router = APIRouter(prefix="/lavori", tags=["lavori"])


def _macchina_collegabile(db, current, forniti: dict) -> None:
    """La macchina che si collega dev'essere una che posso vedere."""
    if "macchina_id" not in forniti or forniti["macchina_id"] is None:
        return
    if macchina_visibile(db, current, forniti["macchina_id"]) is None:
        raise HTTPException(status_code=404, detail="Macchina non trovata")


# Le funzioni _progetto_mio/_lavoro_mio che stavano qui sono state sostituite da
# quelle di visibilita.py: la regola (azienda + reparto) vive in un posto solo.


@router.post("", response_model=LavoroRead, status_code=201)
def crea_lavoro(dati: LavoroCreate, db: Session = Depends(get_db),
                current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    if progetto_visibile(db, current, dati.progetto_id) is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato")

    _macchina_collegabile(db, current, {"macchina_id": dati.macchina_id})

    lavoro = Lavoro(
        titolo=dati.titolo,
        descrizione=dati.descrizione,
        priorita=dati.priorita,
        progetto_id=dati.progetto_id,
        data_scadenza=dati.data_scadenza,
        macchina_id=dati.macchina_id,
    )
    db.add(lavoro)
    db.commit()
    db.refresh(lavoro)
    return lavoro


@router.get("", response_model=list[LavoroRead])
def elenca_lavori(progetto_id: int | None = None, stato: StatoLavoro | None = None,
                  q: str | None = None,
                  db: Session = Depends(get_db),
                  current: Utente = Depends(get_current_user)):
    """I lavori che posso vedere.

    'q' cerca nel titolo, nella descrizione, nei COMMENTI e nelle voci di
    CHECKLIST: spesso quello che si ricorda non e' il titolo del lavoro ma una
    frase scritta in un commento ("dove avevo scritto di quella valvola?").
    """
    query = lavori_visibili(db, current)
    if progetto_id is not None:
        query = query.filter(Lavoro.progetto_id == progetto_id)
    if stato is not None:
        query = query.filter(Lavoro.stato == stato)

    cerca = condizione_testo([Lavoro.titolo, Lavoro.descrizione], q)
    if cerca is not None:
        # Sottoquery invece di join: una join farebbe tornare lo stesso lavoro
        # una volta per ogni commento che corrisponde.
        nei_commenti = (
            db.query(Commento.lavoro_id)
            .filter(condizione_testo([Commento.testo], q)).scalar_subquery()
        )
        nella_checklist = (
            db.query(SottoAttivita.lavoro_id)
            .filter(condizione_testo([SottoAttivita.testo], q)).scalar_subquery()
        )
        query = query.filter(or_(cerca,
                                 Lavoro.id.in_(nei_commenti),
                                 Lavoro.id.in_(nella_checklist)))
    return query.all()


@router.patch("/{lavoro_id}/stato", response_model=LavoroRead)
def cambia_stato(lavoro_id: int, dati: LavoroUpdateStato,
                 db: Session = Depends(get_db),
                 current: Utente = Depends(get_current_user)):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    # Permesso: admin e caposquadra su qualsiasi lavoro; l'operatore SOLO
    # se e' tra gli assegnatari di quel lavoro ("i lavori suoi").
    if current.ruolo_attivo == RuoloUtente.operatore:
        assegnato = any(u.id == current.id for u in lavoro.assegnatari)
        if not assegnato:
            raise HTTPException(status_code=403, detail="Puoi aggiornare solo i lavori a te assegnati")

    from datetime import datetime, timezone
    nuovo = dati.stato
    # Se passa a "fatto" (e non lo era gia'): registro quando e chi.
    if nuovo == StatoLavoro.fatto and lavoro.stato != StatoLavoro.fatto:
        lavoro.completato_il = datetime.now(timezone.utc)
        lavoro.completato_da_id = current.id
    # Se esce da "fatto": azzero i dati di completamento (non e' piu' completo).
    elif nuovo != StatoLavoro.fatto and lavoro.stato == StatoLavoro.fatto:
        lavoro.completato_il = None
        lavoro.completato_da_id = None

    lavoro.stato = nuovo
    db.commit()
    db.refresh(lavoro)
    return lavoro


@router.patch("/{lavoro_id}", response_model=LavoroRead)
def modifica_lavoro(lavoro_id: int, dati: LavoroUpdate,
                    db: Session = Depends(get_db),
                    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    dati_forniti = dati.model_dump(exclude_unset=True)

    # Se si vuole spostare il lavoro in un altro progetto, quel progetto
    # dev'essere della MIA organizzazione (non si "ruba" un lavoro altrui).
    if "progetto_id" in dati_forniti:
        if progetto_visibile(db, current, dati_forniti["progetto_id"]) is None:
            raise HTTPException(status_code=404, detail="Progetto di destinazione non trovato")
    _macchina_collegabile(db, current, dati_forniti)

    for campo, valore in dati_forniti.items():
        setattr(lavoro, campo, valore)
    db.commit()
    db.refresh(lavoro)
    return lavoro


@router.delete("/{lavoro_id}", status_code=204)
def elimina_lavoro(lavoro_id: int, db: Session = Depends(get_db),
                   current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    db.delete(lavoro)   # le sotto-attivita' e i commenti spariscono in cascata
    db.commit()


@router.post("/{lavoro_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_lavoro(lavoro_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                    current: Utente = Depends(get_current_user)):
    """Un link appeso al lavoro (foto dal campo, schema, documentazione)."""
    if lavoro_visibile(db, current, lavoro_id) is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    allegato = Allegato(url=dati.url, titolo=dati.titolo,
                        lavoro_id=lavoro_id, autore_id=current.id)
    db.add(allegato)
    db.commit()
    db.refresh(allegato)
    return allegato
