"""
Configurazione dell'app.

Legge le impostazioni dalle variabili d'ambiente (file .env in locale,
o le variabili impostate sulla piattaforma di hosting in produzione).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. In locale: SQLite. In produzione: l'URL di PostgreSQL,
    # che la piattaforma di hosting fornisce come variabile d'ambiente.
    database_url: str = "sqlite:///./gestione_lavori.db"

    # Chiave segreta per firmare i token JWT. In produzione DEVE essere
    # impostata come variabile d'ambiente (lunga e casuale).
    secret_key: str = "CAMBIAMI-in-produzione-con-una-chiave-lunga-e-casuale"
    token_durata_minuti: int = 60 * 24  # 24 ore

    # Origini permesse per il CORS (chi puo' chiamare l'API dal browser).
    # In locale: il server di sviluppo. In produzione: l'indirizzo del frontend.
    # Formato: indirizzi separati da virgola.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Indirizzo pubblico di questo backend (per costruire i link nelle email).
    # In produzione: l'URL del backend su Render.
    base_url: str = "http://127.0.0.1:8000"

    # Indirizzo del frontend (per i link che portano l'utente su una PAGINA,
    # es. il reset password dove digita la nuova password).
    frontend_url: str = "http://localhost:5173"

    # --- Invio email ---
    # Mittente (deve essere un indirizzo/dominio VERIFICATO presso il provider).
    mittente_email: str = ""
    mittente_nome: str = "CoordSync"

    # Opzione A (consigliata su hosting che bloccano SMTP, es. Render free):
    # API HTTP di Brevo. Usa la porta 443 (sempre aperta). Basta la API key.
    brevo_api_key: str = ""

    # Opzione B: SMTP classico. Funziona dove le porte SMTP non sono bloccate
    # (piani a pagamento, altri hosting, sviluppo locale).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Se nessuna delle due e' configurata: le email vengono stampate nei log.

    @property
    def lista_cors(self) -> list[str]:
        """Trasforma la stringa 'a,b,c' nella lista ['a','b','c']."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_url_normalizzato(self) -> str:
        """Alcune piattaforme danno l'URL come 'postgres://...', ma SQLAlchemy
        vuole 'postgresql://...'. Correggo qui, cosi' funziona ovunque."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()
