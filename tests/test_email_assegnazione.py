"""
Email di avviso quando ti assegnano un lavoro.

E' l'unico evento che manda un'email oltre alla campanella. Due cose da
proteggere: che parta a chi di dovere, e soprattutto che un guasto nell'invio
NON faccia perdere l'assegnazione — il lavoro e' gia' salvato, l'email e' un
di piu'.
"""
from datetime import date, timedelta

import pytest

from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo="operatore"):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


def _id_utente(client, admin, email):
    return [u for u in client.get("/utenti", headers=admin).json() if u["email"] == email][0]["id"]


@pytest.fixture()
def email_spedite(monkeypatch):
    """Intercetta le email invece di spedirle davvero."""
    spedite = []

    def finta(destinatario, oggetto, corpo, corpo_html=None):
        spedite.append({"a": destinatario, "oggetto": oggetto, "corpo": corpo})
        return True

    monkeypatch.setattr("app.notifiche.invia_email", finta)
    return spedite


def _scenario(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_utente(client, a, "Luca", "luca@a.it")
    p = client.post("/progetti", json={"nome": "Linea 3"}, headers=a).json()
    l = client.post("/lavori", json={
        "titolo": "Cablaggio quadro", "progetto_id": p["id"],
        "data_scadenza": str(date.today() + timedelta(days=7)),
    }, headers=a).json()
    return a, l, _id_utente(client, a, "luca@a.it")


def test_assegnare_manda_l_email(client, email_spedite):
    a, l, luca_id = _scenario(client)
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": luca_id}, headers=a)

    assert len(email_spedite) == 1
    mail = email_spedite[0]
    assert mail["a"] == "luca@a.it"
    assert "Cablaggio quadro" in mail["oggetto"]
    assert "Marco" in mail["corpo"]        # chi ha assegnato
    assert "Linea 3" in mail["corpo"]      # il progetto
    assert "entro" in mail["corpo"]        # la scadenza


def test_assegnarsi_da_soli_non_manda_email(client, email_spedite):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    marco_id = _id_utente(client, a, "marco@a.it")

    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": marco_id}, headers=a)
    assert email_spedite == []


def test_riassegnare_non_rimanda_l_email(client, email_spedite):
    a, l, luca_id = _scenario(client)
    for _ in range(3):
        client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": luca_id}, headers=a)
    assert len(email_spedite) == 1


def test_se_l_email_non_parte_l_assegnazione_resta(client, monkeypatch):
    """Il punto piu' importante: un guasto nel servizio email non deve far
    perdere il lavoro assegnato."""
    def esplode(**_):
        raise RuntimeError("servizio email irraggiungibile")

    monkeypatch.setattr("app.notifiche.invia_email", esplode)

    a, l, luca_id = _scenario(client)
    r = client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": luca_id}, headers=a)

    assert r.status_code == 201
    assert [u["email"] for u in r.json()["assegnatari"]] == ["luca@a.it"]
    # e l'avviso nella campanella c'e' comunque
    luca = _login(client, "luca@a.it")
    assert client.get("/notifiche", headers=luca).json()["non_lette"] == 1


def test_i_commenti_non_mandano_email(client, email_spedite):
    """Solo le assegnazioni: commenti e riunioni restano nella campanella."""
    a, l, luca_id = _scenario(client)
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": luca_id}, headers=a)
    email_spedite.clear()

    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "una nota"}, headers=a)
    assert email_spedite == []


def test_le_riunioni_non_mandano_email(client, email_spedite):
    from datetime import datetime
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_utente(client, a, "Luca", "luca@a.it")
    ids = [_id_utente(client, a, e) for e in ("marco@a.it", "luca@a.it")]
    quando = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()

    client.post("/agenda", json={"titolo": "Riunione", "inizio": quando,
                                 "partecipanti_ids": ids}, headers=a)
    assert email_spedite == []
