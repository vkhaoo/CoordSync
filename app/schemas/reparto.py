"""Schemi Pydantic per il Reparto (sotto-gruppo dentro l'azienda)."""
from pydantic import BaseModel, ConfigDict


class RepartoBase(BaseModel):
    nome: str


class RepartoCreate(RepartoBase):
    """L'organizzazione NON si passa: viene presa da chi e' loggato."""
    pass


class RepartoUpdate(BaseModel):
    nome: str | None = None


class RepartoRead(RepartoBase):
    id: int
    organizzazione_id: int
    model_config = ConfigDict(from_attributes=True)
