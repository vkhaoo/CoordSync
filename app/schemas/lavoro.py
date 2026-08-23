"""
Schemi Pydantic per il Lavoro.

Come per il progetto: Base = campi comuni, Create = input, Read = output.
In piu' qui c'e' un LavoroUpdateStato: uno schema minuscolo dedicato al
solo cambio di stato (non vogliamo far reinviare tutto il lavoro per
spostarlo da 'da_fare' a 'in_corso').
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# Riutilizziamo gli enum gia' definiti nel model: una sola fonte di verita'.
from app.models.lavoro import StatoLavoro, PrioritaLavoro
from app.schemas.utente import UtenteRead


class LavoroBase(BaseModel):
    titolo: str
    descrizione: str | None = None
    priorita: PrioritaLavoro = PrioritaLavoro.normale   # default se non fornita


class LavoroCreate(LavoroBase):
    """Per creare un lavoro serve anche dire a QUALE progetto appartiene."""
    progetto_id: int


class LavoroUpdateStato(BaseModel):
    """Schema minimo per il solo cambio di stato."""
    stato: StatoLavoro


class LavoroRead(LavoroBase):
    """Cosa restituisce l'API."""
    id: int
    stato: StatoLavoro
    progetto_id: int
    creato_il: datetime
    aggiornato_il: datetime
    assegnatari: list[UtenteRead] = []   # chi ci lavora (molti-a-molti)
    completato_il: datetime | None = None      # quando e' stato completato
    completato_da: UtenteRead | None = None     # chi l'ha completato

    model_config = ConfigDict(from_attributes=True)
