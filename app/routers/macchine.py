"""
Router della scheda macchina: macchine, sezioni, voci di taccuino e allegati.

Permessi, in due livelli:
- la STRUTTURA (creare/rinominare/eliminare macchine e sezioni) e' di admin e
  caposquadra: e' una decisione organizzativa;
- SCRIVERE nel taccuino lo puo' fare chiunque veda la macchina, operatori
  compresi. Se un operatore trova un guasto deve poterlo annotare subito: e'
  li' che sta il valore di uno storico.
Modificare o cancellare una voce e' invece riservato a chi l'ha scritta e a
admin/caposquadra.

Visibilita': la macchina segue il reparto, esattamente come i progetti.
La regola vive in visibilita.py, qui non si riscrive.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.allegato import Allegato
from app.models.macchina import Macchina, SezioneMacchina
from app.models.voce_macchina import VoceMacchina, TipoVoce
from app.models.utente import Utente, RuoloUtente
from app.schemas.macchina import (
    MacchinaCreate, MacchinaUpdate, MacchinaRead, MacchinaDettaglio,
    SezioneCreate, SezioneUpdate, SezioneRead,
    VoceCreate, VoceUpdate, VoceRead,
    AllegatoCreate, AllegatoRead,
)
from app.dependencies import get_current_user, richiedi_ruolo
from app.visibilita import macchine_visibili, macchina_visibile, reparto_assegnabile

router = APIRouter(tags=["macchine"])


def _gestisce(current: Utente) -> bool:
    return current.ruolo in (RuoloUtente.admin, RuoloUtente.caposquadra)


def _macchina_o_404(db, current, macchina_id) -> Macchina:
    macchina = macchina_visibile(db, current, macchina_id)
    if macchina is None:
        raise HTTPException(status_code=404, detail="Macchina non trovata")
    return macchina


def _sezione_o_404(db, current, sezione_id) -> SezioneMacchina:
    sezione = db.query(SezioneMacchina).filter(SezioneMacchina.id == sezione_id).first()
    # Passo comunque dalla macchina: cosi' la visibilita' vale anche qui.
    if sezione is None or macchina_visibile(db, current, sezione.macchina_id) is None:
        raise HTTPException(status_code=404, detail="Sezione non trovata")
    return sezione


def _voce_o_404(db, current, voce_id) -> VoceMacchina:
    voce = db.query(VoceMacchina).filter(VoceMacchina.id == voce_id).first()
    if voce is None or macchina_visibile(db, current, voce.macchina_id) is None:
        raise HTTPException(status_code=404, detail="Voce non trovata")
    return voce


# ---------- MACCHINE ----------

@router.post("/macchine", response_model=MacchinaRead, status_code=201)
def crea_macchina(dati: MacchinaCreate, db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    if not reparto_assegnabile(db, current, dati.reparto_id):
        raise HTTPException(status_code=404, detail="Reparto non trovato")

    macchina = Macchina(
        nome=dati.nome,
        descrizione=dati.descrizione,
        organizzazione_id=current.organizzazione_id,
        reparto_id=dati.reparto_id,
    )
    db.add(macchina)
    db.commit()
    db.refresh(macchina)
    return macchina


@router.get("/macchine", response_model=list[MacchinaRead])
def elenca_macchine(db: Session = Depends(get_db),
                    current: Utente = Depends(get_current_user)):
    return macchine_visibili(db, current).all()


@router.get("/macchine/{macchina_id}", response_model=MacchinaDettaglio)
def leggi_macchina(macchina_id: int, db: Session = Depends(get_db),
                   current: Utente = Depends(get_current_user)):
    """La scheda completa in una chiamata sola: sezioni, voci e allegati."""
    return _macchina_o_404(db, current, macchina_id)


@router.patch("/macchine/{macchina_id}", response_model=MacchinaRead)
def modifica_macchina(macchina_id: int, dati: MacchinaUpdate, db: Session = Depends(get_db),
                      current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    macchina = _macchina_o_404(db, current, macchina_id)
    forniti = dati.model_dump(exclude_unset=True)
    if "reparto_id" in forniti and not reparto_assegnabile(db, current, forniti["reparto_id"]):
        raise HTTPException(status_code=404, detail="Reparto non trovato")
    for campo, valore in forniti.items():
        setattr(macchina, campo, valore)
    db.commit()
    db.refresh(macchina)
    return macchina


@router.delete("/macchine/{macchina_id}", status_code=204)
def elimina_macchina(macchina_id: int, db: Session = Depends(get_db),
                     current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    macchina = _macchina_o_404(db, current, macchina_id)
    # Spariscono in cascata sezioni, voci e allegati. I progetti e i lavori
    # collegati NON spariscono: perdono solo il riferimento (SET NULL).
    db.delete(macchina)
    db.commit()


# ---------- SEZIONI ----------

@router.post("/macchine/{macchina_id}/sezioni", response_model=SezioneRead, status_code=201)
def crea_sezione(macchina_id: int, dati: SezioneCreate, db: Session = Depends(get_db),
                 current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    _macchina_o_404(db, current, macchina_id)
    sezione = SezioneMacchina(nome=dati.nome, ordine=dati.ordine, macchina_id=macchina_id)
    db.add(sezione)
    db.commit()
    db.refresh(sezione)
    return sezione


@router.patch("/sezioni/{sezione_id}", response_model=SezioneRead)
def modifica_sezione(sezione_id: int, dati: SezioneUpdate, db: Session = Depends(get_db),
                     current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    sezione = _sezione_o_404(db, current, sezione_id)
    for campo, valore in dati.model_dump(exclude_unset=True).items():
        setattr(sezione, campo, valore)
    db.commit()
    db.refresh(sezione)
    return sezione


@router.delete("/sezioni/{sezione_id}", status_code=204)
def elimina_sezione(sezione_id: int, db: Session = Depends(get_db),
                    current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    sezione = _sezione_o_404(db, current, sezione_id)
    # Le voci NON spariscono: perdono solo il collegamento a questa sezione
    # (la riga della tabella-ponte). Restano nella macchina.
    db.delete(sezione)
    db.commit()


# ---------- VOCI ----------

def _applica_sezioni(db, voce: VoceMacchina, sezioni_ids: list[int]) -> None:
    """Collega la voce alle sezioni indicate, ma solo a quelle della SUA macchina."""
    if not sezioni_ids:
        voce.sezioni = []
        return
    sezioni = (
        db.query(SezioneMacchina)
        .filter(SezioneMacchina.id.in_(sezioni_ids),
                SezioneMacchina.macchina_id == voce.macchina_id)
        .all()
    )
    if len(sezioni) != len(set(sezioni_ids)):
        raise HTTPException(status_code=404, detail="Sezione non trovata su questa macchina")
    voce.sezioni = sezioni


def _normalizza_stato(tipo: TipoVoce, stato):
    """Lo stato ha senso solo sui 'lavoro'. Sugli altri tipi lo azzero, per non
    lasciare in giro dati che non vogliono dire niente."""
    return stato if tipo == TipoVoce.lavoro else None


@router.post("/macchine/{macchina_id}/voci", response_model=VoceRead, status_code=201)
def crea_voce(macchina_id: int, dati: VoceCreate, db: Session = Depends(get_db),
              current: Utente = Depends(get_current_user)):
    """Scrivere nel taccuino lo puo' fare chiunque veda la macchina."""
    _macchina_o_404(db, current, macchina_id)

    voce = VoceMacchina(
        tipo=dati.tipo,
        stato=_normalizza_stato(dati.tipo, dati.stato),
        titolo=dati.titolo,
        testo=dati.testo,
        in_generale=dati.in_generale,
        macchina_id=macchina_id,
        autore_id=current.id,
    )
    db.add(voce)
    db.flush()   # serve un id prima di collegare le sezioni
    _applica_sezioni(db, voce, dati.sezioni_ids)
    db.commit()
    db.refresh(voce)
    return voce


