"""
Router dell'Agenda: gli impegni con data e ora, piu' le scadenze dei lavori.

L'agenda risponde a una domanda diversa da quella della bacheca lavori: non
"cosa c'e' da fare" ma "cosa ho in programma". Per questo gli impegni hanno
l'ora e appartengono a una persona.

Un impegno con piu' partecipanti e' una riunione: UNA cosa sola che compare
nell'agenda di tutti quelli che ci sono dentro. Spostandola, si sposta per
tutti; nessuno si ritrova una copia scollegata dalle altre.

Chi vede cosa:
- "miei": gli impegni in cui compaio fra i partecipanti;
- "reparto": anche quelli dei colleghi con cui divido almeno un reparto;
- "azienda": tutti quelli dell'organizzazione (per chi coordina).
Le scadenze mostrate sono sempre e solo quelle dei lavori che gia' posso
vedere: l'agenda non e' una scorciatoia per aggirare i reparti.
"""
from datetime import datetime, date, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.impegno import Impegno, partecipante_impegno
from app.models.lavoro import Lavoro, StatoLavoro
from app.models.progetto import Progetto
from app.models.reparto import membro_reparto
from app.models.utente import Utente, RuoloUtente
from app.schemas.impegno import (
    ImpegnoCreate, ImpegnoUpdate, ImpegnoRead, ScadenzaRead, AgendaRead,
)
from app.dependencies import get_current_user
from app.visibilita import lavori_visibili, lavoro_visibile, macchina_visibile
from app.avvisi import avvisa
from app.models.notifica import TipoAvviso

router = APIRouter(prefix="/agenda", tags=["agenda"])


def _coordina(current: Utente) -> bool:
    return current.ruolo in (RuoloUtente.admin, RuoloUtente.caposquadra)


def _con_partecipante(db: Session, utente_ids):
    """Condizione "fra i partecipanti c'e' almeno uno di questi".

    Passo dalla tabella-ponte invece di fare una join: con i partecipanti
    multipli una join restituirebbe la stessa riunione una volta per ogni
    partecipante che corrisponde.
    """
    return Impegno.id.in_(
        db.query(partecipante_impegno.c.impegno_id)
        .filter(partecipante_impegno.c.utente_id.in_(utente_ids))
        .scalar_subquery()
    )


def _impegni_visibili(db: Session, current: Utente, ambito: str):
    """Query degli impegni secondo l'ambito richiesto."""
    # La join sull'organizzatore serve solo a restare dentro la mia azienda:
    # e' un legame a uno, quindi non moltiplica le righe.
    query = db.query(Impegno).join(Utente, Impegno.organizzatore_id == Utente.id).filter(
        Utente.organizzazione_id == current.organizzazione_id)

    if ambito == "miei":
        return query.filter(_con_partecipante(db, [current.id]))

    if ambito == "azienda":
        return query

    # "reparto": i colleghi con cui divido almeno un reparto, piu' me stesso.
    ids_reparti = [r.id for r in current.reparti]
    if not ids_reparti:
        return query.filter(_con_partecipante(db, [current.id]))
    colleghi = (
        db.query(membro_reparto.c.utente_id)
        .filter(membro_reparto.c.reparto_id.in_(ids_reparti))
        .scalar_subquery()
    )
    from sqlalchemy import or_
    return query.filter(or_(_con_partecipante(db, [current.id]),
                            Impegno.id.in_(
                                db.query(partecipante_impegno.c.impegno_id)
                                .filter(partecipante_impegno.c.utente_id.in_(colleghi))
                                .scalar_subquery())))


