"""
Schemi Pydantic per il Lavoro.

Come per il progetto: Base = campi comuni, Create = input, Read = output.
In piu' qui c'e' un LavoroUpdateStato: uno schema minuscolo dedicato al
solo cambio di stato (non vogliamo far reinviare tutto il lavoro per
spostarlo da 'da_fare' a 'in_corso').
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

# Riutilizziamo gli enum gia' definiti nel model: una sola fonte di verita'.
from app.models.lavoro import StatoLavoro, PrioritaLavoro
from app.schemas.utente import UtenteRead
from app.schemas.sotto_attivita import SottoAttivitaRead


class LavoroBase(BaseModel):
    titolo: str
    descrizione: str | None = None
    priorita: PrioritaLavoro = PrioritaLavoro.normale   # default se non fornita
    data_scadenza: date | None = None   # facoltativa; i badge li calcola il frontend


class LavoroCreate(LavoroBase):
    """Per creare un lavoro serve anche dire a QUALE progetto appartiene."""
    progetto_id: int


class LavoroUpdateStato(BaseModel):
    """Schema minimo per il solo cambio di stato."""
    stato: StatoLavoro


class LavoroUpdate(BaseModel):
    """Modifica di un lavoro (tutti opzionali): titolo, descrizione, priorita',
    e anche spostarlo in un altro progetto (progetto_id)."""
    titolo: str | None = None
    descrizione: str | None = None
    priorita: PrioritaLavoro | None = None
    progetto_id: int | None = None
    # None qui vale "togli la scadenza": exclude_unset distingue 'non inviato' da 'null'.
    data_scadenza: date | None = None


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
    sotto_attivita: list[SottoAttivitaRead] = []   # checklist del lavoro

    model_config = ConfigDict(from_attributes=True)
