"""
Configurazione dell'app.

Legge le impostazioni dalle variabili d'ambiente (file .env).
Perche' cosi': i segreti (URL del database, chiave dei token) NON stanno nel
codice, ma in un file .env che resta fuori da git. Standard professionale.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Valore di default se .env non c'e': SQLite locale.
    database_url: str = "sqlite:///./gestione_lavori.db"

    # Chiave segreta per FIRMARE i token JWT. In produzione DEVE stare nel .env
    # ed essere lunga e casuale: chi la conosce puo' falsificare i token.
    secret_key: str = "CAMBIAMI-in-produzione-con-una-chiave-lunga-e-casuale"

    # Per quanto tempo resta valido un token dopo il login (in minuti).
    token_durata_minuti: int = 60 * 24  # 24 ore


settings = Settings()
