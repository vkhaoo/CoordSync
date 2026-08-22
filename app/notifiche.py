"""
Invio notifiche email.

- Se le credenziali SMTP NON sono configurate (sviluppo): stampa nei log
  (utile per testare senza un servizio email).
- Se sono configurate (produzione): spedisce davvero via SMTP.

SMTP e' uno standard: questo codice funziona con qualsiasi provider
(Brevo, Resend, SendGrid...) cambiando solo le variabili d'ambiente.
"""
import smtplib
import logging
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("coordsync.email")


def invia_email(destinatario: str, oggetto: str, corpo: str) -> None:
    # --- Sviluppo: nessun SMTP configurato -> stampo invece di spedire ---
    if not settings.smtp_host:
        logger.warning(
            "\n===== EMAIL (sviluppo, non spedita) =====\n"
            f"A: {destinatario}\nOggetto: {oggetto}\n{corpo}\n"
            "=========================================\n"
        )
        return

    # --- Produzione: costruisco e spedisco l'email via SMTP ---
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = destinatario
    msg["Subject"] = oggetto
    msg.set_content(corpo)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()   # cifra la connessione
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info(f"Email inviata a {destinatario}")
    except Exception as e:
        # Non faccio fallire l'operazione dell'utente se l'email non parte:
        # registro l'errore. (Es. la registrazione va a buon fine comunque.)
        logger.error(f"Invio email fallito verso {destinatario}: {e}")
