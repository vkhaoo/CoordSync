"""
Il controllo che si fa all'avvio: la produzione non deve partire con la
chiave di firma di esempio.

E' l'unica cosa che protegge i token: con la chiave scritta nel codice,
chiunque puo' fabbricarsi un accesso come chiunque altro. Meglio un deploy
che fallisce e si vede, che un'app in piedi e aperta.
"""
import pytest

from app.config import (
    CHIAVE_DI_RIPIEGO, ConfigurazioneInsicura, Settings, controlla_configurazione,
)


def _impostazioni(**cambiamenti):
    """Impostazioni finte, senza leggere l'ambiente vero."""
    base = {
        "database_url": "sqlite:///./prova.db",
        "secret_key": CHIAVE_DI_RIPIEGO,
        "ambiente": "sviluppo",
    }
    base.update(cambiamenti)
    return Settings(**base)


def test_in_locale_la_chiave_di_esempio_va_bene():
    """Sviluppare non deve richiedere di inventarsi una chiave ogni volta."""
    controlla_configurazione(_impostazioni())


def test_con_postgres_la_chiave_di_esempio_ferma_tutto():
    """PostgreSQL = produzione: in locale si usa SQLite."""
    with pytest.raises(ConfigurazioneInsicura) as errore:
        controlla_configurazione(_impostazioni(
            database_url="postgresql://utente:parola@host/db"))
    assert "SECRET_KEY" in str(errore.value)


def test_riconosce_anche_postgres_scritto_alla_vecchia():
    """Alcune piattaforme danno l'URL come 'postgres://': il controllo deve
    scattare lo stesso, non farsi ingannare da una lettera in meno."""
    with pytest.raises(ConfigurazioneInsicura):
        controlla_configurazione(_impostazioni(
            database_url="postgres://utente:parola@host/db"))


def test_ambiente_produzione_dichiarato_a_mano():
    """Anche senza PostgreSQL, chi dichiara AMBIENTE=produzione viene preso
    sul serio."""
    with pytest.raises(ConfigurazioneInsicura):
        controlla_configurazione(_impostazioni(ambiente="produzione"))


def test_con_una_chiave_vera_la_produzione_parte():
    controlla_configurazione(_impostazioni(
        database_url="postgresql://utente:parola@host/db",
        secret_key="una-chiave-lunga-e-casuale-che-nessuno-conosce-12345"))