def _impegno_mio_o_404(db, current, impegno_id) -> Impegno:
    impegno = (
        db.query(Impegno).join(Utente, Impegno.organizzatore_id == Utente.id)
        .filter(Impegno.id == impegno_id,
                Utente.organizzazione_id == current.organizzazione_id)
        .first()
    )
    if impegno is None:
        raise HTTPException(status_code=404, detail="Impegno non trovato")
    # Un'agenda e' personale: la tocca chi ha organizzato l'impegno, o chi
    # coordina. Un invitato non deve poter spostare la riunione agli altri.
    if impegno.organizzatore_id != current.id and not _coordina(current):
        raise HTTPException(status_code=403, detail="Puoi modificare solo gli impegni che hai creato")
    return impegno


def _risolvi_partecipanti(db, current: Utente, ids: list[int]) -> list[Utente]:
    """Chi partecipa. La lista si prende alla lettera: chi la manda decide se
    metterci dentro anche se stesso (una riunione di solito si', un incarico
    dato a un collega no).

    Invitare qualcun altro e' un atto di coordinamento: lo possono fare admin e
    caposquadra. E devono essere tutti colleghi della mia azienda; se anche uno
    solo non lo e', rifiuto tutto invece di creare mezza riunione.
    """
    if not ids:
        raise HTTPException(status_code=422, detail="Serve almeno un partecipante")

    voluti = set(ids)
    altri = voluti - {current.id}
    if altri and not _coordina(current):
        raise HTTPException(status_code=403,
                            detail="Non puoi mettere impegni nell'agenda di un collega")

    persone = (
        db.query(Utente)
        .filter(Utente.id.in_(voluti),
                Utente.organizzazione_id == current.organizzazione_id)
        .all()
    )
    if len(persone) != len(voluti):
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return persone


def _avvisa_partecipanti(db, current: Utente, impegno: Impegno, persone) -> None:
    """Fa sapere alle persone che si sono ritrovate qualcosa in agenda."""
    quando = impegno.inizio.strftime("%d/%m alle %H:%M")
    avvisa(db, persone, TipoAvviso.impegno,
           f"{current.nome} ti ha messo in agenda \"{impegno.titolo}\" il {quando}",
           mittente=current, impegno_id=impegno.id)


def _controlla_collegamenti(db, current, forniti: dict) -> None:
    """Lavoro e macchina collegati devono essere cose che posso vedere."""
    if forniti.get("lavoro_id") is not None:
        if lavoro_visibile(db, current, forniti["lavoro_id"]) is None:
            raise HTTPException(status_code=404, detail="Lavoro non trovato")
    if forniti.get("macchina_id") is not None:
        if macchina_visibile(db, current, forniti["macchina_id"]) is None:
            raise HTTPException(status_code=404, detail="Macchina non trovata")


@router.post("", response_model=ImpegnoRead, status_code=201)
def crea_impegno(dati: ImpegnoCreate, db: Session = Depends(get_db),
                 current: Utente = Depends(get_current_user)):
    if dati.fine is not None and dati.fine < dati.inizio:
        raise HTTPException(status_code=422, detail="La fine non puo' venire prima dell'inizio")

    # Senza indicazioni, l'impegno e' solo mio.
    partecipanti = _risolvi_partecipanti(db, current, dati.partecipanti_ids or [current.id])
    _controlla_collegamenti(db, current, dati.model_dump())

    impegno = Impegno(
        titolo=dati.titolo, note=dati.note, luogo=dati.luogo,
        inizio=dati.inizio, fine=dati.fine,
        promemoria_minuti=dati.promemoria_minuti,
        organizzatore_id=current.id,
        lavoro_id=dati.lavoro_id, macchina_id=dati.macchina_id,
    )
    impegno.partecipanti = partecipanti
    db.add(impegno)
    db.flush()   # serve l'id per collegarci gli avvisi

    _avvisa_partecipanti(db, current, impegno, partecipanti)

    db.commit()
    db.refresh(impegno)
    return impegno


