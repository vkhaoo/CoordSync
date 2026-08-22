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

from app.database import get_db
from app.models.utente import Utente
from app.security import leggi_token

# Estrae automaticamente il token dall'header Authorization: Bearer ...
_bearer = HTTPBearer()


def get_current_user(
    credenziali: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Utente:
    utente_id = leggi_token(credenziali.credentials)
    if utente_id is None:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")

    utente = db.query(Utente).filter(Utente.id == utente_id).first()
    if utente is None:
        raise HTTPException(status_code=401, detail="Utente non trovato")

    return utente
