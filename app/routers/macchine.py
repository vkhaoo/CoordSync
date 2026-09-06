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
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.allegato import Allegato
from app.models.commento import Commento
from app.models.macchina import Macchina, SezioneMacchina
from app.models.sotto_attivita import SottoAttivita
from app.models.voce_macchina import VoceMacchina, TipoVoce
from app.models.utente import Utente, RuoloUtente
from app.schemas.macchina import (
    MacchinaCreate, MacchinaUpdate, MacchinaRead, MacchinaDettaglio,
    SezioneCreate, SezioneUpdate, SezioneRead, OrdineSezioni,
    VoceCreate, VoceUpdate, VoceRead,
    AllegatoCreate, AllegatoRead,
    CommentoCreate, CommentoRead,
    SottoAttivitaCreate, SottoAttivitaRead,
)
from app.dependencies import richiedi_azienda, richiedi_ruolo
from app.visibilita import (macchine_visibili, macchina_visibile,
                            reparti_assegnabili, carica_reparti)
from app.ricerca import condizione_testo
from app.avvisi import avvisa
from app.menzioni import trova_menzionati, colleghi_che_possono_vedere
from app.models.notifica import TipoAvviso

router = APIRouter(tags=["macchine"])


def _gestisce(current: Utente) -> bool:
    return current.ruolo_attivo in (RuoloUtente.admin, RuoloUtente.caposquadra)


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
    if not reparti_assegnabili(db, current, dati.reparti_ids):
        raise HTTPException(status_code=404, detail="Reparto non trovato")

    macchina = Macchina(
        nome=dati.nome,
        descrizione=dati.descrizione,
        organizzazione_id=current.org_attiva_id,
    )
    macchina.reparti = carica_reparti(db, current, dati.reparti_ids)
    db.add(macchina)
    db.commit()
    db.refresh(macchina)
    return macchina


@router.get("/macchine", response_model=list[MacchinaRead])
def elenca_macchine(db: Session = Depends(get_db),
                    current: Utente = Depends(richiedi_azienda)):
    return macchine_visibili(db, current).all()


@router.get("/macchine/{macchina_id}", response_model=MacchinaDettaglio)
def leggi_macchina(macchina_id: int, db: Session = Depends(get_db),
                   current: Utente = Depends(richiedi_azienda)):
    """La scheda completa in una chiamata sola: sezioni, voci e allegati."""
    return _macchina_o_404(db, current, macchina_id)


