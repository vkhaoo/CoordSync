"""
Router di autenticazione: registrazione e login.

- /auth/register : crea AZIENDA + primo utente (admin) insieme. E' l'unico
  modo legittimo di far nascere un'azienda. Ritorna subito un token (auto-login).
- /auth/login    : email + password -> token JWT.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.organizzazione import Organizzazione
from app.models.utente import Utente, RuoloUtente
from app.schemas.utente import UtenteRead
from app.appartenenze import iscrivi
from app.security import (
    verifica_password, crea_token, hash_password,
    crea_token_scopo, leggi_token_scopo,
)
from app.schemas.validators import PasswordStr
from app.dependencies import get_current_user
from app.notifiche import invia_email
from app import limiti
from app.email_templates import (
    verifica_email as email_verifica_template,
    reset_password as email_reset_template,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPO_VERIFICA = "verifica_email"


def _invia_verifica(utente: Utente) -> None:
    """Genera il link di verifica e lo 'invia' (in sviluppo: log)."""
    token = crea_token_scopo(utente.id, SCOPO_VERIFICA, durata_minuti=60 * 24)
    # Il link punta a questo backend; l'utente ci clicca e l'email risulta verificata.
    link = f"{settings.base_url}/auth/verifica-email?token={token}"
    oggetto, testo, html = email_verifica_template(utente.nome, link)
    invia_email(destinatario=utente.email, oggetto=oggetto, corpo=testo, corpo_html=html)


# ---------- REGISTRAZIONE ----------

class RegisterRichiesta(BaseModel):
    nome_azienda: str
    nome: str
    email: EmailStr
    password: PasswordStr


class TokenRisposta(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenRisposta, status_code=201)
def register(dati: RegisterRichiesta, db: Session = Depends(get_db)):
    # L'email non deve essere gia' in uso.
    if db.query(Utente).filter(Utente.email == dati.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email gia' registrata")

    # 1) Creo l'azienda.
    org = Organizzazione(nome=dati.nome_azienda)
    db.add(org)
    db.flush()   # assegna un id a org senza chiudere la transazione

    # 2) Creo il primo utente, che diventa ADMIN dell'azienda.
    admin = Utente(
        nome=dati.nome,
        email=dati.email,
        password_hash=hash_password(dati.password),
        ruolo=RuoloUtente.admin,
        organizzazione_id=org.id,
    )
    db.add(admin)
    db.flush()   # serve l'id dell'utente per la tessera

    # 3) La tessera di appartenenza: da qui in avanti e' quella che dice chi
    #    lavora dove e con che ruolo (vedi app/appartenenze.py).
    iscrivi(db, admin, org.id, RuoloUtente.admin)

    db.commit()
    db.refresh(admin)

    # Invio l'email di verifica (in sviluppo: link nei log).
    _invia_verifica(admin)

    # Lo loggo subito: gli restituisco un token.
    return TokenRisposta(access_token=crea_token(admin.id))


# ---------- LOGIN ----------

class LoginRichiesta(BaseModel):
    email: EmailStr
    password: str


@router.post("/login", response_model=TokenRisposta)
def login(dati: LoginRichiesta, richiesta: Request, db: Session = Depends(get_db)):
    ip = richiesta.client.host if richiesta.client else "sconosciuto"

    # Prima di tutto: chi ha gia' sbagliato troppe volte aspetta.
    attesa = limiti.attesa_richiesta(dati.email, ip)
    if attesa is not None:
        raise HTTPException(
            status_code=429,
            detail=f"Troppi tentativi di accesso. Riprova fra {attesa} secondi.",
            headers={"Retry-After": str(attesa)},
        )

    utente = db.query(Utente).filter(Utente.email == dati.email).first()
    # Stesso errore generico se l'utente non c'e' o la password e' sbagliata.
    if (utente is None
            or utente.password_hash is None
            or not verifica_password(dati.password, utente.password_hash)):
        limiti.registra_fallimento(dati.email, ip)
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    limiti.azzera(dati.email, ip)   # chi entra davvero riparte pulito
    return TokenRisposta(access_token=crea_token(utente.id))


@router.get("/me", response_model=UtenteRead)
def leggi_me(current: Utente = Depends(get_current_user)):
    """Restituisce l'utente attualmente loggato (nome, email, ruolo, azienda).
    Serve al frontend per sapere che ruolo ho e adattare l'interfaccia."""
    return current


@router.get("/verifica-email", response_class=HTMLResponse)
def verifica_email(token: str, db: Session = Depends(get_db)):
    """L'utente arriva qui cliccando il link nell'email. Se il token e' valido,
    segna l'email come verificata."""
    utente_id = leggi_token_scopo(token, SCOPO_VERIFICA)
    if utente_id is None:
        return HTMLResponse("<h2>Link non valido o scaduto.</h2>", status_code=400)

    utente = db.query(Utente).filter(Utente.id == int(utente_id)).first()
    if utente is None:
        return HTMLResponse("<h2>Utente non trovato.</h2>", status_code=404)

    utente.email_verificata = True
    db.commit()
    return HTMLResponse("<h2>Email verificata. Puoi tornare all'app e accedere.</h2>")


