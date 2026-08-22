"""
Invio notifiche email. Tre modi, in ordine di preferenza:

1) API HTTP di Brevo (se brevo_api_key e' configurata): usa la porta 443 (HTTPS),
   sempre aperta anche dove le porte SMTP sono bloccate (es. Render free tier).
2) SMTP (se smtp_host e' configurato): lo standard classico, dove le porte
   SMTP non sono bloccate.
3) Nessuno dei due (sviluppo): stampa nei log.
"""
import json
import smtplib
import logging
import urllib.request
import urllib.error
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("coordsync.email")


def invia_email(destinatario: str, oggetto: str, corpo: str) -> None:
    if settings.brevo_api_key and settings.mittente_email:
        _invia_via_brevo_api(destinatario, oggetto, corpo)
    elif settings.smtp_host:
        _invia_via_smtp(destinatario, oggetto, corpo)
    else:
        _stampa_nei_log(destinatario, oggetto, corpo)


def _stampa_nei_log(destinatario, oggetto, corpo):
    logger.warning(
        "\n===== EMAIL (sviluppo, non spedita) =====\n"
        f"A: {destinatario}\nOggetto: {oggetto}\n{corpo}\n"
        "=========================================\n"
    )


def _invia_via_brevo_api(destinatario, oggetto, corpo):
    """Spedisce con una chiamata HTTP all'API di Brevo (porta 443, mai bloccata)."""
    payload = {
        "sender": {"name": settings.mittente_nome, "email": settings.mittente_email},
        "to": [{"email": destinatario}],
        "subject": oggetto,
        "textContent": corpo,
    }
    richiesta = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": settings.brevo_api_key,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=15) as risposta:
            risposta.read()
        logger.info(f"Email inviata (Brevo API) a {destinatario}")
    except urllib.error.HTTPError as e:
        # errore dal servizio (es. mittente non verificato, api key errata)
        logger.error(f"Invio email fallito (Brevo API) verso {destinatario}: "
                     f"{e.code} {e.read().decode('utf-8', 'ignore')}")
    except Exception as e:
        logger.error(f"Invio email fallito (Brevo API) verso {destinatario}: {e}")


def _invia_via_smtp(destinatario, oggetto, corpo):
    """Spedisce via SMTP (dove le porte non sono bloccate)."""
    msg = EmailMessage()
    msg["From"] = f"{settings.mittente_nome} <{settings.mittente_email}>"
    msg["To"] = destinatario
    msg["Subject"] = oggetto
    msg.set_content(corpo)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info(f"Email inviata (SMTP) a {destinatario}")
    except Exception as e:
        logger.error(f"Invio email fallito (SMTP) verso {destinatario}: {e}")
