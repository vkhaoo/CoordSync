"""
La sessione nel browser: il token in un cookie che JavaScript non puo' leggere.

PERCHE'. Finora il token stava in localStorage, dove qualunque codice che gira
nella pagina puo' leggerlo — una libreria compromessa, un'estensione, uno
script infilato dentro un campo di testo. Da li' se lo porta via e lo riusa
comodamente da un'altra parte, anche a giorni di distanza.

Con **HttpOnly** il browser lo tiene per se': lo allega alle richieste ma non
lo passa a nessuno script. Non e' un lucchetto assoluto (chi riesce a far
girare del codice nella pagina puo' comunque fare richieste al posto tuo,
finche' quella pagina e' aperta), ma cambia la partita: la chiave non si puo'
piu' rubare e portare via.

IL PREZZO SONO I CSRF. Un cookie il browser lo allega DA SOLO, anche quando la
richiesta parte da un altro sito: senza contromisure, una pagina qualunque
potrebbe far partire una POST verso CoordSync con la tua sessione attaccata.
Qui si usa il "doppio invio": accanto al cookie della sessione ce n'e' uno con
un numero casuale, che il frontend rispedisce in un header; il server confronta
i due.

ATTENZIONE, imparato rompendo la produzione: il frontend NON puo' leggere quel
cookie da document.cookie, perche' le pagine stanno su un host
(coordsync.onrender.com) e il backend su un altro
(coordsync-backend.onrender.com), e un documento vede solo i cookie del PROPRIO
host. Il cookie parte comunque verso il backend — quello lo fa il browser da
solo — ma per il codice della pagina e' invisibile. Quindi il valore si
consegna nel CORPO di una risposta (GET /auth/csrf) e il frontend lo tiene in
memoria.

Il doppio invio resta valido lo stesso: un sito estraneo non puo' LEGGERE
quella risposta, perche' il CORS lascia passare solo la nostra origine. Puo'
far partire una richiesta col cookie attaccato, ma non sapra' mai cosa scrivere
nell'header.

PERCHE' SI ACCETTA ANCORA L'HEADER Authorization. Chi era gia' collegato ha in
tasca un token in localStorage: se il server smettesse di colpo di accettarlo,
il giorno della pubblicazione verrebbero buttati fuori tutti insieme. Le due
vie convivono, e nel giro di un giorno (tanto dura un token) restano solo i
cookie.
"""
import secrets

from fastapi import Request, Response

from app.config import settings

NOME_COOKIE = "coordsync_sessione"
NOME_COOKIE_CSRF = "coordsync_csrf"
HEADER_CSRF = "X-CSRF-Token"

# I metodi che non cambiano niente non hanno bisogno della protezione CSRF:
# al massimo leggono, e la risposta un sito estraneo non riesce comunque a
# vederla (glielo impedisce il CORS).
METODI_SICURI = {"GET", "HEAD", "OPTIONS"}


def imposta(risposta: Response, token: str) -> str:
    """Attacca alla risposta il cookie della sessione e quello anti-CSRF.

    Restituisce il valore anti-CSRF, perche' il frontend NON puo' leggerlo dal
    cookie: le pagine stanno su un host e il backend su un altro, e
    document.cookie mostra solo i cookie del proprio host. Va consegnato nel
    CORPO della risposta (vedi GET /auth/csrf).
    """
    durata = settings.token_durata_minuti * 60

    risposta.set_cookie(
        NOME_COOKIE, token,
        max_age=durata,
        httponly=True,      # JavaScript non lo vede: e' tutto il punto
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    # Questo invece DEVE essere leggibile: il frontend lo rilegge e lo
    # rispedisce nell'header. Non e' un segreto — serve solo a dimostrare che
    # la richiesta arriva da una pagina che i cookie li puo' leggere, cioe'
    # dalla nostra.
    prova = secrets.token_urlsafe(24)
    risposta.set_cookie(
        NOME_COOKIE_CSRF, prova,
        max_age=durata,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return prova


def solo_csrf(risposta: Response) -> str:
    """Rilascia il solo cookie anti-CSRF, senza toccare la sessione.

    Serve a chi non e' ancora entrato: anche il primo accesso e' una POST, e
    anche quella deve poter portare la sua prova.
    """
    prova = secrets.token_urlsafe(24)
    risposta.set_cookie(
        NOME_COOKIE_CSRF, prova,
        max_age=settings.token_durata_minuti * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return prova


def cancella(risposta: Response) -> None:
    """Toglie i cookie: e' l'uscita vera, quella che il browser rispetta."""
    for nome in (NOME_COOKIE, NOME_COOKIE_CSRF):
        risposta.delete_cookie(nome, path="/",
                               secure=settings.cookie_secure,
                               samesite=settings.cookie_samesite)


def token_dalla_richiesta(richiesta: Request) -> tuple[str | None, bool]:
    """Il token e da dove arriva: (token, e_arrivato_da_un_cookie).

    L'header ha la precedenza sul cookie. Serve a non incastrare chi ha
    entrambi durante il passaggio: se l'header c'e' ed e' quello che il
    frontend vecchio sta ancora mandando, e' lui a comandare.
    """
    autorizzazione = richiesta.headers.get("Authorization", "")
    if autorizzazione.lower().startswith("bearer "):
        return autorizzazione[7:].strip(), False

    cookie = richiesta.cookies.get(NOME_COOKIE)
    if cookie:
        return cookie, True

    return None, False


def csrf_valido(richiesta: Request) -> bool:
    """True se l'header anti-CSRF corrisponde al cookie leggibile.

    Il confronto usa compare_digest: confrontare stringhe segrete con == fa
    trapelare, dal tempo impiegato, quanti caratteri iniziali erano giusti.
    """
    atteso = richiesta.cookies.get(NOME_COOKIE_CSRF)
    ricevuto = richiesta.headers.get(HEADER_CSRF)
    if not atteso or not ricevuto:
        return False
    return secrets.compare_digest(atteso, ricevuto)
