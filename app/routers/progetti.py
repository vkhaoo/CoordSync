"""Router dei Progetti: protetto da login, filtrato per organizzazione."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.models.lavoro import Lavoro
from app.models.sotto_attivita import SottoAttivita
from app.schemas.progetto import (ProgettoCreate, ProgettoRead, ProgettoUpdate,
                                  ProgettoDuplica)
from app.models.utente import RuoloUtente
from app.dependencies import richiedi_azienda, richiedi_ruolo
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


@router.post("/{progetto_id}/duplica", response_model=ProgettoRead, status_code=201)
def duplica_progetto(
    progetto_id: int,
    dati: ProgettoDuplica,
    db: Session = Depends(get_db),
    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)),
):
    """Rifa' un progetto uguale, vuoto, per una commessa che si ripete.

    SI COPIA LA STRUTTURA, NON LA STORIA. Un impianto uguale al precedente
    vuole gli stessi venti lavori con le stesse checklist, non il racconto di
    come e' andata la volta scorsa.

    Si copiano: descrizione, reparti, link al documento, macchina collegata,
    i lavori (titolo, descrizione, priorita', macchina) con le loro checklist
    e i link appesi — che sono materiale di riferimento, schemi e manuali che
    servono di nuovo.

    NON si copiano, e ognuno per una ragione sua:

    - gli STATI: tutto riparte da "da fare", se no il progetto nuovo
      nascerebbe gia' mezzo completato;
    - le SPUNTE della checklist, per lo stesso motivo;
    - le SCADENZE: le date della commessa vecchia non dicono niente su quella
      nuova, e lasciarle vorrebbe dire far nascere un progetto gia' in ritardo;
    - i COMMENTI: sono la conversazione di quella volta li';
    - gli ASSEGNATARI. Questa e' la scelta meno ovvia: spesso e' la stessa
      squadra. Ma copiarli farebbe partire subito venti avvisi (e venti email)
      per un lavoro che nessuno ha ancora deciso di dare a nessuno, e chi
      duplica lo fa proprio per ripianificare.
    """
    originale = progetto_visibile(db, current, progetto_id)
    if originale is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato")

    copia = Progetto(
        nome=dati.nome,
        descrizione=originale.descrizione,
        link_documento=originale.link_documento,
        organizzazione_id=current.org_attiva_id,
        macchina_id=originale.macchina_id,
    )
    # I reparti si copiano tali e quali: chi puo' vedere l'originale puo'
    # vedere anche la copia, ne' piu' ne' meno.
    copia.reparti = list(originale.reparti)
    db.add(copia)
    db.flush()   # serve l'id prima di appenderci i lavori

    for vecchio in originale.lavori:
        nuovo = Lavoro(
            titolo=vecchio.titolo,
            descrizione=vecchio.descrizione,
            priorita=vecchio.priorita,
            progetto_id=copia.id,
            macchina_id=vecchio.macchina_id,
        )
        db.add(nuovo)
        db.flush()
        for passo in vecchio.sotto_attivita:
            db.add(SottoAttivita(testo=passo.testo, completata=False,
                                 lavoro_id=nuovo.id))
        for link in vecchio.allegati:
            db.add(Allegato(url=link.url, titolo=link.titolo,
                            autore_id=current.id, lavoro_id=nuovo.id))

    for link in originale.allegati:
        db.add(Allegato(url=link.url, titolo=link.titolo,
                        autore_id=current.id, progetto_id=copia.id))

    db.commit()
    db.refresh(copia)
    return copia


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
    current: Utente = Depends(richiedi_azienda),
):
    # Azienda + reparto: la regola sta tutta in visibilita.py.
    return progetti_visibili(db, current).all()


@router.post("/{progetto_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_progetto(progetto_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                      current: Utente = Depends(richiedi_azienda)):
    """Un link appeso al progetto (foglio, cartella, documentazione)."""
    if progetto_visibile(db, current, progetto_id) is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    allegato = Allegato(url=dati.url, titolo=dati.titolo,
                        progetto_id=progetto_id, autore_id=current.id)
    db.add(allegato)
    db.commit()
    db.refresh(allegato)
    return allegato
