"""Schemi Pydantic per la SottoAttivita (voce di checklist)."""
from pydantic import BaseModel, ConfigDict


class SottoAttivitaCreate(BaseModel):
    testo: str


class SottoAttivitaUpdate(BaseModel):
    """Modifica parziale: testo e/o stato 'completata' (entrambi opzionali)."""
    testo: str | None = None
    completata: bool | None = None


class SottoAttivitaRead(BaseModel):
    id: int
    testo: str
    completata: bool
    # Il genitore: uno dei due e' valorizzato, l'altro resta a null.
    lavoro_id: int | None = None
    voce_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
