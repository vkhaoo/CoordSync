"""Schemi Pydantic per la scheda macchina: macchina, sezioni, voci, allegati."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.voce_macchina import TipoVoce, StatoVoce
from app.schemas.allegato import AllegatoCreate, AllegatoRead   # noqa: F401 (riesportati)


# ---------- SEZIONI ----------

class SezioneCreate(BaseModel):
    nome: str
    ordine: int = 0


class SezioneUpdate(BaseModel):
    nome: str | None = None
    ordine: int | None = None


class SezioneRead(BaseModel):
    id: int
    nome: str
    ordine: int
    macchina_id: int
    allegati: list[AllegatoRead] = []
    model_config = ConfigDict(from_attributes=True)


# ---------- VOCI ----------

class VoceCreate(BaseModel):
    tipo: TipoVoce
    titolo: str
    testo: str | None = None
    # Solo per tipo "lavoro": da_fare / in_corso / fatto.
    stato: StatoVoce | None = None
    # Dove si vede: nel generale, in certe sezioni, o in entrambi.
    in_generale: bool = True
    sezioni_ids: list[int] = []


class VoceUpdate(BaseModel):
    titolo: str | None = None
    testo: str | None = None
    tipo: TipoVoce | None = None
    stato: StatoVoce | None = None
    in_generale: bool | None = None
    sezioni_ids: list[int] | None = None


class AutoreRead(BaseModel):
    id: int
    nome: str
    model_config = ConfigDict(from_attributes=True)


class VoceRead(BaseModel):
    id: int
    tipo: TipoVoce
    stato: StatoVoce | None = None
    titolo: str
    testo: str | None = None
    in_generale: bool
    macchina_id: int
    creato_il: datetime
    autore: AutoreRead | None = None
    sezioni: list[SezioneRead] = []
    allegati: list[AllegatoRead] = []
    model_config = ConfigDict(from_attributes=True)


# ---------- MACCHINA ----------

class MacchinaCreate(BaseModel):
    nome: str
    descrizione: str | None = None   # modello, matricola, note d'impianto
    reparto_id: int | None = None    # None = visibile a tutta l'azienda


class MacchinaUpdate(BaseModel):
    nome: str | None = None
    descrizione: str | None = None
    reparto_id: int | None = None


class MacchinaRead(BaseModel):
    id: int
    nome: str
    descrizione: str | None = None
    organizzazione_id: int
    reparto_id: int | None = None
    creato_il: datetime
    model_config = ConfigDict(from_attributes=True)


class MacchinaDettaglio(MacchinaRead):
    """La scheda completa: sezioni, voci e allegati in un colpo solo."""
    sezioni: list[SezioneRead] = []
    voci: list[VoceRead] = []
    allegati: list[AllegatoRead] = []
