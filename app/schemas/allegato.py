"""Schemi Pydantic per gli Allegati (link appesi a una scheda)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AllegatoCreate(BaseModel):
    url: str
    titolo: str | None = None   # etichetta leggibile; se manca si mostra il link


class AllegatoRead(BaseModel):
    id: int
    url: str
    titolo: str | None = None
    creato_il: datetime
    model_config = ConfigDict(from_attributes=True)
