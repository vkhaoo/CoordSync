"""
Le "guardie" dell'app.

Sono due, e la differenza conta:

- **get_current_user** dice soltanto CHI stai chiedendo. Passa anche se non
  fai parte di nessuna azienda: e' il caso di chi si e' appena iscritto e deve
  ancora crearne una o accettare un invito. Serve alle poche pagine che devono
  funzionare in quel momento — il proprio profilo, l'elenco delle proprie
  aziende, la creazione della prima.

- **richiedi_azienda** aggiunge "e dentro quale azienda". La usano tutti gli
  endpoint che parlano di progetti, lavori, macchine, agenda: senza un'azienda
  attiva quelle domande non hanno risposta, e rispondere con un elenco vuoto
  sarebbe peggio di un errore chiaro.

richiedi_ruolo, che serve per i permessi, passa da richiedi_azienda: un ruolo
esiste solo dentro un'azienda.
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
    """Chi sta chiedendo. L'azienda attiva puo' anche non esserci."""
    letto = leggi_token(credenziali.credentials)
    if letto is None:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")
    utente_id, org_dal_token = letto

    utente = db.query(Utente).filter(Utente.id == utente_id).first()
    if utente is None:
        raise HTTPException(status_code=401, detail="Utente non trovato")

    # --- dentro QUALE azienda sta lavorando adesso ---------------------------
    # L'azienda arriva dal token. Se manca puo' essere un token emesso prima
    # del multi-azienda (allora vale quella di casa, cosi' nessuno viene
    # buttato fuori per un token vecchio in tasca) oppure un account appena
    # nato, che di aziende non ne ha ancora nessuna.
    org = org_dal_token if org_dal_token is not None else utente.organizzazione_id

    if org is not None:
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


def richiedi_azienda(current: Utente = Depends(get_current_user)) -> Utente:
    """Come sopra, ma pretende di stare dentro un'azienda.

    Il 409 e' scelto apposta: non e' "non hai il permesso" (403) ne' "non
    esiste" (404), e' "manca un passaggio". Il frontend lo riconosce e apre la
    schermata di scelta, dove si crea la prima azienda o si accetta un invito.
    """
    if current.org_attiva_id is None:
        raise HTTPException(
            status_code=409,
            detail="Non fai ancora parte di nessuna azienda: creane una o "
                   "accetta un invito.",
        )
    return current


def richiedi_ruolo(*ruoli_ammessi):
    """
    Crea una dependency che lascia passare SOLO gli utenti con uno dei ruoli
    indicati. Uso: Depends(richiedi_ruolo(RuoloUtente.admin, RuoloUtente.caposquadra)).
    Evita di riscrivere lo stesso controllo in ogni endpoint.
    """
    def controllo(current: Utente = Depends(richiedi_azienda)) -> Utente:
        if current.ruolo_attivo not in ruoli_ammessi:
            raise HTTPException(status_code=403, detail="Permesso negato per il tuo ruolo")
        return current
    return controllo
