"""
Router degli avvisi in-app: quello che alimenta la campanella.

Ognuno vede SOLO i propri: non c'e' modo di leggere gli avvisi di un collega,
nemmeno essendo admin. Un avviso e' una cosa personale.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notifica import Notifica, TipoAvviso
from app.models.utente import Utente
from app.dependencies import get_current_user

router = APIRouter(prefix="/notifiche", tags=["notifiche"])


class NotificaRead(BaseModel):
    id: int
    tipo: TipoAvviso
    testo: str
    letta: bool
    creato_il: datetime
    lavoro_id: int | None = None
    impegno_id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class ElencoAvvisi(BaseModel):
    """Elenco e conteggio insieme: alla campanella servono entrambi, e una
    chiamata sola e' meglio di due."""
    non_lette: int
    notifiche: list[NotificaRead] = []


def _mie(db: Session, current: Utente):
    return db.query(Notifica).filter(Notifica.utente_id == current.id)


def _componi(db: Session, current: Utente, solo_non_lette: bool = False,
             limite: int = 30) -> ElencoAvvisi:
    """La risposta della campanella. Funzione normale e non endpoint, cosi'
    puo' richiamarla anche chi segna tutto come letto: chiamare direttamente
    una funzione-endpoint le passerebbe gli oggetti Query di FastAPI invece
    dei valori."""
    non_lette = _mie(db, current).filter(Notifica.letta.is_(False)).count()

    query = _mie(db, current)
    if solo_non_lette:
        query = query.filter(Notifica.letta.is_(False))
    elenco = query.order_by(Notifica.creato_il.desc(), Notifica.id.desc()).limit(limite).all()

    return ElencoAvvisi(non_lette=non_lette, notifiche=elenco)


@router.get("", response_model=ElencoAvvisi)
def elenca(solo_non_lette: bool = False, limite: int = Query(30, ge=1, le=100),
           db: Session = Depends(get_db), current: Utente = Depends(get_current_user)):
    """I miei avvisi, dal piu' recente. Il conteggio dei non letti e' sempre
    quello TOTALE, anche quando la lista e' tagliata dal limite."""
    return _componi(db, current, solo_non_lette, limite)


@router.patch("/{notifica_id}", response_model=NotificaRead)
def segna_letta(notifica_id: int, db: Session = Depends(get_db),
                current: Utente = Depends(get_current_user)):
    avviso = _mie(db, current).filter(Notifica.id == notifica_id).first()
    if avviso is None:
        raise HTTPException(status_code=404, detail="Avviso non trovato")
    avviso.letta = True
    db.commit()
    db.refresh(avviso)
    return avviso


@router.post("/segna-tutte-lette", response_model=ElencoAvvisi)
def segna_tutte_lette(db: Session = Depends(get_db),
                      current: Utente = Depends(get_current_user)):
    """Azzera la campanella in un colpo solo."""
    _mie(db, current).filter(Notifica.letta.is_(False)).update(
        {Notifica.letta: True}, synchronize_session=False)
    db.commit()
    return _componi(db, current)


@router.delete("/{notifica_id}", status_code=204)
def elimina(notifica_id: int, db: Session = Depends(get_db),
            current: Utente = Depends(get_current_user)):
    avviso = _mie(db, current).filter(Notifica.id == notifica_id).first()
    if avviso is None:
        raise HTTPException(status_code=404, detail="Avviso non trovato")
    db.delete(avviso)
    db.commit()
