"""Router dei Lavori: protetto, isolato per organizzazione, con permessi per ruolo."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lavoro import Lavoro, StatoLavoro
from app.models.progetto import Progetto
from app.models.utente import Utente, RuoloUtente
from app.schemas.lavoro import LavoroCreate, LavoroRead, LavoroUpdateStato, LavoroUpdate
from app.dependencies import richiedi_azienda, richiedi_ruolo
from app.visibilita import (lavori_visibili, lavoro_visibile, progetto_visibile,
                            macchina_visibile)
from app.ricerca import condizione_testo
from app.pagine import PAGINA, MASSIMO_PAGINA
from app.models.commento import Commento
from app.models.sotto_attivita import SottoAttivita
from sqlalchemy import or_, case
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


# L'ordine in cui le priorita' contano davvero. Non e' quello alfabetico
# ("alta" verrebbe prima di "urgente") ne' quello dell'enum: va scritto.
_PESO_PRIORITA = {"urgente": 0, "alta": 1, "normale": 2, "bassa": 3}


def _ordinamento(ordina: str | None):
    """Come mettere in fila i lavori.

    L'ordine lo decide il SERVER e non il browser, anche quello predefinito.
    Prima lo faceva il browser sulla lista gia' scaricata: funziona finche' i
    lavori arrivano tutti: il giorno in cui si scaricheranno a pagine,
    riordinare la pagina che si ha in mano darebbe un ordine sbagliato — la
    prima pagina non contiene necessariamente i primi.

    - predefinito: i lavori conclusi in fondo, poi per priorita' vera;
    - scadenza: prima le piu' vicine, e i lavori SENZA scadenza in fondo. Il
      caso ci vuole per forza: in SQL un NULL non e' ne' grande ne' piccolo, e
      i due database lo mettono in punti diversi (PostgreSQL in fondo quando si
      ordina crescendo, SQLite in cima). Senza, l'elenco cambierebbe fra
      sviluppo e produzione — il tipo di differenza che i test non vedono.
    """
    peso_priorita = case(_PESO_PRIORITA, value=Lavoro.priorita, else_=9)

    if ordina == "scadenza":
        senza = case((Lavoro.data_scadenza.is_(None), 1), else_=0)
        return [senza, Lavoro.data_scadenza.asc(), Lavoro.id.desc()]
    if ordina == "priorita":
        return [peso_priorita, Lavoro.id.desc()]
    if ordina == "recenti":
        return [Lavoro.creato_il.desc(), Lavoro.id.desc()]

    # Predefinito: quello che il browser faceva prima, spostato qui.
    conclusi = case((Lavoro.stato.in_(StatoLavoro.conclusi()), 1), else_=0)
    return [conclusi, peso_priorita, Lavoro.id.desc()]


@router.get("", response_model=list[LavoroRead])
def elenca_lavori(progetto_id: int | None = None, stato: StatoLavoro | None = None,
                  q: str | None = None,
                  assegnato_a: int | None = None,
                  solo_miei: bool = False,
                  ordina: str | None = Query(None, pattern="^(scadenza|priorita|recenti)$"),
                  limite: int = Query(PAGINA, ge=1, le=MASSIMO_PAGINA),
                  salta: int = Query(0, ge=0),
                  risposta: Response = None,
                  db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_azienda)):
    """I lavori che posso vedere.

    'q' cerca nel titolo, nella descrizione, nei COMMENTI e nelle voci di
    CHECKLIST: spesso quello che si ricorda non e' il titolo del lavoro ma una
    frase scritta in un commento ("dove avevo scritto di quella valvola?").

    I filtri si SOMMANO: chiedere insieme stato, persona e testo restringe,
    non allarga. E nessuno di loro allarga la visibilita': si parte sempre da
    lavori_visibili, poi si toglie.

    A PAGINE. Ne arrivano 50 alla volta; quanti ce ne sono in tutto si legge
    nell'intestazione X-Totale, cosi' il frontend sa se ha senso chiedere il
    resto. Serve a un progetto che accumula centinaia di lavori: scaricarli
    tutti per mostrarne venti diventa lento proprio quando l'app comincia a
    essere usata sul serio.
    """
    query = lavori_visibili(db, current)
    if progetto_id is not None:
        query = query.filter(Lavoro.progetto_id == progetto_id)
    if stato is not None:
        query = query.filter(Lavoro.stato == stato)

    # "Solo i miei" ha la precedenza su 'assegnato_a': se arrivano tutti e due
    # vince quello che parla di me, cosi' non si puo' costruire una richiesta
    # che dice "i miei, ma di un altro".
    chi = current.id if solo_miei else assegnato_a
    if chi is not None:
        # NON si controlla che 'chi' sia un collega visibile: non serve, e
        # farlo direbbe qualcosa in piu' di chi esiste. Chiedere i lavori di
        # un id qualunque restituisce al massimo i lavori che gia' vedo, cioe'
        # spesso nessuno.
        query = query.filter(Lavoro.assegnatari.any(Utente.id == chi))

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

    # Il TOTALE si conta prima di tagliare: serve al frontend per sapere se
    # c'e' altro da chiedere, e si conta senza ordinamento perche' ordinare
    # per contare e' lavoro buttato.
    if risposta is not None:
        risposta.headers["X-Totale"] = str(query.count())

    return (
        query.order_by(*_ordinamento(ordina))
        .offset(salta).limit(limite).all()
    )


@router.patch("/{lavoro_id}/stato", response_model=LavoroRead)
def cambia_stato(lavoro_id: int, dati: LavoroUpdateStato,
                 db: Session = Depends(get_db),
                 current: Utente = Depends(richiedi_azienda)):
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
                    current: Utente = Depends(richiedi_azienda)):
    """Un link appeso al lavoro (foto dal campo, schema, documentazione)."""
    if lavoro_visibile(db, current, lavoro_id) is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    allegato = Allegato(url=dati.url, titolo=dati.titolo,
                        lavoro_id=lavoro_id, autore_id=current.id)
    db.add(allegato)
    db.commit()
    db.refresh(allegato)
    return allegato
