"""
Router delle Assegnazioni: chi lavora su un lavoro (molti-a-molti).

Usa la tabella-ponte 'assegnazioni' predisposta all'inizio.
Regola di sicurezza: puoi assegnare SOLO colleghi della tua stessa azienda,
e solo su lavori della tua azienda.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.appartenenze import condizione_membro
from app.database import get_db
from app.models.lavoro import Lavoro
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.schemas.lavoro import LavoroRead
from app.models.utente import RuoloUtente
from app.dependencies import get_current_user, richiedi_ruolo
from app.visibilita import lavoro_visibile
from app.avvisi import avvisa
from app.models.notifica import TipoAvviso

router = APIRouter(prefix="/lavori/{lavoro_id}/assegnati", tags=["assegnazioni"])


def _avvisa_via_email(chi_assegna: Utente, destinatario: Utente, lavoro) -> None:
    """Manda l'email dell'assegnazione, senza far fallire l'assegnazione se
    l'invio non riesce.

    Il lavoro e' gia' stato salvato: se il servizio email e' giu' o l'indirizzo
    e' sbagliato, meglio un'email persa che un'assegnazione persa. L'avviso
    nella campanella c'e' comunque.
    """
    if not destinatario.email:
        return
    if destinatario.id == chi_assegna.id:
        return   # assegnarsi un lavoro da soli non merita un'email da se stessi
    try:
        from app.config import settings
        from app.email_templates import assegnazione_lavoro
        from app.notifiche import invia_email

        scadenza = lavoro.data_scadenza.strftime("%d/%m/%Y") if lavoro.data_scadenza else None
        oggetto, testo, html = assegnazione_lavoro(
            destinatario.nome, chi_assegna.nome, lavoro.titolo,
            lavoro.progetto.nome if lavoro.progetto else "-",
            scadenza, settings.frontend_url)
        invia_email(destinatario=destinatario.email, oggetto=oggetto,
                    corpo=testo, corpo_html=html)
    except Exception:
        import logging
        logging.getLogger("coordsync").exception(
            "Assegnazione salvata ma email non inviata a %s", destinatario.email)


class AssegnaRichiesta(BaseModel):
    utente_id: int


@router.post("", response_model=LavoroRead, status_code=201)
def assegna(lavoro_id: int, dati: AssegnaRichiesta, db: Session = Depends(get_db),
            current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    # L'utente da assegnare deve essere della MIA azienda.
    utente = (
        db.query(Utente)
        .filter(Utente.id == dati.utente_id,
                condizione_membro(current.org_attiva_id))
        .first()
    )
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Evito doppioni: se e' gia' assegnato, non lo aggiungo di nuovo.
    if utente not in lavoro.assegnatari:
        lavoro.assegnatari.append(utente)   # <- aggiunge una riga nella tabella-ponte
        # Glielo faccio sapere: e' il momento in cui un lavoro diventa "suo".
        avvisa(db, [utente], TipoAvviso.assegnazione,
               f"{current.nome} ti ha assegnato il lavoro \"{lavoro.titolo}\"",
               mittente=current, lavoro_id=lavoro.id)
        db.commit()
        db.refresh(lavoro)
        # ...e, solo per questo evento, anche via email: e' l'unica cosa che
        # non ci si puo' permettere di non vedere se non si apre l'app.
        _avvisa_via_email(current, utente, lavoro)
    return lavoro


@router.delete("/{utente_id}", response_model=LavoroRead)
def rimuovi(lavoro_id: int, utente_id: int, db: Session = Depends(get_db),
            current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra))):
    lavoro = lavoro_visibile(db, current, lavoro_id)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    utente = db.query(Utente).filter(Utente.id == utente_id).first()
    if utente is not None and utente in lavoro.assegnatari:
        lavoro.assegnatari.remove(utente)   # <- toglie la riga dalla tabella-ponte
        db.commit()
        db.refresh(lavoro)
    return lavoro
