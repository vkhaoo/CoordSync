"""
Configurazione condivisa dei test (pytest la carica in automatico).

Punto chiave: i test NON toccano il database vero. Ne usano uno tutto loro,
svuotato prima di ogni test, cosi' ognuno parte pulito e non dipende da quelli
che l'hanno preceduto.
"""
import os
import pathlib
import tempfile

# Il database dei test sta FUORI dalla cartella del progetto, in una cartella
# temporanea di sistema, e porta nel nome il NUMERO DEL PROCESSO.
#
# Perche' fuori dal progetto: il progetto vive dentro OneDrive, che sincronizza
# in continuazione e teneva occupato il file proprio mentre i test lo usavano.
#
# Perche' il numero del processo: prima il nome era sempre lo stesso e il file
# si provava a cancellarlo all'inizio. Su Windows quella cancellazione a volte
# non riesce, perche' il file risulta ancora in uso, e l'errore veniva
# ignorato: si ripartiva quindi da un file VECCHIO, con lo schema di giorni
# prima, perche' create_all aggiunge le tabelle che mancano ma non tocca quelle
# che trova gia' li'. Ne uscivano fallimenti che cambiavano a ogni esecuzione e
# sembravano venire dal codice in prova. Con un nome nuovo ogni volta, il
# problema non puo' proprio presentarsi.
#
# Deve stare PRIMA di importare l'app: e' cosi' che la si dirotta sul database
# di test invece che su quello vero.
_DB_TEST = pathlib.Path(tempfile.gettempdir()) / f"coordsync_test_{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_TEST.as_posix()}"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _schema_dei_test():
    """Le tabelle si creano UNA volta per tutta la sessione di test."""
    Base.metadata.create_all(bind=engine)
    yield

    # Finito: si porta via il proprio file, e gia' che c'e' anche quelli
    # lasciati indietro da esecuzioni interrotte a meta'. Senza questa
    # pulizia la cartella temporanea si riempirebbe di database abbandonati.
    engine.dispose()
    for avanzo in _DB_TEST.parent.glob("coordsync_test_*.db"):
        try:
            avanzo.unlink()
        except OSError:
            pass   # e' di un'esecuzione ancora viva, o Windows lo tiene: pazienza


@pytest.fixture(autouse=True)
def _database_pulito(_schema_dei_test):
    """Prima di OGNI test: tabelle vuote, ma lo schema resta in piedi.

    Si SVUOTANO le tabelle invece di cancellare e ricreare il file, perche' su
    Windows il file non si lascia cancellare finche' risulta in uso.

    Durante lo svuotamento i vincoli si SPENGONO. Andare in ordine inverso non
    basterebbe: sorted_tables risolve le dipendenze, ma quando fra le tabelle
    c'e' un anello l'ordine che restituisce non e' garantito. Basta che una
    tabella figlia finisca dopo la madre e la cancellazione si ferma a meta'
    con "FOREIGN KEY constraint failed", lasciando qualche tabella piena.
    Qui l'integrita' non protegge niente: si sta buttando via TUTTO, non si
    stanno modificando dei dati veri.

    'autouse=True' = si applica da solo a tutti i test, senza chiederlo.
    """
    from app import limiti
    # Il conteggio dei tentativi di accesso sta in memoria e sopravviverebbe
    # da un test all'altro: azzerato qui, cosi' i test non si fanno inciampare.
    limiti.azzera_tutto()

    e_sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as connessione:
        # Il PRAGMA va dato FUORI da una transazione, altrimenti SQLite lo
        # ignora in silenzio: per questo qui si usa connect() e non begin().
        if e_sqlite:
            connessione.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for tabella in reversed(Base.metadata.sorted_tables):
            connessione.execute(tabella.delete())
        connessione.commit()
        if e_sqlite:
            # Riacceso subito: il test che sta per partire deve trovare i
            # vincoli attivi, altrimenti non verificherebbe piu' niente.
            connessione.exec_driver_sql("PRAGMA foreign_keys=ON")
    yield


@pytest.fixture()
def client():
    """Un client per parlare con l'app nei test, come farebbe un browser."""
    with TestClient(app) as c:
        yield c


# --- piccoli aiutanti riutilizzabili dai test ---

def registra(client, azienda, nome, email, password="password1"):
    """Crea un account E la sua prima azienda, e restituisce gli header pronti.

    Da quando iscriversi e aprire un'azienda sono due gesti separati servono
    due chiamate. Restano insieme qui perche' e' lo scenario di partenza di
    quasi tutti i test: "c'e' un'azienda con dentro un amministratore".
    """
    r = client.post("/auth/register", json={
        "nome": nome, "email": email, "password": password,
    })
    token = r.json()["access_token"]
    creata = client.post("/auth/aziende", json={"nome": azienda},
                         headers={"Authorization": f"Bearer {token}"})
    # Il token nuovo punta gia' all'azienda appena creata.
    return {"Authorization": f"Bearer {creata.json()['access_token']}"}


def registra_solo_account(client, nome, email, password="password1"):
    """Un account senza nessuna azienda: appena iscritto, non appartiene a
    niente. E' lo stato in cui si apre la schermata di scelta."""
    r = client.post("/auth/register", json={
        "nome": nome, "email": email, "password": password,
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