@router.post("/reinvia-verifica", status_code=202)
def reinvia_verifica(current: Utente = Depends(get_current_user)):
    """Reinvia il link di verifica all'utente loggato (se non gia' verificato)."""
    if current.email_verificata:
        return {"messaggio": "Email gia' verificata"}
    _invia_verifica(current)
    return {"messaggio": "Email di verifica inviata"}


# ---------- RECUPERO PASSWORD ----------

SCOPO_RESET = "reset_password"


class RichiediResetRichiesta(BaseModel):
    email: EmailStr


class ResetPasswordRichiesta(BaseModel):
    token: str
    nuova_password: PasswordStr


@router.post("/richiedi-reset", status_code=202)
def richiedi_reset(dati: RichiediResetRichiesta, db: Session = Depends(get_db)):
    """L'utente chiede il reset inserendo l'email. Se esiste, gli mandiamo il link.
    Rispondiamo SEMPRE ok (anche se l'email non esiste) per non rivelare quali
    email sono registrate (evita 'email enumeration')."""
    utente = db.query(Utente).filter(Utente.email == dati.email).first()
    if utente is not None:
        token = crea_token_scopo(utente.id, SCOPO_RESET, durata_minuti=60)
        # Il link porta alla PAGINA del frontend dove si digita la nuova password.
        link = f"{settings.frontend_url}/?reset_token={token}"
        oggetto, testo, html = email_reset_template(utente.nome, link)
        invia_email(destinatario=utente.email, oggetto=oggetto, corpo=testo, corpo_html=html)
    return {"messaggio": "Se l'email e' registrata, riceverai un link per reimpostare la password"}


@router.post("/reset-password", status_code=200)
def reset_password(dati: ResetPasswordRichiesta, db: Session = Depends(get_db)):
    """L'utente arriva qui dal link, con il token e la nuova password."""
    utente_id = leggi_token_scopo(dati.token, SCOPO_RESET)
    if utente_id is None:
        raise HTTPException(status_code=400, detail="Link non valido o scaduto")

    utente = db.query(Utente).filter(Utente.id == int(utente_id)).first()
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    utente.password_hash = hash_password(dati.nuova_password)
    # La password ora l'ha scelta lui: se era obbligato a cambiarla, l'obbligo decade.
    utente.deve_cambiare_password = False
    db.commit()
    return {"messaggio": "Password reimpostata. Ora puoi accedere."}


# ---------- CAMBIO PASSWORD (utente loggato) ----------

class CambiaPasswordRichiesta(BaseModel):
    vecchia_password: str
    nuova_password: PasswordStr


@router.post("/cambia-password", status_code=200)
def cambia_password(dati: CambiaPasswordRichiesta, db: Session = Depends(get_db),
                    current: Utente = Depends(get_current_user)):
    """Cambio password volontario o obbligato (primo accesso di un utente
    creato dall'admin). Chiedo la vecchia password: un token rubato da solo
    non deve bastare a cambiarla."""
    if current.password_hash is None or not verifica_password(dati.vecchia_password, current.password_hash):
        raise HTTPException(status_code=401, detail="Password attuale non corretta")

    current.password_hash = hash_password(dati.nuova_password)
    current.deve_cambiare_password = False
    db.commit()
    return {"messaggio": "Password aggiornata."}


# ---------- INVITI ----------

# Lo scopo del token di invito. Usato anche da /utenti/invita (che lo genera).
SCOPO_INVITO = "invito"


class AccettaInvitoRichiesta(BaseModel):
    token: str
    password: PasswordStr


@router.post("/accetta-invito", status_code=200)
def accetta_invito(dati: AccettaInvitoRichiesta, db: Session = Depends(get_db)):
    """L'invitato arriva qui dal link nell'email e sceglie la SUA password.
    L'admin non la conosce mai: piu' sicuro del modello 'admin crea con password'."""
    utente_id = leggi_token_scopo(dati.token, SCOPO_INVITO)
    if utente_id is None:
        raise HTTPException(status_code=400, detail="Invito non valido o scaduto")

    utente = db.query(Utente).filter(Utente.id == int(utente_id)).first()
    if utente is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Un invito vale una volta sola: se la password c'e' gia', e' gia' stato usato.
    if utente.password_hash is not None:
        raise HTTPException(status_code=400, detail="Invito gia' utilizzato")

    utente.password_hash = hash_password(dati.password)
    # L'invito e' arrivato via email: cliccare il link prova gia' che l'email e' sua.
    utente.email_verificata = True
    db.commit()
    return {"messaggio": "Password impostata. Ora puoi accedere."}


