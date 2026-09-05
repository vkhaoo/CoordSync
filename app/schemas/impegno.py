"""Schemi Pydantic per l'agenda: impegni e scadenze in vista."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ImpegnoBase(BaseModel):
    titolo: str
    note: str | None = None
    luogo: str | None = None
    inizio: datetime          # data E ora: e' il punto dell'agenda
    fine: datetime | None = None
    promemoria_minuti: int | None = None   # None = nessun promemoria


class ImpegnoCreate(ImpegnoBase):
    # Chi ci deve stare. Vuoto = solo io. Con piu' nomi diventa una riunione:
    # UN impegno solo, che compare nell'agenda di tutti i partecipanti.
    # Invitare qualcun altro e' riservato a chi coordina (admin e caposquadra).
    partecipanti_ids: list[int] = []
    lavoro_id: int | None = None
    macchina_id: int | None = None


class ImpegnoUpdate(BaseModel):
    titolo: str | None = None
    note: str | None = None
    luogo: str | None = None
    inizio: datetime | None = None
    fine: datetime | None = None
    promemoria_minuti: int | None = None
    partecipanti_ids: list[int] | None = None
    lavoro_id: int | None = None
    macchina_id: int | None = None


class PersonaRead(BaseModel):
    id: int
    nome: str
    model_config = ConfigDict(from_attributes=True)


class ImpegnoRead(ImpegnoBase):
    id: int
    organizzatore: PersonaRead
    partecipanti: list[PersonaRead] = []
    lavoro_id: int | None = None
    macchina_id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class ScadenzaRead(BaseModel):
    """Il secondo livello dell'agenda: le scadenze dei lavori, che sono solo
    date (nessuna ora) e non si modificano da qui."""
    lavoro_id: int
    titolo: str
    data_scadenza: date
    stato: str
    progetto: str
    mia: bool   # true se sono fra gli assegnatari


class AgendaRead(BaseModel):
    """Cosa serve al calendario per disegnare un intervallo di giorni."""
    impegni: list[ImpegnoRead] = []
    scadenze: list[ScadenzaRead] = []
