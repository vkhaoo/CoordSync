"""
Router degli Utenti: creazione e gestione ruoli, riservate all'ADMIN.

L'admin aggiunge utenti (scegliendone il ruolo) e puo' cambiare il ruolo
degli utenti della sua azienda. Il nuovo utente eredita l'organizzazione
da chi lo crea.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.utente import Utente, RuoloUtente
from app.schemas.utente import UtenteCreate, UtenteRead
from app.appartenenze import condizione_membro, iscrivi
from app.security import hash_password, crea_token_scopo
from app.dependencies import richiedi_azienda, richiedi_ruolo
from app.notifiche import invia_email
from app.email_templates import invito as email_invito_template
from app.routers.auth import SCOPO_INVITO, SCOPO_INVITO_AZIENDA

router = APIRouter(prefix="/utenti", tags=["utenti"])


@router.post("", response_model=UtenteRead, status_code=201)
def crea_utente(dati: UtenteCreate, db: Session = Depends(get_db),
                current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    if db.query(Utente).filter(Utente.email == dati.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email gia' registrata")

    utente = Utente(
        nome=dati.nome,
        email=dati.email,
        password_hash=hash_password(dati.password),
        ruolo=dati.ruolo,
        organizzazione_id=current.org_attiva_id,
        # L'admin conosce questa password: al primo accesso l'utente ne sceglie una sua.
        deve_cambiare_password=True,
    )
    db.add(utente)
    db.flush()
    iscrivi(db, utente, current.org_attiva_id, dati.ruolo)
    db.commit()
    db.refresh(utente)
    return utente


class InvitoRichiesta(BaseModel):
    nome: str
    email: EmailStr
    ruolo: RuoloUtente = RuoloUtente.operatore


GIORNI_INVITO = 7   # un invito puo' restare qualche giorno nella casella


def _nome_azienda_attiva(db: Session, current: Utente) -> str:
    """Il nome dell'azienda in cui si sta lavorando adesso.

    Non `current.organizzazione.nome`: quella e' l'azienda di casa, e chi sta
    lavorando altrove manderebbe inviti con scritto il nome sbagliato."""
    from app.models.organizzazione import Organizzazione
    org = db.query(Organizzazione).filter(
        Organizzazione.id == current.org_attiva_id).first()
    return org.nome if org else "CoordSync"


@router.post("/invita", response_model=UtenteRead, status_code=201)
def invita_utente(dati: InvitoRichiesta, db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    """Invita qualcuno nell'azienda in cui sto lavorando.

    Due strade, a seconda di chi c'e' dall'altra parte:

    - **email nuova**: nasce un account SENZA password, che l'invitato
      scegliera' dal link. E' l'onboarding di sempre.
    - **email che ha gia' un account CoordSync**: si scrive un invito in
      attesa, che quella persona trova sia nella posta sia dentro l'app, e a
      cui puo' rispondere di si' o di no. Finche' non accetta non vede niente
      di quest'azienda e non compare fra i colleghi.

    Il consenso non e' un dettaglio: un amministratore non deve poter
    attaccare l'account di qualcun altro alla propria azienda.
    """
    esistente = db.query(Utente).filter(Utente.email == dati.email).first()
    if esistente is not None:
        return _invita_chi_ha_gia_un_account(db, current, esistente, dati.ruolo)

    utente = Utente(
        nome=dati.nome,
        email=dati.email,
        password_hash=None,   # niente password: la imposta l'invitato
        ruolo=dati.ruolo,
        organizzazione_id=current.org_attiva_id,
    )
    db.add(utente)
    db.flush()
    iscrivi(db, utente, current.org_attiva_id, dati.ruolo)
    db.commit()
    db.refresh(utente)

    token = crea_token_scopo(utente.id, SCOPO_INVITO,
                             durata_minuti=60 * 24 * GIORNI_INVITO)
    link = f"{settings.frontend_url}/?invito_token={token}"
    oggetto, testo, html = email_invito_template(
        utente.nome, _nome_azienda_attiva(db, current), link)
    invia_email(destinatario=utente.email, oggetto=oggetto, corpo=testo, corpo_html=html)
    return utente


def _invita_chi_ha_gia_un_account(db: Session, current: Utente, invitato: Utente,
                                  ruolo: RuoloUtente):
    """Manda l'invito a chi CoordSync ce l'ha gia'.

    Si risponde 202 ("preso in carico") e non 201 ("creato"): un utente non e'
    stato creato, e finche' quella persona non accetta, per quest'azienda non
    esiste. Si risponde anche senza dire niente di lei: chi invita ha scritto
    un indirizzo email, e non deve venire a sapere dalla risposta come si
    chiama chi c'e' dietro.
    """
    from fastapi.responses import JSONResponse
    from app.appartenenze import ruolo_in
    from app.email_templates import invito_azienda as email_invito_azienda

    if invitato.password_hash is None and invitato.nome == "Utente eliminato":
        # Un account cancellato non si "riattiva" invitandolo.
        raise HTTPException(status_code=409, detail="Email gia' registrata")

    from app.models.appartenenza import Appartenenza, StatoAppartenenza
    tessera = (
        db.query(Appartenenza)
        .filter(Appartenenza.utente_id == invitato.id,
                Appartenenza.organizzazione_id == current.org_attiva_id)
        .first()
    )
    if tessera is not None and tessera.stato == StatoAppartenenza.attiva:
        raise HTTPException(status_code=409,
                            detail="Questa persona fa gia' parte dell'azienda")

    # L'invito si SCRIVE, come tessera in attesa: cosi' l'invitato lo trova
    # dentro l'app anche se l'email si perde per strada, e puo' rispondere di
    # no. Finche' resta "invitata" non apre proprio niente (vedi ruolo_in).
    #
    # Il link email resta la scorciatoia: nel token c'e' tutto quello che
    # serve ad accettare senza nemmeno collegarsi.
    iscrivi(db, invitato, current.org_attiva_id, ruolo,
            stato=StatoAppartenenza.invitata)
    db.commit()

    soggetto = f"{invitato.id}:{current.org_attiva_id}:{ruolo.value}"
    token = crea_token_scopo(soggetto, SCOPO_INVITO_AZIENDA,
                             durata_minuti=60 * 24 * GIORNI_INVITO)
    link = f"{settings.frontend_url}/?invito_azienda_token={token}"
    oggetto, testo, html = email_invito_azienda(
        invitato.nome, _nome_azienda_attiva(db, current), link)
    invia_email(destinatario=invitato.email, oggetto=oggetto, corpo=testo, corpo_html=html)

    return JSONResponse(status_code=202,
                        content={"messaggio": "Invito inviato."})


@router.get("", response_model=list[UtenteRead])
def elenca_utenti(db: Session = Depends(get_db),
                  current: Utente = Depends(richiedi_azienda)):
    """I colleghi dell'azienda in cui sto lavorando.

    Il ruolo che si legge qui e' quello che ognuno ha IN QUEST'AZIENDA, preso
    dalla sua tessera: chi e' amministratore a casa propria e operatore qui
    dev'essere mostrato come operatore, se no si finisce per assegnargli cose
    che il server gli rifiutera'.
    """
    from app.models.appartenenza import Appartenenza, StatoAppartenenza

    tessere = (
        db.query(Appartenenza)
        .filter(Appartenenza.organizzazione_id == current.org_attiva_id,
                # Chi e' stato invitato ma non ha ancora risposto NON e' un
                # collega: non deve comparire fra le persone a cui assegnare
                # lavori, perche' potrebbe anche dire di no.
                Appartenenza.stato == StatoAppartenenza.attiva)
        .all()
    )
    elenco = []
    for tessera in tessere:
        dati = UtenteRead.model_validate(tessera.utente).model_dump()
        dati["ruolo"] = tessera.ruolo
        dati["organizzazione_id"] = current.org_attiva_id
        elenco.append(dati)
    return elenco


class CambioRuolo(BaseModel):
    ruolo: RuoloUtente


@router.patch("/{utente_id}/ruolo", response_model=UtenteRead)
def cambia_ruolo(utente_id: int, dati: CambioRuolo, db: Session = Depends(get_db),
                 current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    # Solo utenti della MIA azienda.
    utente = (
        db.query(Utente)
        .filter(Utente.id == utente_id,
                condizione_membro(current.org_attiva_id))
        .first()
    )
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Il ruolo vive sulla tessera dell'azienda in cui si sta lavorando.
    iscrivi(db, utente, current.org_attiva_id, dati.ruolo)
    # La colonna sulla riga dell'utente si tocca SOLO se qui e' casa sua:
    # cambiargli il ruolo qui non deve cambiarglielo nell'azienda dov'e' nato.
    if utente.organizzazione_id == current.org_attiva_id:
        utente.ruolo = dati.ruolo
    db.commit()
    db.refresh(utente)

    risposta = UtenteRead.model_validate(utente).model_dump()
    risposta["ruolo"] = dati.ruolo      # il ruolo QUI, che e' quello che si e' appena cambiato
    risposta["organizzazione_id"] = current.org_attiva_id
    return risposta


@router.delete("/{utente_id}", status_code=204)
def elimina_utente(utente_id: int, db: Session = Depends(get_db),
                   current: Utente = Depends(richiedi_ruolo(RuoloUtente.admin))):
    """L'admin fa uscire un collega dall'azienda.

    Due esiti diversi, e la differenza conta parecchio:

    - se quella persona lavora **solo qui**, vale la regola di sempre: il
      lavoro resta alla squadra, l'identita' sparisce e non entra piu';
    - se lavora **anche altrove**, esce solo da quest'azienda. Sarebbe grave
      il contrario: un amministratore non deve poter cancellare un account
      che serve anche a qualcun altro.

    Per cancellare se stesso c'e' DELETE /auth/me, cosi' non capita per
    sbaglio dall'elenco degli utenti.
    """
    from app.cancellazione import anonimizza, e_ultimo_admin
    from app.models.appartenenza import Appartenenza

    if utente_id == current.id:
        raise HTTPException(
            status_code=400,
            detail="Per cancellare il tuo account usa la voce nel tuo profilo.",
        )

    utente = (
        db.query(Utente)
        .filter(Utente.id == utente_id,
                condizione_membro(current.org_attiva_id))
        .first()
    )
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if utente.password_hash is None and utente.nome == "Utente eliminato":
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if e_ultimo_admin(db, utente, current.org_attiva_id):
        raise HTTPException(status_code=409,
                            detail="E' l'ultimo amministratore: nominane un altro prima.")

    altre = [t for t in utente.appartenenze
             if t.organizzazione_id != current.org_attiva_id]
    if altre:
        # Lavora anche altrove: si toglie solo la tessera di qui, e con lei
        # i reparti e i lavori di quest'azienda.
        db.query(Appartenenza).filter(
            Appartenenza.utente_id == utente.id,
            Appartenenza.organizzazione_id == current.org_attiva_id,
        ).delete(synchronize_session=False)
        utente.reparti = [r for r in utente.reparti
                          if r.organizzazione_id != current.org_attiva_id]
        utente.lavori = [l for l in utente.lavori
                         if l.progetto.organizzazione_id != current.org_attiva_id]
    else:
        anonimizza(db, utente)
    db.commit()
