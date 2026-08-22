"""
Regole di validazione riutilizzabili.

PasswordStr: un tipo "stringa password" che impone regole minime di robustezza.
Usarlo negli schemi (al posto di 'str') applica la validazione automaticamente,
in un posto solo: se domani cambiamo le regole, le cambiamo qui.
"""
import re
from typing import Annotated

from pydantic import AfterValidator

# Requisiti minimi (allineati alle buone pratiche): lunghezza + varieta'.
LUNGHEZZA_MINIMA = 8


def _valida_password(v: str) -> str:
    if len(v) < LUNGHEZZA_MINIMA:
        raise ValueError(f"La password deve avere almeno {LUNGHEZZA_MINIMA} caratteri")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("La password deve contenere almeno una lettera")
    if not re.search(r"\d", v):
        raise ValueError("La password deve contenere almeno un numero")
    return v


# Tipo riutilizzabile: una stringa che deve rispettare _valida_password.
PasswordStr = Annotated[str, AfterValidator(_valida_password)]
