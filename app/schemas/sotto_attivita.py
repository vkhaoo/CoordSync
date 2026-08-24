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
    lavoro_id: int

    model_config = ConfigDict(from_attributes=True)