@router.get("/macchine/{macchina_id}/voci", response_model=list[VoceRead])
def elenca_voci(macchina_id: int, tipo: TipoVoce | None = None,
                sezione_id: int | None = None,
                db: Session = Depends(get_db),
                current: Utente = Depends(get_current_user)):
    """Le voci della macchina. Senza filtri e' lo storico completo, in ordine
    di tempo: e' la vista "cosa e' successo su questo impianto"."""
    _macchina_o_404(db, current, macchina_id)

    query = db.query(VoceMacchina).filter(VoceMacchina.macchina_id == macchina_id)
    if tipo is not None:
        query = query.filter(VoceMacchina.tipo == tipo)
    if sezione_id is not None:
        query = query.filter(VoceMacchina.sezioni.any(SezioneMacchina.id == sezione_id))
    return query.order_by(VoceMacchina.creato_il.desc()).all()


@router.patch("/voci/{voce_id}", response_model=VoceRead)
def modifica_voce(voce_id: int, dati: VoceUpdate, db: Session = Depends(get_db),
                  current: Utente = Depends(get_current_user)):
    voce = _voce_o_404(db, current, voce_id)
    # La modifica una voce chi l'ha scritta, oppure chi gestisce.
    if voce.autore_id != current.id and not _gestisce(current):
        raise HTTPException(status_code=403, detail="Puoi modificare solo le voci che hai scritto")

    forniti = dati.model_dump(exclude_unset=True)
    sezioni_ids = forniti.pop("sezioni_ids", None)
    for campo, valore in forniti.items():
        setattr(voce, campo, valore)
    # Se cambia il tipo, lo stato va rivalutato (un'analisi non ha stato).
    voce.stato = _normalizza_stato(voce.tipo, voce.stato)
    if sezioni_ids is not None:
        _applica_sezioni(db, voce, sezioni_ids)

    db.commit()
    db.refresh(voce)
    return voce


