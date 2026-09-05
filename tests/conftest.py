"""
Configurazione condivisa dei test (pytest la carica in automatico).

Punto chiave: i test NON toccano il database vero. Ne usano uno tutto loro,
ricreato da zero prima di ogni test, cosi' ognuno parte pulito e non dipende
da quelli che l'hanno preceduto.
"""
import os
import pathlib
import tempfile

# Il database dei test sta FUORI dalla cartella del progetto, in una cartella
# temporanea di sistema.
#
# Perche': il progetto vive dentro OneDrive, che sincronizza in continuazione.
# Con il file dentro la cartella sincronizzata, OneDrive lo teneva occupato
# proprio mentre i test lo ricreavano, e ne uscivano errori che cambiavano a
# ogni esecuzione e non c'entravano niente col codice in prova.
#
# Deve stare PRIMA di importare l'app: dirotta l'app sul database di test.
_DB_TEST = pathlib.Path(tempfile.gettempdir()) / "coordsync_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_TEST.as_posix()}"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _schema_dei_test():
    """Le tabelle si creano UNA volta per tutta la sessione di test."""
    engine.dispose()
    try:
        _DB_TEST.unlink(missing_ok=True)
    except OSError:
        # Su Windows il file puo' risultare ancora in uso per un istante dopo
        # un'esecuzione precedente. Non e' grave: create_all aggiunge quello
        # che manca e le tabelle vengono comunque svuotate prima di ogni test.
        pass
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _database_pulito(_schema_dei_test):
    """Prima di OGNI test: tabelle vuote, ma lo schema resta in piedi.

    Si SVUOTANO le tabelle invece di cancellarle e ricrearle. Due motivi:

    - da quando SQLite applica davvero le chiavi esterne, cancellare le tabelle
      a una a una falliva a meta' con "FOREIGN KEY constraint failed",
      lasciandone qualcuna viva e qualcuna no. Da li' partiva una cascata di
      errori ("no such table: utenti") che cambiavano a ogni esecuzione e non
      c'entravano niente col codice in prova;
    - buttare via il file non funziona su Windows, che non lo lascia cancellare
      finche' risulta in uso.

    L'ordine inverso e' quello che serve: sorted_tables mette prima i genitori,
    quindi al contrario si svuotano prima i figli e nessun vincolo si lamenta.

    'autouse=True' = si applica da solo a tutti i test, senza chiederlo.
    """
    from app import limiti
    # Il conteggio dei tentativi di accesso sta in memoria e sopravviverebbe
    # da un test all'altro: azzerato qui, cosi' i test non si fanno inciampare.
    limiti.azzera_tutto()

    with engine.begin() as connessione:
        for tabella in reversed(Base.metadata.sorted_tables):
            connessione.execute(tabella.delete())
    yield


@pytest.fixture()
def client():
    """Un client per parlare con l'app nei test, come farebbe un browser."""
    with TestClient(app) as c:
        yield c


# --- piccoli aiutanti riutilizzabili dai test ---

def registra(client, azienda, nome, email, password="password1"):
    """Registra un'azienda+admin e restituisce gli header con il token pronti."""
    r = client.post("/auth/register", json={
        "nome_azienda": azienda, "nome": nome, "email": email, "password": password,
    })
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
