"""Schemi per l'Organizzazione (l'azienda/tenant)."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OrganizzazioneCreate(BaseModel):
    nome: str


class OrganizzazioneRead(BaseModel):
    id: int
    nome: str
    creato_il: datetime
    model_config = ConfigDict(from_attributes=True)