@router.delete("/voci/{voce_id}", status_code=204)
def elimina_voce(voce_id: int, db: Session = Depends(get_db),
                 current: Utente = Depends(get_current_user)):
    voce = _voce_o_404(db, current, voce_id)
    if voce.autore_id != current.id and not _gestisce(current):
        raise HTTPException(status_code=403, detail="Puoi eliminare solo le voci che hai scritto")
    db.delete(voce)
    db.commit()


# ---------- ALLEGATI ----------
# Un endpoint per genitore: cosi' un allegato ha per costruzione una sola scheda.

def _crea_allegato(db, current, dati: AllegatoCreate, **genitore) -> Allegato:
    allegato = Allegato(url=dati.url, titolo=dati.titolo, autore_id=current.id, **genitore)
    db.add(allegato)
    db.commit()
    db.refresh(allegato)
    return allegato


@router.post("/macchine/{macchina_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_macchina(macchina_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                      current: Utente = Depends(get_current_user)):
    _macchina_o_404(db, current, macchina_id)
    return _crea_allegato(db, current, dati, macchina_id=macchina_id)


@router.post("/sezioni/{sezione_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_sezione(sezione_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                     current: Utente = Depends(get_current_user)):
    _sezione_o_404(db, current, sezione_id)
    return _crea_allegato(db, current, dati, sezione_id=sezione_id)


@router.post("/voci/{voce_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_voce(voce_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                  current: Utente = Depends(get_current_user)):
    _voce_o_404(db, current, voce_id)
    return _crea_allegato(db, current, dati, voce_id=voce_id)


@router.delete("/allegati/{allegato_id}", status_code=204)
def elimina_allegato(allegato_id: int, db: Session = Depends(get_db),
                     current: Utente = Depends(get_current_user)):
    allegato = db.query(Allegato).filter(Allegato.id == allegato_id).first()
    if allegato is None:
        raise HTTPException(status_code=404, detail="Allegato non trovato")

    # Devo poter vedere la scheda a cui e' appeso, altrimenti per me non esiste.
    if allegato.macchina_id is not None:
        _macchina_o_404(db, current, allegato.macchina_id)
    elif allegato.sezione_id is not None:
        _sezione_o_404(db, current, allegato.sezione_id)
    elif allegato.voce_id is not None:
        _voce_o_404(db, current, allegato.voce_id)
    else:
        from app.visibilita import progetto_visibile, lavoro_visibile
        visibile = (
            progetto_visibile(db, current, allegato.progetto_id) if allegato.progetto_id
            else lavoro_visibile(db, current, allegato.lavoro_id)
        )
        if visibile is None:
            raise HTTPException(status_code=404, detail="Allegato non trovato")

    if allegato.autore_id != current.id and not _gestisce(current):
        raise HTTPException(status_code=403, detail="Puoi eliminare solo gli allegati che hai messo")
    db.delete(allegato)
    db.commit()