@router.patch("/macchine/{macchina_id}", response_model=MacchinaRead)
def modifica_macchina(macchina_id: int, dati: MacchinaUpdate, db: Session = Depends(get_db),
                      current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    macchina = _macchina_o_404(db, current, macchina_id)
    forniti = dati.model_dump(exclude_unset=True)
    reparti_ids = forniti.pop("reparti_ids", None)
    if reparti_ids is not None and not reparti_assegnabili(db, current, reparti_ids):
        raise HTTPException(status_code=404, detail="Reparto non trovato")
    for campo, valore in forniti.items():
        setattr(macchina, campo, valore)
    if reparti_ids is not None:
        macchina.reparti = carica_reparti(db, current, reparti_ids)
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
    ordine = dati.ordine
    if ordine is None:
        ultimo = (
            db.query(func.max(SezioneMacchina.ordine))
            .filter(SezioneMacchina.macchina_id == macchina_id)
            .scalar()
        )
        ordine = 0 if ultimo is None else ultimo + 1
    sezione = SezioneMacchina(nome=dati.nome, ordine=ordine, macchina_id=macchina_id)
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


@router.put("/macchine/{macchina_id}/sezioni/ordine", response_model=list[SezioneRead])
def riordina_sezioni(macchina_id: int, dati: OrdineSezioni, db: Session = Depends(get_db),
                     current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    """Rimette le sezioni nell'ordine indicato.

    L'ordine di una macchina non e' alfabetico: e' quello in cui i pezzi stanno
    sull'impianto, o quello in cui si guardano quando si cerca un guasto. Solo
    chi la usa sa qual e'.

    Si riceve la lista COMPLETA degli id. Deve corrispondere esattamente alle
    sezioni di questa macchina: se ne manca una o ne arriva una di un'altra
    macchina si rifiuta tutto, invece di salvare un ordine a meta'.
    """
    _macchina_o_404(db, current, macchina_id)

    sezioni = (
        db.query(SezioneMacchina)
        .filter(SezioneMacchina.macchina_id == macchina_id)
        .all()
    )
    per_id = {s.id: s for s in sezioni}
    if len(dati.sezioni_ids) != len(set(dati.sezioni_ids)):
        raise HTTPException(status_code=400, detail="Ci sono sezioni ripetute nell'ordine")
    if set(dati.sezioni_ids) != set(per_id):
        raise HTTPException(
            status_code=400,
            detail="L'ordine deve contenere tutte e sole le sezioni di questa macchina",
        )

    for posto, sezione_id in enumerate(dati.sezioni_ids):
        per_id[sezione_id].ordine = posto
    db.commit()
    # Rileggo dal database: cosi' l'ordine che torna e' quello davvero salvato.
    return (
        db.query(SezioneMacchina)
        .filter(SezioneMacchina.macchina_id == macchina_id)
        .order_by(SezioneMacchina.ordine)
        .all()
    )


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


def _controlla_genitore(db: Session, macchina_id: int, genitore_id: int | None,
                        voce: VoceMacchina | None = None) -> None:
    """Verifica che una voce possa stare sotto l'argomento indicato.

    Le regole sono tre, e tutte servono a tenere la struttura leggibile:

    1) l'argomento dev'essere della STESSA macchina. Sparpagliare le voci di
       un impianto sotto quelle di un altro non vuol dire niente;
    2) UN SOLO LIVELLO: non si mette una voce sotto una che sta gia' sotto
       qualcos'altro. E' la forma di progetto/lavoro, non un albero in cui a
       forza di rientri non si ritrova piu' niente;
    3) chi ha gia' delle voci sotto di se' non puo' diventare figlia a sua
       volta, se no il livello diventerebbe due lo stesso.
    """
    if genitore_id is None:
        return

    if voce is not None and genitore_id == voce.id:
        raise HTTPException(status_code=400,
                            detail="Una voce non puo' stare sotto se stessa")

    genitore = (
        db.query(VoceMacchina)
        .filter(VoceMacchina.id == genitore_id,
                VoceMacchina.macchina_id == macchina_id)
        .first()
    )
    if genitore is None:
        raise HTTPException(status_code=400,
                            detail="L'argomento scelto non e' di questa macchina")
    if genitore.genitore_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Si puo' raggruppare su un livello solo: quell'argomento sta gia' sotto un altro",
        )
    if voce is not None and db.query(VoceMacchina).filter(
            VoceMacchina.genitore_id == voce.id).first() is not None:
        raise HTTPException(
            status_code=400,
            detail="Questa voce ha gia' altre voci sotto di se': staccale prima di spostarla",
        )


def _voci_col_testo_dentro(db: Session, q: str | None) -> list:
    """Condizioni "il testo cercato sta in un commento / in una spunta".

    Sottoquery e non join: una join farebbe tornare la stessa voce una volta
    per ogni commento che corrisponde. Vive qui e non in ricerca.py perche'
    parla di voci di macchina, non di ricerca in generale.
    """
    nei_commenti = (
        db.query(Commento.voce_id)
        .filter(Commento.voce_id.isnot(None),
                condizione_testo([Commento.testo], q)).scalar_subquery()
    )
    nella_checklist = (
        db.query(SottoAttivita.voce_id)
        .filter(SottoAttivita.voce_id.isnot(None),
                condizione_testo([SottoAttivita.testo], q)).scalar_subquery()
    )
    return [VoceMacchina.id.in_(nei_commenti), VoceMacchina.id.in_(nella_checklist)]


@router.post("/macchine/{macchina_id}/voci", response_model=VoceRead, status_code=201)
def crea_voce(macchina_id: int, dati: VoceCreate, db: Session = Depends(get_db),
              current: Utente = Depends(richiedi_azienda)):
    """Scrivere nel taccuino lo puo' fare chiunque veda la macchina."""
    _macchina_o_404(db, current, macchina_id)
    _controlla_genitore(db, macchina_id, dati.genitore_id)

    voce = VoceMacchina(
        tipo=dati.tipo,
        genitore_id=dati.genitore_id,
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
                sezione_id: int | None = None, q: str | None = None,
                db: Session = Depends(get_db),
                current: Utente = Depends(richiedi_azienda)):
    """Le voci della macchina. Senza filtri e' lo storico completo, in ordine
    di tempo: e' la vista "cosa e' successo su questo impianto".

    'q' cerca nel titolo, nel testo, nei COMMENTI e nella CHECKLIST: con anni
    di storico e' l'unico modo pratico per ritrovare quella volta che si era
    rotta la valvola — e spesso quello che si ricorda non e' il titolo della
    voce, ma una frase scritta rispondendo ("dove avevo scritto della
    guarnizione?"). E' la stessa regola che vale sui lavori di progetto."""
    _macchina_o_404(db, current, macchina_id)

    query = db.query(VoceMacchina).filter(VoceMacchina.macchina_id == macchina_id)
    cerca = condizione_testo([VoceMacchina.titolo, VoceMacchina.testo], q)
    if cerca is not None:
        query = query.filter(or_(cerca, *_voci_col_testo_dentro(db, q)))
    if tipo is not None:
        query = query.filter(VoceMacchina.tipo == tipo)
    if sezione_id is not None:
        query = query.filter(VoceMacchina.sezioni.any(SezioneMacchina.id == sezione_id))
    return query.order_by(VoceMacchina.creato_il.desc()).all()


@router.patch("/voci/{voce_id}", response_model=VoceRead)
def modifica_voce(voce_id: int, dati: VoceUpdate, db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_azienda)):
    voce = _voce_o_404(db, current, voce_id)
    # La modifica una voce chi l'ha scritta, oppure chi gestisce.
    if voce.autore_id != current.id and not _gestisce(current):
        raise HTTPException(status_code=403, detail="Puoi modificare solo le voci che hai scritto")

    forniti = dati.model_dump(exclude_unset=True)
    sezioni_ids = forniti.pop("sezioni_ids", None)
    # 'genitore_id' presente e a null = staccala dall'argomento; assente =
    # non si tocca. Per questo si guarda dentro 'forniti' e non il valore.
    if "genitore_id" in forniti:
        _controlla_genitore(db, voce.macchina_id, forniti["genitore_id"], voce)
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
                 current: Utente = Depends(richiedi_azienda)):
    voce = _voce_o_404(db, current, voce_id)
    if voce.autore_id != current.id and not _gestisce(current):
        raise HTTPException(status_code=403, detail="Puoi eliminare solo le voci che hai scritto")
    db.delete(voce)
    db.commit()


