"""
Schemi Pydantic per il Progetto.

Uno "schema" definisce la FORMA dei dati che entrano ed escono dall'API.
E' diverso dal model (models/progetto.py): il model e' la tabella nel database,
lo schema e' cosa viaggia dentro/fuori dall'API. Pydantic li usa per validare
in ingresso e serializzare in uscita.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProgettoBase(BaseModel):
    """Campi comuni: quello che l'utente puo' fornire."""
    nome: str
    descrizione: str | None = None   # opzionale: se non arriva, resta None


class ProgettoCreate(ProgettoBase):
    """Cosa serve per CREARE un progetto (input).
    NB: l'organizzazione NON si passa piu': viene presa dall'utente loggato."""
    pass


class ProgettoRead(ProgettoBase):
    """Cosa l'API RESTITUISCE (output): include i campi generati dal DB."""
    id: int
    organizzazione_id: int
    creato_il: datetime

    # Permette a Pydantic di leggere i dati da un oggetto SQLAlchemy
    # (non solo da un dizionario). Senza questo, non saprebbe convertire il model.
    model_config = ConfigDict(from_attributes=True)
