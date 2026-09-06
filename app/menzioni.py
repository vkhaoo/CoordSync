"""
Le menzioni dentro i commenti: scrivere @Mario per tirare dentro Mario.

COME SI RICONOSCE UN NOME. Non con un'espressione regolare che prende la
parola dopo la chiocciola: i nomi veri hanno spazi ("Marco Rossi"), accenti e
apostrofi, e una regola generica sbaglierebbe su tutti e tre. Si fa il
contrario: si parte dall'elenco delle persone e si guarda quali compaiono nel
testo preceduti dalla chiocciola. L'elenco e' corto (i colleghi di un'azienda)
e cosi' non si puo' inventare una menzione per qualcuno che non esiste.

Si accetta il nome INTERO ("@Marco Rossi") e anche il solo nome di battesimo
("@Marco"), ma quest'ultimo SOLO se in azienda ce n'e' uno solo con quel nome.
Con due Marco un avviso a caso sarebbe peggio di nessun avviso: chi scrive
crederebbe di aver chiamato qualcuno, e quel qualcuno non lo saprebbe mai.

I nomi si provano dal PIU' LUNGO al piu' corto: senza, in un'azienda con
"Marco" e "Marco Rossi", scrivere "@Marco Rossi" chiamerebbe Marco e basta.

UNA MENZIONE NON APRE NIENTE. Chi viene nominato riceve l'avviso solo se quel
lavoro (o quella macchina) lo vedeva gia': altrimenti bastera' scrivere il
nome di un collega di un altro reparto per fargli sapere che esiste un lavoro
riservato, e per farglielo aprire dalla campanella. Il controllo lo fa chi
chiama, passando solo i candidati che possono vedere la cosa.
"""
import unicodedata


def _normalizza(testo: str) -> str:
    """Minuscolo e senza accenti, per confrontare i nomi.

    Serve perche' chi scrive di fretta digita "@nicolo" invece di "@Nicolò":
    senza questo, la menzione non scatterebbe e nessuno saprebbe perche'.
    """
    scomposto = unicodedata.normalize("NFD", testo.lower())
    return "".join(c for c in scomposto if unicodedata.category(c) != "Mn")


def trova_menzionati(testo: str, candidati) -> list:
    """Le persone nominate nel testo, fra quelle passate.

    `candidati` sono gia' filtrati da chi chiama: devono essere SOLO le
    persone che quella cosa la possono gia' vedere.
    """
    if not testo or "@" not in testo:
        return []

    piatto = _normalizza(testo)

    # Ogni forma scrivibile -> la persona. Il nome di battesimo entra solo se
    # e' di una persona sola.
    per_forma: dict[str, object] = {}
    quanti_col_nome: dict[str, int] = {}
    for persona in candidati:
        primo = _normalizza((persona.nome or "").split(" ")[0])
        if primo:
            quanti_col_nome[primo] = quanti_col_nome.get(primo, 0) + 1

    for persona in candidati:
        intero = _normalizza(persona.nome or "")
        if not intero:
            continue
        per_forma[intero] = persona
        primo = intero.split(" ")[0]
        if quanti_col_nome.get(primo, 0) == 1:
            per_forma.setdefault(primo, persona)

    trovate = []
    gia_viste = set()
    # Dal piu' lungo al piu' corto: "@Marco Rossi" deve valere Marco Rossi,
    # non Marco.
    for forma in sorted(per_forma, key=len, reverse=True):
        if f"@{forma}" in piatto:
            persona = per_forma[forma]
            if persona.id not in gia_viste:
                gia_viste.add(persona.id)
                trovate.append(persona)
            # Tolgo quello che ho appena riconosciuto, cosi' la forma piu'
            # corta non lo ripesca dentro quella piu' lunga.
            piatto = piatto.replace(f"@{forma}", " ")
    return trovate


def colleghi_che_possono_vedere(db, current, *, lavoro_id=None, macchina_id=None) -> list:
    """I colleghi dell'azienda attiva a cui quella cosa e' gia' visibile.

    E' il filtro che rende una menzione innocua: si parte da chi lavora qui,
    e si tiene solo chi quel lavoro (o quella macchina) lo vedeva gia' per
    conto suo. Scrivere il nome di qualcuno non gli apre niente.

    Se stessi esclusi: nominarsi da soli non deve far suonare la propria
    campanella.
    """
    from app.appartenenze import condizione_membro
    from app.models.utente import Utente
    from app.visibilita import vede_lavoro, vede_macchina

    org = current.org_attiva_id
    colleghi = (
        db.query(Utente)
        .filter(condizione_membro(org), Utente.id != current.id)
        .all()
    )

    if lavoro_id is not None:
        return [u for u in colleghi if vede_lavoro(db, u, org, lavoro_id)]
    if macchina_id is not None:
        return [u for u in colleghi if vede_macchina(db, u, org, macchina_id)]
    return []
