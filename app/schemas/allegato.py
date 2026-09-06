"""Schemi Pydantic per gli Allegati (link appesi a una scheda)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.validators import UrlSicuro


class AllegatoCreate(BaseModel):
    url: UrlSicuro
    titolo: str | None = None   # etichetta leggibile; se manca si mostra il link


class AllegatoRead(BaseModel):
    id: int
    url: str
    titolo: str | None = None
    creato_il: datetime
    model_config = ConfigDict(from_attributes=True)
