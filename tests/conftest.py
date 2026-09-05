"""
Configurazione condivisa dei test (pytest la carica in automatico).

Punto chiave: i test NON toccano il database vero. Usano un database
di test separato (test.db), creato pulito PRIMA di ogni test e buttato DOPO.
Cosi' ogni test parte da zero e non dipende dagli altri.
"""
import os

# Deve stare PRIMA di importare l'app: dirotta l'app su un DB di test.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def _database_pulito():
    """Prima di OGNI test: crea le tabelle vuote. Dopo: le cancella.
    'autouse=True' = si applica da solo a tutti i test, senza chiederlo."""
    from app import limiti
    # Il conteggio dei tentativi di accesso sta in memoria e sopravviverebbe
    # da un test all'altro: azzerato qui, cosi' i test non si fanno inciampare.
    limiti.azzera_tutto()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


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