# ---------- ESPORTAZIONE DEI PROPRI DATI ----------

@router.get("/me/export")
def esporta_i_miei_dati(db: Session = Depends(get_db),
                        current: Utente = Depends(get_current_user)):
    """Tutto quello che l'app sa DI TE, in un file JSON da portarsi via.

    E' la portabilita' dei dati: ognuno deve poter tirare fuori la propria
    roba senza chiedere il permesso a nessuno.

    Cosa c'e' dentro: il profilo, quello che hai SCRITTO (commenti, voci di
    storico, link), quello che ti riguarda (lavori assegnati, impegni in
    agenda, avvisi). Cosa NON c'e': i dati dell'azienda che non sono tuoi, e
    la password, che non esiste in chiaro nemmeno per noi.
    """
    from app.models.commento import Commento
    from app.models.voce_macchina import VoceMacchina
    from app.models.allegato import Allegato
    from app.models.impegno import Impegno, partecipante_impegno
    from app.models.notifica import Notifica

    def quando(valore):
        return valore.isoformat() if valore else None

    commenti = (db.query(Commento).filter(Commento.autore_id == current.id)
                .order_by(Commento.creato_il).all())
    voci = (db.query(VoceMacchina).filter(VoceMacchina.autore_id == current.id)
            .order_by(VoceMacchina.creato_il).all())
    allegati = (db.query(Allegato).filter(Allegato.autore_id == current.id)
                .order_by(Allegato.creato_il).all())
    impegni = (db.query(Impegno)
               .filter(Impegno.id.in_(
                   db.query(partecipante_impegno.c.impegno_id)
                   .filter(partecipante_impegno.c.utente_id == current.id)
                   .scalar_subquery()))
               .order_by(Impegno.inizio).all())
    avvisi = (db.query(Notifica).filter(Notifica.utente_id == current.id)
              .order_by(Notifica.creato_il).all())

    return {
        "esportato_il": datetime.now(timezone.utc).isoformat(),
        "profilo": {
            "nome": current.nome,
            "email": current.email,
            "ruolo": current.ruolo.value,
            "email_verificata": current.email_verificata,
            "azienda": current.organizzazione.nome if current.organizzazione else None,
            "reparti": [r.nome for r in current.reparti],
        },
        "lavori_assegnati": [
            {"titolo": l.titolo, "descrizione": l.descrizione,
             "stato": l.stato.value, "priorita": l.priorita.value,
             "scadenza": l.data_scadenza.isoformat() if l.data_scadenza else None,
             "progetto": l.progetto.nome if l.progetto else None}
            for l in current.lavori
        ],
        "commenti_scritti": [
            {"testo": c.testo, "quando": quando(c.creato_il),
             "lavoro": c.lavoro.titolo if c.lavoro else None}
            for c in commenti
        ],
        "voci_di_storico_scritte": [
            {"tipo": v.tipo.value, "titolo": v.titolo, "testo": v.testo,
             "stato": v.stato.value if v.stato else None,
             "quando": quando(v.creato_il),
             "macchina": v.macchina.nome if v.macchina else None}
            for v in voci
        ],
        "link_aggiunti": [
            {"titolo": a.titolo, "url": a.url, "quando": quando(a.creato_il)}
            for a in allegati
        ],
        "agenda": [
            {"titolo": i.titolo, "note": i.note, "luogo": i.luogo,
             "inizio": quando(i.inizio), "fine": quando(i.fine),
             "organizzatore": i.organizzatore.nome if i.organizzatore else None,
             "partecipanti": [p.nome for p in i.partecipanti]}
            for i in impegni
        ],
        "avvisi_ricevuti": [
            {"testo": n.testo, "letto": n.letta, "quando": quando(n.creato_il)}
            for n in avvisi
        ],
    }


# ---------- CANCELLAZIONE DEL PROPRIO ACCOUNT ----------

@router.delete("/me", status_code=204)
def cancella_il_mio_account(db: Session = Depends(get_db),
                            current: Utente = Depends(get_current_user)):
    """Chiunque puo' andarsene. E' il diritto alla cancellazione.

    Il lavoro che ha fatto resta alla squadra, attribuito a "Utente eliminato";
    quello che sparisce e' l'identita' (vedi app/cancellazione.py).

    Unica eccezione: l'ultimo admin di un'azienda. Lasciarla senza timone
    significherebbe che nessuno puo' piu' gestire utenti e permessi, e non c'e'
    modo di rimediare dall'interno. Prima si nomina un altro admin.
    """
    from app.cancellazione import anonimizza, e_ultimo_admin

    if e_ultimo_admin(db, current):
        raise HTTPException(
            status_code=409,
            detail="Sei l'ultimo amministratore: nomina prima qualcun altro, "
                   "altrimenti l'azienda resta senza nessuno che possa gestirla.",
        )

    anonimizza(db, current)
    db.commit()
