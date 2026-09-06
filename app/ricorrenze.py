"""
Le ripetizioni degli impegni in agenda: la manutenzione di ogni primo lunedi',
la riunione di squadra del martedi'.

DUE MODI DI FARLO, e la scelta conta.

Il primo e' salvare una REGOLA ("ogni due settimane") su un impegno solo, e
calcolare le date al volo quando si disegna il calendario. E' elegante finche'
non serve spostare una singola occorrenza, o annullarne una, o sapere se il
promemoria di quella di giovedi' e' gia' partito: a quel punto servono le
eccezioni alla regola, e ogni pezzo dell'app che tocca un impegno va insegnato
a capirle.

Il secondo — quello scelto qui — e' GENERARE gli impegni veri, uno per data,
legati da un numero di serie. Costa qualche riga in piu' nel database, ma ogni
occorrenza e' una cosa vera: si sposta da sola, si cancella da sola, ha il suo
promemoria, e tutto il resto dell'app continua a funzionare senza sapere che
esistono le ripetizioni.

IL TETTO NON E' UN DETTAGLIO. Una ripetizione "ogni settimana" senza fine
genererebbe righe finche' il database non si stufa. Si pretende una data di
fine e si taglia comunque a MASSIMO occorrenze: chi ne vuole di piu' rifa'
l'operazione l'anno dopo, che e' meno peggio di un'agenda ingestibile.
"""
import calendar
from datetime import datetime, timedelta

# Ogni quanto si ripete, in giorni. Il mensile e' a parte: i mesi non hanno
# tutti la stessa lunghezza, quindi non si puo' esprimere in giorni.
PASSI_IN_GIORNI = {
    "settimanale": 7,
    "quindicinale": 14,
    "quattro_settimane": 28,
}
RIPETIZIONI = tuple(PASSI_IN_GIORNI) + ("mensile",)

# Quante occorrenze al massimo, comunque vada.
MASSIMO = 104   # due anni di appuntamenti settimanali


def _stesso_giorno_del_mese_dopo(quando: datetime, quanti_mesi: int) -> datetime:
    """La stessa data e ora, spostata avanti di N mesi.

    Il 31 in un mese che non ce l'ha diventa l'ULTIMO giorno di quel mese, non
    salta. Saltarlo farebbe sparire una manutenzione senza dire niente a
    nessuno; spostarla di un giorno si vede, e chi la guarda capisce.
    """
    mese = quando.month - 1 + quanti_mesi
    anno = quando.year + mese // 12
    mese = mese % 12 + 1
    giorno = min(quando.day, calendar.monthrange(anno, mese)[1])
    return quando.replace(year=anno, month=mese, day=giorno)


def date_successive(inizio: datetime, ripeti: str, fino_a: datetime) -> list[datetime]:
    """Le date DOPO la prima, fino alla data indicata compresa.

    La prima non c'e' dentro: quella e' l'impegno che si sta creando, e chi
    chiama ce l'ha gia'.
    """
    if ripeti not in RIPETIZIONI or fino_a <= inizio:
        return []

    date = []
    passo = 1
    while len(date) < MASSIMO:
        if ripeti == "mensile":
            prossima = _stesso_giorno_del_mese_dopo(inizio, passo)
        else:
            prossima = inizio + timedelta(days=PASSI_IN_GIORNI[ripeti] * passo)
        if prossima > fino_a:
            break
        date.append(prossima)
        passo += 1
    return date
