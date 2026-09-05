"""
Configurazione dell'app.

Legge le impostazioni dalle variabili d'ambiente (file .env in locale,
o le variabili impostate sulla piattaforma di hosting in produzione).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


# La chiave che c'e' quando nessuno ne ha messa una. E' scritta qui, quindi e'
# pubblica: chiunque legga il codice su GitHub potrebbe firmarsi dei token e
# entrare come chi vuole. Va bene solo per sviluppare in locale.
CHIAVE_DI_RIPIEGO = "CAMBIAMI-in-produzione-con-una-chiave-lunga-e-casuale"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. In locale: SQLite. In produzione: l'URL di PostgreSQL,
    # che la piattaforma di hosting fornisce come variabile d'ambiente.
    database_url: str = "sqlite:///./gestione_lavori.db"

    # Chiave segreta per firmare i token JWT. In produzione DEVE essere
    # impostata come variabile d'ambiente (lunga e casuale).
    # Vedi controlla_configurazione(): con questo valore l'app in produzione
    # si rifiuta di partire.
    secret_key: str = CHIAVE_DI_RIPIEGO
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

    # --- Sapere quando l'app si rompe ---
    # Chiave di Sentry. VUOTA = nessun avviso spedito a nessuno: e' cosi' che
    # deve restare in locale e nei test.
    sentry_dsn: str = ""
    # Serve solo a distinguere gli errori veri da quelli delle prove.
    ambiente: str = "sviluppo"

    # Chiave per far partire l'invio dei promemoria dall'esterno (es. una
    # GitHub Action schedulata). Finche' resta VUOTA l'endpoint rifiuta di
    # funzionare: meglio inerte che aperto a chiunque.
    chiave_promemoria: str = ""

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


class ConfigurazioneInsicura(RuntimeError):
    """L'app e' configurata in modo che non si puo' accettare in produzione."""


def controlla_configurazione(impostazioni: Settings = None) -> None:
    """Si arrabbia all'avvio se la produzione gira con la chiave di ripiego.

    Perche' fermare tutto invece di scrivere un avviso nei log: con quella
    chiave chiunque puo' fabbricarsi un token valido per qualsiasi account, e
    un avviso nei log non lo legge nessuno finche' non e' troppo tardi. Un
    deploy che fallisce si nota subito; un'app aperta a chiunque no.

    "Siamo in produzione" si riconosce dal database PostgreSQL (in locale e'
    SQLite) oppure da AMBIENTE impostato a mano. Non si usa solo AMBIENTE
    perche' e' facoltativa: se qualcuno dimentica di impostarla, il controllo
    si spegnerebbe proprio dove serve.
    """
    imp = impostazioni or settings
    in_produzione = (
        imp.db_url_normalizzato.startswith("postgresql")
        or imp.ambiente.lower().startswith("produzione")
    )
    if in_produzione and imp.secret_key == CHIAVE_DI_RIPIEGO:
        raise ConfigurazioneInsicura(
            "SECRET_KEY non e' impostata: l'app userebbe la chiave di esempio "
            "scritta nel codice, e chiunque potrebbe fabbricarsi un accesso. "
            "Imposta SECRET_KEY (lunga e casuale) fra le variabili d'ambiente."
        )
