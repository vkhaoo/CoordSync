"""
Invio notifiche email.

In sviluppo NON spedisce davvero: stampa nei log il contenuto (utile per testare
il flusso senza un servizio email). In produzione, qui si collega un servizio
reale (SendGrid, Postmark, SMTP...) senza cambiare il resto del codice.
"""
import logging

logger = logging.getLogger("coordsync.email")


def invia_email(destinatario: str, oggetto: str, corpo: str) -> None:
    # --- Sviluppo: stampo invece di spedire ---
    logger.warning(
        "\n===== EMAIL (sviluppo, non spedita) =====\n"
        f"A: {destinatario}\nOggetto: {oggetto}\n{corpo}\n"
        "=========================================\n"
    )
    # --- Produzione (futuro): qui la chiamata al servizio email reale ---