# ---------- COMMENTI E CHECKLIST SULLE VOCI ----------
#
# Una voce di taccuino non e' solo un'annotazione da rileggere: intorno a un
# guasto si discute e si tiene il conto dei passi da fare. Sono le stesse due
# cose che hanno i lavori di progetto, quindi si riusano quelle tabelle.
#
# I PERMESSI seguono la regola del taccuino, non quella dei lavori: SCRIVERE
# (commentare, aggiungere una spunta, spuntarla) lo puo' fare chiunque veda la
# macchina, operatori compresi. Sui lavori si pretende di essere assegnati, ma
# sulle macchine l'assegnazione non esiste proprio: chi trova il guasto e' chi
# passa di li', ed e' li' che sta il valore di uno storico.
#
# TOGLIERE una spunta dalla lista e' invece una modifica alla voce, quindi vale
# la stessa regola del modificare la voce: l'autore, oppure chi gestisce.


@router.get("/voci/{voce_id}/commenti", response_model=list[CommentoRead])
def elenca_commenti_voce(voce_id: int, db: Session = Depends(get_db),
                         current: Utente = Depends(richiedi_azienda)):
    voce = _voce_o_404(db, current, voce_id)
    return (
        db.query(Commento)
        .filter(Commento.voce_id == voce.id)
        .order_by(Commento.creato_il)
        .all()
    )


