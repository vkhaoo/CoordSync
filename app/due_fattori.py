"""
Secondo fattore (2FA): il codice che cambia ogni 30 secondi.

A cosa serve: la password puo' finire in mano a qualcuno — riusata su un altro
sito, letta da sopra la spalla, scritta su un foglietto. Con il secondo fattore
non basta piu' saperla: serve anche il telefono su cui gira l'app che genera i
codici.

E' **facoltativo, e spento di default**. Per chi non lo accende l'accesso resta
identico a prima, ed e' voluto: imporlo a una squadra che lavora sul campo, con
i guanti e il telefono in tasca, vorrebbe dire farsi odiare.

Lo standard e' TOTP (RFC 6238), lo stesso di Google Authenticator, Aegis, 1Password
e compagnia: si usa una libreria collaudata invece di riscriverlo, perche' un
errore qui non si vede finche' non e' troppo tardi.

I CODICI DI RECUPERO sono la parte che di solito si dimentica: se il telefono
si perde o si rompe, senza di quelli si resta chiusi fuori dal proprio account
per sempre. Se ne generano otto all'attivazione, si mostrano UNA volta e si
salvano solo come impronte, esattamente come le password. Ognuno vale una volta
sola.
"""
import secrets

import pyotp

from app.security import hash_password, verifica_password

QUANTI_RECUPERO = 8
# Tolleranza di un intervallo (30 secondi) prima e dopo: gli orologi dei
# telefoni non sono mai perfettamente allineati, e senza questo margine chi ha
# il telefono indietro di qualche secondo non entrerebbe mai.
FINESTRA = 1


def nuovo_segreto() -> str:
    """Il segreto condiviso fra l'app e il telefono."""
    return pyotp.random_base32()


def uri_configurazione(segreto: str, email: str) -> str:
    """L'indirizzo otpauth:// che le app di autenticazione sanno leggere.

    Sul telefono, toccandolo, si apre direttamente l'app dei codici. Da
    computer si legge il segreto e lo si scrive a mano.
    """
    return pyotp.TOTP(segreto).provisioning_uri(name=email, issuer_name="CoordSync")


def codice_valido(segreto: str, codice: str) -> bool:
    """True se il codice di sei cifre e' quello giusto in questo momento."""
    if not segreto or not codice:
        return False
    return pyotp.TOTP(segreto).verify(codice.strip().replace(" ", ""),
                                      valid_window=FINESTRA)


def genera_codici_recupero() -> list[str]:
    """Otto codici usa e getta, da stampare o conservare da qualche parte.

    Formato leggibile a voce e senza caratteri che si confondono: sono fatti
    per essere copiati a mano su un foglio, non per essere belli.
    """
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # niente I, O, 0, 1
    codici = []
    for _ in range(QUANTI_RECUPERO):
        pezzi = ["".join(secrets.choice(alfabeto) for _ in range(4)) for _ in range(2)]
        codici.append("-".join(pezzi))
    return codici


def impronte(codici: list[str]) -> list[str]:
    """Le impronte da salvare al posto dei codici veri.

    Stesso trattamento delle password: se il database finisse in mano a
    qualcuno, i codici di recupero non devono essere leggibili."""
    return [hash_password(c) for c in codici]


def consuma_codice_recupero(codici_hash: list[str], tentativo: str) -> list[str] | None:
    """Verifica un codice di recupero e lo BRUCIA.

    Restituisce la lista aggiornata (senza quello usato) se il codice era
    buono, None se non lo era. Un codice di recupero vale una volta sola: se
    restasse valido, chi lo ha letto una volta entrerebbe per sempre.
    """
    pulito = tentativo.strip().upper().replace(" ", "")
    for impronta in codici_hash:
        if verifica_password(pulito, impronta):
            return [h for h in codici_hash if h != impronta]
    return None
