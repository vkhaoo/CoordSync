"""
Router dei Commenti: protetto, autore = utente loggato, isolato per org.

DUE ROUTER in un file solo. Scrivere e leggere passano dal genitore
(/lavori/{id}/commenti qui, /voci/{id}/commenti in macchine.py); correggere e
togliere passano da un indirizzo unico /commenti/{id} che riconosce da solo
sotto quale genitore sta il commento. E' la stessa forma di
DELETE /allegati/{id} e di PATCH /sotto-attivita/{id}.

CHI PUO' COSA, e non e' la stessa cosa:

- CORREGGERE: solo chi l'ha scritto. Riscrivere le parole di un altro non e'
  moderazione, e' metterglielo in bocca — nemmeno un admin lo puo' fare.
- TOGLIERE: chi l'ha scritto, oppure admin e caposquadra. Qui il permesso in
  piu' serve davvero: se qualcuno scrive una cosa fuori posto, qualcuno deve
  poterla togliere.

E una correzione si VEDE: si segna 'modificato_il' e l'app lo dichiara. In uno
strumento di coordinamento riscrivere in silenzio quello che si era detto —
magari dopo che un collega ci ha gia' risposto — cambia la storia senza che si
veda.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.commento import Commento
from app.models.lavoro import Lavoro
from app.models.progetto import Progetto
from app.models.utente import Utente, RuoloUtente
from app.schemas.commento import CommentoCreate, CommentoUpdate, CommentoRead
from app.dependencies import richiedi_azienda
from app.visibilita import lavoro_visibile, macchina_visibile
from app.avvisi import avvisa
from app.models.notifica import TipoAvviso

router = APIRouter(prefix="/lavori/{lavoro_id}/commenti", tags=["commenti"])

# Il secondo router: senza prefisso, per gli indirizzi che valgono per
# entrambi i mondi.
singolo = APIRouter(prefix="/commenti", tags=["commenti"])


def _commento_o_404(db: Session, current: Utente, commento_id: int) -> Commento:
    """Il commento, ma solo se posso vedere il posto in cui sta.

    Si passa dalla visibilita' del GENITORE e non si interroga la tabella dei
    commenti da sola: cosi' la regola su chi vede cosa resta scritta in un
    posto solo, e un commento non diventa la porta di servizio per sbirciare
    un reparto che non e' il mio.
    """
    commento = db.query(Commento).filter(Commento.id == commento_id).first()
    if commento is None:
        raise HTTPException(status_code=404, detail="Commento non trovato")

    if commento.lavoro_id is not None:
        visibile = lavoro_visibile(db, current, commento.lavoro_id) is not None
    elif commento.voce is not None:
        visibile = macchina_visibile(db, current, commento.voce.macchina_id) is not None
    else:
        visibile = False

    if not visibile:
        raise HTTPException(status_code=404, detail="Commento non trovato")
    return commento


@singolo.patch("/{commento_id}", response_model=CommentoRead)
def correggi(commento_id: int, dati: CommentoUpdate, db: Session = Depends(get_db),
             current: Utente = Depends(richiedi_azienda)):
    commento = _commento_o_404(db, current, commento_id)
    if commento.autore_id != current.id:
        raise HTTPException(status_code=403,
                            detail="Puoi correggere solo i commenti che hai scritto")

    commento.testo = dati.testo
    commento.modificato_il = datetime.now(timezone.utc)
    db.commit()
    db.refresh(commento)
    return commento


@singolo.delete("/{commento_id}", status_code=204)
def togli(commento_id: int, db: Session = Depends(get_db),
          current: Utente = Depends(richiedi_azienda)):
    commento = _commento_o_404(db, current, commento_id)
    gestisce = current.ruolo_attivo in (RuoloUtente.admin, RuoloUtente.caposquadra)
    if commento.autore_id != current.id and not gestisce:
        raise HTTPException(status_code=403,
                            detail="Puoi togliere solo i commenti che hai scritto")
    db.delete(commento)
    db.commit()


@router.post("", response_model=CommentoRead, status_code=201)
def aggiungi_commento(lavoro_id: int, dati: CommentoCreate,
                      db: Session = Depends(get_db),
                      current: Utente = Depends(richiedi_azienda)):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    # L'operatore puo' commentare SOLO i lavori a lui assegnati.
    if current.ruolo_attivo == RuoloUtente.operatore:
        assegnato = any(u.id == current.id for u in lavoro.assegnatari)
        if not assegnato:
            raise HTTPException(status_code=403, detail="Puoi commentare solo i lavori a te assegnati")

    # L'autore e' chi e' loggato: non si puo' commentare "a nome di" un altro.
    commento = Commento(testo=dati.testo, lavoro_id=lavoro_id, autore_id=current.id)
    db.add(commento)

    # Avviso chi sta su quel lavoro (non me stesso: ci pensa avvisa()).
    anteprima = dati.testo if len(dati.testo) <= 60 else dati.testo[:57] + "..."
    avvisa(db, lavoro.assegnatari, TipoAvviso.commento,
           f"{current.nome} ha commentato \"{lavoro.titolo}\": {anteprima}",
           mittente=current, lavoro_id=lavoro.id)

    db.commit()
    db.refresh(commento)
    return commento


@router.get("", response_model=list[CommentoRead])
def elenca_commenti(lavoro_id: int, db: Session = Depends(get_db),
                    current: Utente = Depends(richiedi_azienda)):
    if lavoro_visibile(db, current, lavoro_id) is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    return (
        db.query(Commento)
        .filter(Commento.lavoro_id == lavoro_id)
        .order_by(Commento.creato_il)
        .all()
    )
