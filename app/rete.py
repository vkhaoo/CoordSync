"""
Da dove arriva davvero una richiesta.

IL PROBLEMA. `request.client.host` e' l'indirizzo dell'ULTIMO pezzo che ha
parlato col server — che in produzione non e' l'utente, ma il proxy davanti
all'app (qui Cloudflare + Render). Per tutti gli utenti e' lo STESSO indirizzo.

Perche' conta: il limite ai tentativi di accesso conta anche "per indirizzo".
Con l'indirizzo del proxy, quel contatore diventa uno solo per tutti — e
bastano dieci password sbagliate, da chiunque, per bloccare l'accesso a
chiunque altro per un quarto d'ora. Non e' teoria: e' un modo banale di
mettere fuori uso il login.

LA SOLUZIONE. Cloudflare, che sta davanti a tutto, aggiunge un'intestazione
`CF-Connecting-IP` con l'indirizzo VERO del client, e la riscrive ogni volta:
un client non puo' falsificarla, perche' passa comunque da Cloudflare. La si
usa per prima. In mancanza (altri hosting, o prove in locale) si ripiega su
`X-Forwarded-For` e infine sull'indirizzo diretto.
"""
from fastapi import Request


def ip_reale(richiesta: Request) -> str:
    # Cloudflare: l'indirizzo vero, non falsificabile passando da loro.
    cf = richiesta.headers.get("CF-Connecting-IP")
    if cf:
        return cf.strip()

    # Catena di proxy generica: il primo della lista e' il client originale.
    # (Ci si fida perche' si e' dietro un proxy noto; senza proxy questa
    # intestazione non c'e'.)
    inoltrato = richiesta.headers.get("X-Forwarded-For")
    if inoltrato:
        return inoltrato.split(",")[0].strip()

    # Nessun proxy: l'indirizzo diretto e' quello vero (sviluppo locale).
    return richiesta.client.host if richiesta.client else "sconosciuto"
