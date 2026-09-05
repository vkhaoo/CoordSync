"""
La "guardia" dell'app: get_current_user.

E' una dependency che, a OGNI richiesta protetta, legge il token
dall'header 'Authorization: Bearer <token>', capisce chi sei e carica
il tuo utente dal database. Se il token manca/e' invalido/scaduto -> 401.

Da qui in poi gli endpoint sanno CHI chiede, e possono filtrare per
la sua organizzazione.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.appartenenze import ruolo_in
from app.database import get_db
from app.models.utente import Utente
from app.security import leggi_token

# Estrae automaticamente il token dall'header Authorization: Bearer ...
_bearer = HTTPBearer()


def get_current_user(
    credenziali: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Utente:
    letto = leggi_token(credenziali.credentials)
    if letto is None:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")
    utente_id, org_dal_token = letto

    utente = db.query(Utente).filter(Utente.id == utente_id).first()
    if utente is None:
        raise HTTPException(status_code=401, detail="Utente non trovato")

    # --- dentro QUALE azienda sta lavorando adesso ---------------------------
    # L'azienda arriva dal token. Se manca e' un token emesso prima del
    # multi-azienda: vale quella di casa, cosi' nessuno viene buttato fuori il
    # giorno della pubblicazione solo perche' aveva un token vecchio in tasca.
    org = org_dal_token if org_dal_token is not None else utente.organizzazione_id

    # Il controllo che regge tutto: il token DICE un'azienda, la tessera
    # CONFERMA che ci si puo' stare. Senza questa riga, chi si fabbrica un
    # token con dentro un'altra azienda entrerebbe in casa d'altri.
    ruolo = ruolo_in(db, utente, org)
    if ruolo is None:
        raise HTTPException(status_code=403,
                            detail="Non fai (piu') parte di questa azienda")

    utente._org_attiva_id = org
    utente._ruolo_attivo = ruolo
    return utente


def richiedi_ruolo(*ruoli_ammessi):
    """
    Crea una dependency che lascia passare SOLO gli utenti con uno dei ruoli
    indicati. Uso: Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)).
    Evita di riscrivere lo stesso controllo in ogni endpoint.
    """
    def controllo(current: Utente = Depends(get_current_user)) -> Utente:
        if current.ruolo_attivo not in ruoli_ammessi:
            raise HTTPException(status_code=403, detail="Permesso negato per il tuo ruolo")
        return current
    return controllo
