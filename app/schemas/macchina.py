"""Schemi Pydantic per la scheda macchina: macchina, sezioni, voci, allegati."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.voce_macchina import TipoVoce, StatoVoce
from app.schemas.allegato import AllegatoCreate, AllegatoRead   # noqa: F401 (riesportati)
from app.schemas.reparto import RepartoRead


# ---------- SEZIONI ----------

class SezioneCreate(BaseModel):
    nome: str
    # Non indicato = in fondo. Lo calcola il server: il conteggio che aveva il
    # browser sbaglia appena si cancella una sezione (restano dei buchi).
    ordine: int | None = None


class SezioneUpdate(BaseModel):
    nome: str | None = None
    ordine: int | None = None


class OrdineSezioni(BaseModel):
    """L'ordine nuovo, per intero: la lista degli id come devono comparire.

    Si manda tutta la lista invece di "sposta questa su di uno" perche' cosi'
    il riordino e' UN'operazione sola: non ci sono stati intermedi in cui due
    sezioni hanno lo stesso numero, e se i numeri erano gia' incasinati (tutti
    zero, buchi, doppioni) il salvataggio li rimette a posto da solo."""
    sezioni_ids: list[int]


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
    # Sotto quale argomento sta questa voce. Vuoto = e' una voce a se',
    # e puo' diventare lei stessa un argomento.
    genitore_id: int | None = None


class VoceUpdate(BaseModel):
    titolo: str | None = None
    testo: str | None = None
    tipo: TipoVoce | None = None
    stato: StatoVoce | None = None
    in_generale: bool | None = None
    sezioni_ids: list[int] | None = None
    # Mandare genitore_id: null la stacca dall'argomento e la rimette da sola.
    # (Il campo assente e il campo a null sono cose diverse: vedi exclude_unset
    # nel router.)
    genitore_id: int | None = None


class AutoreRead(BaseModel):
    id: int
    nome: str
    model_config = ConfigDict(from_attributes=True)


class VoceRead(BaseModel):
    id: int
    genitore_id: int | None = None
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
    reparti_ids: list[int] = []      # vuota = visibile a tutta l'azienda


class MacchinaUpdate(BaseModel):
    nome: str | None = None
    descrizione: str | None = None
    reparti_ids: list[int] | None = None


class MacchinaRead(BaseModel):
    id: int
    nome: str
    descrizione: str | None = None
    organizzazione_id: int
    reparti: list[RepartoRead] = []
    creato_il: datetime
    model_config = ConfigDict(from_attributes=True)


class MacchinaDettaglio(MacchinaRead):
    """La scheda completa: sezioni, voci e allegati in un colpo solo."""
    sezioni: list[SezioneRead] = []
    voci: list[VoceRead] = []
    allegati: list[AllegatoRead] = []
