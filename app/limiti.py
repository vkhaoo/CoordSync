"""
Limite ai tentativi di accesso, contro chi prova le password a raffica.

Come funziona: si tiene il conto dei fallimenti recenti, sia per EMAIL sia per
INDIRIZZO di provenienza. Se uno dei due sfora, l'accesso viene rifiutato per un
po'. Un accesso riuscito azzera il conto.

Perche' due contatori e non uno: contare solo per email non ferma chi prova la
stessa password su mille indirizzi email diversi; contare solo per indirizzo di
rete non ferma chi cambia rete. Insieme coprono entrambi i casi.

LIMITE NOTO, da sapere: il conteggio sta in memoria, quindi si azzera quando il
processo riparte — e sul piano gratuito di Render il servizio si addormenta
dopo 15 minuti. Rallenta un attacco, non lo rende impossibile. Per una difesa
che sopravvive ai riavvii servirebbe tenerlo nel database, che pero' significa
scrivere a ogni tentativo fallito: sproporzionato finche' l'app ha questa
dimensione. Scritto qui perche' non venga scambiato per piu' di quello che e'.
"""
from datetime import datetime, timedelta, timezone

# Quanti fallimenti si tollerano, e in quanto tempo.
MAX_TENTATIVI = 10
FINESTRA = timedelta(minutes=15)

# chiave -> lista dei momenti in cui si e' fallito
_fallimenti: dict[str, list[datetime]] = {}


def _recenti(chiave: str) -> list[datetime]:
    """I fallimenti ancora dentro la finestra, buttando via i vecchi."""
    adesso = datetime.now(timezone.utc)
    rimasti = [q for q in _fallimenti.get(chiave, []) if adesso - q < FINESTRA]
    if rimasti:
        _fallimenti[chiave] = rimasti
    else:
        _fallimenti.pop(chiave, None)
    return rimasti


def _chiavi(email: str, ip: str) -> tuple[str, str]:
    return f"email:{email.strip().lower()}", f"ip:{ip}"


def attesa_richiesta(email: str, ip: str) -> int | None:
    """Quanti secondi bisogna aspettare, o None se si puo' provare.

    Il tempo di attesa e' quello del contatore piu' "carico": si aspetta finche'
    il fallimento piu' vecchio non esce dalla finestra.
    """
    adesso = datetime.now(timezone.utc)
    attese = []
    for chiave in _chiavi(email, ip):
        recenti = _recenti(chiave)
        if len(recenti) >= MAX_TENTATIVI:
            libero_fra = (min(recenti) + FINESTRA) - adesso
            attese.append(max(1, int(libero_fra.total_seconds())))
    return max(attese) if attese else None


def registra_fallimento(email: str, ip: str) -> None:
    adesso = datetime.now(timezone.utc)
    for chiave in _chiavi(email, ip):
        _fallimenti.setdefault(chiave, []).append(adesso)


def azzera(email: str, ip: str) -> None:
    """Dopo un accesso riuscito: chi ha dimostrato di essere lui riparte pulito."""
    for chiave in _chiavi(email, ip):
        _fallimenti.pop(chiave, None)


def azzera_tutto() -> None:
    """Serve ai test, per non farli inciampare l'uno nell'altro."""
    _fallimenti.clear()
    _azioni.clear()


# --- Freno generico per le azioni "costose verso l'esterno" ----------------
# Il contatore sopra conta i FALLIMENTI (e li azzera quando si entra). Qui
# invece si contano le RICHIESTE, riuscite o no: serve per le cose che mandano
# email (registrazione, reset, reinvio verifica, cambio indirizzo). Senza un
# freno, quegli endpoint sono un modo gratis per bombardare di email un
# indirizzo qualunque e per bruciare il credito del servizio di invio.
_azioni: dict[str, list[datetime]] = {}


def troppo_spesso(chiave: str, massimo: int, finestra: timedelta) -> bool:
    """Segna un'azione e dice se se ne sono fatte troppe di recente.

    A differenza dei tentativi di accesso non c'e' un "azzera": queste azioni
    non hanno un "successo" che pulisce il conto, si diradano da sole col
    passare del tempo.
    """
    adesso = datetime.now(timezone.utc)
    recenti = [q for q in _azioni.get(chiave, []) if adesso - q < finestra]
    recenti.append(adesso)
    _azioni[chiave] = recenti
    return len(recenti) > massimo