@router.post("/voci/{voce_id}/commenti", response_model=CommentoRead, status_code=201)
def commenta_voce(voce_id: int, dati: CommentoCreate, db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_azienda)):
    voce = _voce_o_404(db, current, voce_id)
    # L'autore e' chi e' collegato: non si commenta "a nome di" un altro.
    commento = Commento(testo=dati.testo, voce_id=voce.id, autore_id=current.id)
    db.add(commento)

    # Avviso chi ha scritto la voce: e' l'unica persona di cui si sa con
    # certezza che quella annotazione la segue. Non tutta l'azienda — una
    # macchina la vedono in tanti, e una campanella che suona per ogni
    # commento su ogni impianto smette di volere dire niente.
    anteprima = dati.testo if len(dati.testo) <= 60 else dati.testo[:57] + "..."
    avvisati = avvisa(db, [voce.autore], TipoAvviso.commento,
                      f"{current.nome} ha commentato \"{voce.titolo}\": {anteprima}",
                      mittente=current, voce_id=voce.id)

    # E chi e' stato NOMINATO, se non l'ho gia' avvisato come autore.
    gia_avvisati = {a.utente_id for a in avvisati}
    nominati = trova_menzionati(
        dati.testo,
        [u for u in colleghi_che_possono_vedere(db, current, macchina_id=voce.macchina_id)
         if u.id not in gia_avvisati],
    )
    avvisa(db, nominati, TipoAvviso.menzione,
           f"{current.nome} ti ha nominato su \"{voce.titolo}\": {anteprima}",
           mittente=current, voce_id=voce.id)

    db.commit()
    db.refresh(commento)
    return commento


@router.get("/voci/{voce_id}/sotto-attivita", response_model=list[SottoAttivitaRead])
def elenca_checklist_voce(voce_id: int, db: Session = Depends(get_db),
                          current: Utente = Depends(richiedi_azienda)):
    voce = _voce_o_404(db, current, voce_id)
    return voce.sotto_attivita


@router.post("/voci/{voce_id}/sotto-attivita", response_model=SottoAttivitaRead,
             status_code=201)
def aggiungi_checklist_voce(voce_id: int, dati: SottoAttivitaCreate,
                            db: Session = Depends(get_db),
                            current: Utente = Depends(richiedi_azienda)):
    voce = _voce_o_404(db, current, voce_id)
    passo = SottoAttivita(testo=dati.testo, voce_id=voce.id)
    db.add(passo)
    db.commit()
    db.refresh(passo)
    return passo


# Spuntare e togliere una voce di checklist passano dagli endpoint condivisi
# PATCH e DELETE /sotto-attivita/{id}, che sanno riconoscere sotto quale dei
# due genitori stanno (vedi routers/sotto_attivita.py). Stessa forma di
# DELETE /allegati/{id} qui sotto.


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
                      current: Utente = Depends(richiedi_azienda)):
    _macchina_o_404(db, current, macchina_id)
    return _crea_allegato(db, current, dati, macchina_id=macchina_id)


@router.post("/sezioni/{sezione_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_sezione(sezione_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                     current: Utente = Depends(richiedi_azienda)):
    _sezione_o_404(db, current, sezione_id)
    return _crea_allegato(db, current, dati, sezione_id=sezione_id)


@router.post("/voci/{voce_id}/allegati", response_model=AllegatoRead, status_code=201)
def allega_a_voce(voce_id: int, dati: AllegatoCreate, db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_azienda)):
    _voce_o_404(db, current, voce_id)
    return _crea_allegato(db, current, dati, voce_id=voce_id)


@router.delete("/allegati/{allegato_id}", status_code=204)
def elimina_allegato(allegato_id: int, db: Session = Depends(get_db),
                     current: Utente = Depends(richiedi_azienda)):
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
