"""
Funzioni di sicurezza: hashing password e token JWT.

Tenute tutte qui, cosi' la logica di sicurezza sta in un posto solo
(piu' facile da controllare e, un domani, da rafforzare).
"""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.config import settings

# Un solo algoritmo, esplicito e collaudato: bcrypt.
_hasher = PasswordHash((BcryptHasher(),))

# Algoritmo di firma dei token.
_ALGORITMO = "HS256"


def hash_password(password: str) -> str:
    """Trasforma una password nella sua impronta irreversibile (da salvare)."""
    return _hasher.hash(password)


def verifica_password(in_chiaro: str, impronta: str) -> bool:
    """Confronta la password digitata con l'impronta salvata."""
    return _hasher.verify(in_chiaro, impronta)


def crea_token(utente_id: int) -> str:
    """Crea un token JWT che identifica l'utente e scade dopo un po'."""
    scadenza = datetime.now(timezone.utc) + timedelta(minutes=settings.token_durata_minuti)
    contenuto = {
        "sub": str(utente_id),   # 'sub' (subject) = chi e' il token: l'id utente
        "exp": scadenza,         # 'exp' = quando scade
    }
    return jwt.encode(contenuto, settings.secret_key, algorithm=_ALGORITMO)


def leggi_token(token: str) -> int | None:
    """Verifica un token e restituisce l'id utente, o None se non valido/scaduto."""
    try:
        contenuto = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITMO])
        return int(contenuto["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