@router.get("", response_model=AgendaRead)
def leggi_agenda(dal: date, al: date,
                 ambito: str = Query("miei", pattern="^(miei|reparto|azienda)$"),
                 db: Session = Depends(get_db),
                 current: Utente = Depends(get_current_user)):
    """Impegni e scadenze di un intervallo di giorni, in una chiamata sola."""
    if al < dal:
        raise HTTPException(status_code=422, detail="Intervallo di date non valido")

    inizio_finestra = datetime.combine(dal, time.min)
    fine_finestra = datetime.combine(al, time.max)

    impegni = (
        _impegni_visibili(db, current, ambito)
        .filter(Impegno.inizio >= inizio_finestra, Impegno.inizio <= fine_finestra)
        .order_by(Impegno.inizio)
        .all()
    )

    # Le scadenze: solo lavori che gia' vedo, non ancora conclusi.
    query_scadenze = (
        lavori_visibili(db, current)
        .filter(Lavoro.data_scadenza.isnot(None),
                Lavoro.data_scadenza >= dal, Lavoro.data_scadenza <= al,
                Lavoro.stato != StatoLavoro.fatto)
    )
    if ambito == "miei":
        query_scadenze = query_scadenze.filter(
            Lavoro.assegnatari.any(Utente.id == current.id))

    scadenze = [
        ScadenzaRead(
            lavoro_id=l.id, titolo=l.titolo, data_scadenza=l.data_scadenza,
            stato=l.stato.value, progetto=l.progetto.nome,
            mia=any(u.id == current.id for u in l.assegnatari),
        )
        for l in query_scadenze.order_by(Lavoro.data_scadenza).all()
    ]

    return AgendaRead(impegni=impegni, scadenze=scadenze)


@router.get("/prossimi", response_model=list[ImpegnoRead])
def prossimi_impegni(giorni: int = Query(7, ge=1, le=60),
                     db: Session = Depends(get_db),
                     current: Utente = Depends(get_current_user)):
    """I miei impegni in arrivo. Serve a mostrarli all'apertura dell'app:
    e' il promemoria che funziona senza dipendere da un servizio schedulato."""
    from datetime import timedelta
    adesso = datetime.now()
    return (
        db.query(Impegno)
        .filter(_con_partecipante(db, [current.id]),
                Impegno.inizio >= adesso,
                Impegno.inizio <= adesso + timedelta(days=giorni))
        .order_by(Impegno.inizio)
        .all()
    )


@router.patch("/{impegno_id}", response_model=ImpegnoRead)
def modifica_impegno(impegno_id: int, dati: ImpegnoUpdate, db: Session = Depends(get_db),
                     current: Utente = Depends(get_current_user)):
    impegno = _impegno_mio_o_404(db, current, impegno_id)
    forniti = dati.model_dump(exclude_unset=True)
    partecipanti_ids = forniti.pop("partecipanti_ids", None)
    _controlla_collegamenti(db, current, forniti)

    for campo, valore in forniti.items():
        setattr(impegno, campo, valore)
    if partecipanti_ids is not None:
        prima = {p.id for p in impegno.partecipanti}
        impegno.partecipanti = _risolvi_partecipanti(db, current, partecipanti_ids)
        # Avviso solo chi si e' AGGIUNTO ora: chi c'era gia' e' gia' stato avvisato.
        nuovi = [p for p in impegno.partecipanti if p.id not in prima]
        _avvisa_partecipanti(db, current, impegno, nuovi)
    if impegno.fine is not None and impegno.fine < impegno.inizio:
        raise HTTPException(status_code=422, detail="La fine non puo' venire prima dell'inizio")

    # Se l'orario e' cambiato, il promemoria torna da mandare.
    if "inizio" in forniti or "promemoria_minuti" in forniti:
        impegno.promemoria_inviato_il = None

    db.commit()
    db.refresh(impegno)
    return impegno


@router.delete("/{impegno_id}", status_code=204)
def elimina_impegno(impegno_id: int, db: Session = Depends(get_db),
                    current: Utente = Depends(get_current_user)):
    impegno = _impegno_mio_o_404(db, current, impegno_id)
    db.delete(impegno)
    db.commit()
