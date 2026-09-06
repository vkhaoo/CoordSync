"""
Router delle SottoAttivita (le checklist).

Una voce di checklist puo' stare sotto un LAVORO di progetto o sotto una VOCE
del taccuino di una macchina. Creare e leggere si fa dal router del genitore
(/lavori/... qui sotto, /voci/... in macchine.py); SPUNTARE e TOGLIERE passano
invece da qui, con un indirizzo solo — /sotto-attivita/{id} — che riconosce da
solo sotto quale dei due genitori si trova. E' la stessa forma di
DELETE /allegati/{id}.

Permessi, che sono diversi nei due mondi perche' i due mondi lo sono:

- su un LAVORO creare ed eliminare e' di admin e caposquadra (definiscono il
  lavoro), e spuntare tocca a chi puo' aggiornarlo — cioe' anche l'operatore,
  ma solo se e' assegnato a quel lavoro;
- su una VOCE DI MACCHINA scrivere lo puo' fare chiunque veda la macchina,
  perche' li' l'assegnazione non esiste: chi trova il guasto e' chi passa di
  li'. Togliere una spunta e' invece una modifica alla voce, quindi vale la
  regola della voce: l'autore, oppure chi gestisce.

Tutto e' comunque isolato per organizzazione: si passa sempre dalla
visibilita' del genitore.
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
from app.dependencies import richiedi_azienda, richiedi_ruolo
from app.visibilita import lavoro_visibile, macchina_visibile

router = APIRouter(tags=["sotto-attivita"])


def _gestisce(current: Utente) -> bool:
    return current.ruolo_attivo in (RuoloUtente.admin, RuoloUtente.caposquadra)


def _sotto_mia(db, sotto_id, current):
    """La voce di checklist, ma solo se posso vedere il posto in cui sta.

    Si passa dalla visibilita' del GENITORE — il lavoro o la macchina — invece
    di interrogare direttamente la tabella: cosi' la regola su chi vede cosa
    resta scritta in un posto solo, e una checklist non diventa mai la porta
    di servizio per sbirciare un reparto che non e' il mio.
    """
    voce = db.query(SottoAttivita).filter(SottoAttivita.id == sotto_id).first()
    if voce is None:
        return None

    if voce.lavoro_id is not None:
        return voce if lavoro_visibile(db, current, voce.lavoro_id) else None

    if voce.voce_id is not None and voce.voce is not None:
        return voce if macchina_visibile(db, current, voce.voce.macchina_id) else None

    return None


def _puo_aggiornare(lavoro, current) -> bool:
    """Chi puo' spuntare le voci: admin/caposquadra, o l'operatore se assegnato."""
    if current.ruolo_attivo in (RuoloUtente.admin, RuoloUtente.caposquadra):
        return True
    return any(u.id == current.id for u in lavoro.assegnatari)


@router.get("/lavori/{lavoro_id}/sotto-attivita", response_model=list[SottoAttivitaRead])
def elenca(lavoro_id: int, db: Session = Depends(get_db),
           current: Utente = Depends(richiedi_azienda)):
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
             current: Utente = Depends(richiedi_azienda)):
    voce = _sotto_mia(db, sotto_id, current)
    if voce is None:
        raise HTTPException(status_code=404, detail="Sotto-attivita' non trovata")

    # Su un lavoro spuntare richiede il permesso di aggiornarlo. Su una voce di
    # macchina no: chi la vede la puo' spuntare, ed e' voluto — la spunta la
    # mette chi ha appena fatto la cosa, che sull'impianto e' chi passava di li'.
    if voce.lavoro_id is not None and not _puo_aggiornare(voce.lavoro, current):
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
            current: Utente = Depends(richiedi_azienda)):
    """Toglie un passo dalla lista.

    Il controllo del ruolo NON puo' stare nella dependency, come prima, perche'
    la risposta dipende da dove sta la voce: su un lavoro serve essere admin o
    caposquadra, su una voce di macchina basta esserne l'autore. Quindi si
    entra con richiedi_azienda e si decide qui dentro — ma la regola dei lavori
    resta esattamente quella di prima.
    """
    voce = _sotto_mia(db, sotto_id, current)
    if voce is None:
        raise HTTPException(status_code=404, detail="Sotto-attivita' non trovata")

    if voce.lavoro_id is not None:
        if not _gestisce(current):
            raise HTTPException(status_code=403, detail="Permesso negato per il tuo ruolo")
    else:
        # Sulla macchina: togliere un passo e' modificare la voce.
        if voce.voce.autore_id != current.id and not _gestisce(current):
            raise HTTPException(
                status_code=403,
                detail="Puoi togliere passi solo dalle voci che hai scritto")

    db.delete(voce)
    db.commit()
