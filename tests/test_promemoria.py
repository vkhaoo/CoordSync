"""
Invio dei promemoria dell'agenda.

Punti da proteggere: senza chiave configurata l'endpoint deve restare inerte
(non e' una porta aperta a chiunque), e un promemoria non deve partire due
volte ne' troppo presto.
"""
from datetime import datetime, timedelta

import pytest

from app.config import settings
from app.models.impegno import Impegno
from tests.conftest import registra

CHIAVE = "chiave-di-prova-lunga-abbastanza"


@pytest.fixture()
def con_chiave():
    """Accende l'invio per la durata del test, poi rimette com'era."""
    prima = settings.chiave_promemoria
    settings.chiave_promemoria = CHIAVE
    yield {"X-Chiave-Promemoria": CHIAVE}
    settings.chiave_promemoria = prima


def _impegno(client, headers, fra_minuti: int, promemoria: int | None):
    inizio = (datetime.now() + timedelta(minutes=fra_minuti)).replace(microsecond=0)
    return client.post("/agenda", json={
        "titolo": "Intervento", "luogo": "Officina",
        "inizio": inizio.isoformat(), "promemoria_minuti": promemoria,
    }, headers=headers).json()


def test_senza_chiave_configurata_e_inerte(client):
    """Finche' la chiave non e' impostata, l'endpoint non fa niente."""
    prima = settings.chiave_promemoria
    settings.chiave_promemoria = ""
    try:
        r = client.post("/agenda/promemoria/invia")
        assert r.status_code == 503
    finally:
        settings.chiave_promemoria = prima


def test_chiave_sbagliata_rifiutata(client, con_chiave):
    assert client.post("/agenda/promemoria/invia").status_code == 401
    assert client.post("/agenda/promemoria/invia",
                       headers={"X-Chiave-Promemoria": "sbagliata"}).status_code == 401


def test_manda_solo_quando_e_ora(client, con_chiave):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    # fra 3 ore con promemoria a 1 ora prima: troppo presto
    _impegno(client, a, fra_minuti=180, promemoria=60)

    r = client.post("/agenda/promemoria/invia", headers=con_chiave)
    assert r.status_code == 200 and r.json()["inviati"] == 0


def test_manda_quando_la_finestra_e_aperta(client, con_chiave):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    # fra 30 minuti con promemoria a 1 ora prima: siamo dentro
    _impegno(client, a, fra_minuti=30, promemoria=60)

    r = client.post("/agenda/promemoria/invia", headers=con_chiave)
    assert r.status_code == 200
    assert r.json()["inviati"] == 1
    assert r.json()["destinatari"] == 1


def test_non_manda_due_volte(client, con_chiave):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _impegno(client, a, fra_minuti=30, promemoria=60)

    assert client.post("/agenda/promemoria/invia", headers=con_chiave).json()["inviati"] == 1
    # seconda passata: niente, e' gia' partito
    assert client.post("/agenda/promemoria/invia", headers=con_chiave).json()["inviati"] == 0


def test_gli_impegni_senza_promemoria_restano_fuori(client, con_chiave):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _impegno(client, a, fra_minuti=10, promemoria=None)
    assert client.post("/agenda/promemoria/invia", headers=con_chiave).json()["inviati"] == 0


def test_gli_impegni_passati_non_avvisano(client, con_chiave):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _impegno(client, a, fra_minuti=-60, promemoria=60)   # gia' passato
    assert client.post("/agenda/promemoria/invia", headers=con_chiave).json()["inviati"] == 0


def test_una_riunione_avvisa_tutti_i_partecipanti(client, con_chiave):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it",
                                 "password": "password1", "ruolo": "operatore"}, headers=a)
    utenti = client.get("/utenti", headers=a).json()
    ids = [u["id"] for u in utenti]

    inizio = (datetime.now() + timedelta(minutes=30)).replace(microsecond=0)
    client.post("/agenda", json={"titolo": "Riunione", "inizio": inizio.isoformat(),
                                 "promemoria_minuti": 60, "partecipanti_ids": ids}, headers=a)

    r = client.post("/agenda/promemoria/invia", headers=con_chiave).json()
    assert r["inviati"] == 1          # una riunione sola...
    assert r["destinatari"] == 2      # ...ma due persone avvisate


def test_spostare_l_impegno_riarma_il_promemoria(client, con_chiave):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    i = _impegno(client, a, fra_minuti=30, promemoria=60)
    assert client.post("/agenda/promemoria/invia", headers=con_chiave).json()["inviati"] == 1

    # lo sposto piu' in la': il promemoria deve tornare da mandare
    nuovo = (datetime.now() + timedelta(minutes=45)).replace(microsecond=0)
    client.patch(f"/agenda/{i['id']}", json={"inizio": nuovo.isoformat()}, headers=a)

    assert client.post("/agenda/promemoria/invia", headers=con_chiave).json()["inviati"] == 1
