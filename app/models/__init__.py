"""
Importa qui tutti i modelli, cosi' SQLAlchemy li "vede" tutti insieme
quando crea le tabelle.
"""
from app.models.organizzazione import Organizzazione
from app.models.utente import Utente
from app.models.progetto import Progetto
from app.models.lavoro import Lavoro, StatoLavoro, PrioritaLavoro
from app.models.assegnazione import assegnazione
from app.models.commento import Commento
from app.models.sotto_attivita import SottoAttivita
from app.models.reparto import Reparto, membro_reparto
from app.models.macchina import Macchina, SezioneMacchina
from app.models.voce_macchina import VoceMacchina, TipoVoce, StatoVoce, voce_sezione
from app.models.allegato import Allegato
from app.models.impegno import Impegno

__all__ = [
    "Utente", "Progetto", "Lavoro",
    "StatoLavoro", "PrioritaLavoro", "assegnazione", "Commento", "Organizzazione", "SottoAttivita",
    "Reparto", "membro_reparto",
    "Macchina", "SezioneMacchina", "VoceMacchina", "TipoVoce", "StatoVoce", "voce_sezione",
    "Allegato", "Impegno",
]
