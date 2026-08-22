"""
Schemi Pydantic per il Commento.

Novita': CommentoRead contiene un UtenteRead ANNIDATO (l'autore).
Cosi' la risposta non ti da' solo 'autore_id: 3', ma l'oggetto autore
completo (id, nome, email). Molto piu' comodo per il frontend: mostra
"Marco" senza dover fare una seconda chiamata per sapere chi e' l'utente 3.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.utente import UtenteRead


class CommentoCreate(BaseModel):
    """Per creare un commento serve solo il testo.
    L'autore = utente loggato (dal token); il lavoro = dall'URL."""
    testo: str


class CommentoRead(BaseModel):
    id: int
    testo: str
    creato_il: datetime
    autore: UtenteRead   # <-- schema annidato: l'autore completo, non solo l'id

    model_config = ConfigDict(from_attributes=True)
