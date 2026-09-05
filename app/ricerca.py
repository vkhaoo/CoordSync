"""
Ricerca testuale, tenuta in un posto solo perche' la usano piu' router.

La ricerca si fa nel DATABASE e non nel browser: uno storico di macchina cresce
per anni, e scaricarlo tutto per poi filtrarlo sarebbe uno spreco che peggiora
col tempo. Meglio chiedere al database solo quello che serve.
"""
from sqlalchemy import or_


def condizione_testo(colonne, testo: str | None):
    """Condizione "almeno una di queste colonne contiene il testo cercato",
    senza distinzione fra maiuscole e minuscole.

    Restituisce None se non c'e' niente da cercare, cosi' chi chiama puo'
    semplicemente non applicare alcun filtro.

    I caratteri jolly di LIKE vengono neutralizzati: senza, cercare "50%"
    restituirebbe tutto, e un "_" farebbe da singolo carattere qualsiasi.
    """
    if not testo or not testo.strip():
        return None

    termine = (
        testo.strip()
        .replace("\\", "\\\\")
        .replace("%", "\%")
        .replace("_", "\_")
    )
    schema = f"%{termine}%"
    # ilike e' portabile: su PostgreSQL e' nativo, su SQLite SQLAlchemy lo
    # traduce in un confronto fra minuscole.
    return or_(*[colonna.ilike(schema, escape="\\") for colonna in colonne])
