"""
Test delle preferenze sulle email.

Due cose contano: che gli interruttori nascano ACCESI (chi non tocca niente
deve continuare a ricevere quello che riceveva ieri), e che le email di
SERVIZIO non si possano spegnere — senza quelle non si entra piu'.
"""
from datetime import datetime, timedelta, timezone

from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _utente(client, admin, nome, email, ruolo="operatore"):
    r = client.post("/utenti", json={"nome": nome, "email": email,
                                     "password": "password1", "ruolo": ruolo}, headers=admin)
    return r.json()["id"], _login(client, email)


def test_nascono_accese(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    io = client.get("/auth/me", headers=a).json()
    assert io["email_assegnazioni"] is True
    assert io["email_promemoria"] is True


def test_si_spengono_e_si_riaccendono(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")

    r = client.patch("/auth/me", json={"email_assegnazioni": False}, headers=a)
    assert r.status_code == 200
    assert r.json()["email_assegnazioni"] is False
    # L'altra non si e' mossa: si manda solo quello che si cambia.
    assert r.json()["email_promemoria"] is True

    r = client.patch("/auth/me", json={"email_assegnazioni": True}, headers=a)
    assert r.json()["email_assegnazioni"] is True


def test_cambiare_il_nome_non_tocca_le_preferenze(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.patch("/auth/me", json={"email_promemoria": False}, headers=a)

    r = client.patch("/auth/me", json={"nome": "Marco Rossi"}, headers=a)
    assert r.json()["nome"] == "Marco Rossi"
    assert r.json()["email_promemoria"] is False


def test_il_nome_vuoto_resta_rifiutato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.patch("/auth/me", json={"nome": "   "}, headers=a).status_code == 400


def test_spenta_l_email_di_assegnazione_non_parte(client, monkeypatch):
    """L'avviso in campanella resta comunque: e' l'email a essere invadente,
    non la campanella."""
    partite = []
    import app.notifiche as notifiche
    monkeypatch.setattr(notifiche, "invia_email",
                        lambda **kw: partite.append(kw["destinatario"]))

    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    client.patch("/auth/me", json={"email_assegnazioni": False}, headers=gino)

    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    assert "gino@a.it" not in partite
    # Ma la campanella ha suonato lo stesso.
    avvisi = client.get("/notifiche", headers=gino).json()["notifiche"]
    assert any(n["tipo"] == "assegnazione" for n in avvisi)


def test_accesa_invece_parte(client, monkeypatch):
    partite = []
    import app.notifiche as notifiche
    monkeypatch.setattr(notifiche, "invia_email",
                        lambda **kw: partite.append(kw["destinatario"]))

    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    assert "gino@a.it" in partite


def test_le_email_di_servizio_non_si_spengono(client, monkeypatch):
    """Il recupero password parte anche a interruttori spenti: se non partisse,
    chi ha spento tutto resterebbe chiuso fuori per sempre."""
    partite = []
    # Qui si sostituisce il nome DENTRO auth.py e non dentro notifiche.py:
    # auth lo importa in cima al file, quindi il suo riferimento e' gia'
    # legato e sostituire l'originale non lo cambierebbe.
    import app.routers.auth as auth
    monkeypatch.setattr(auth, "invia_email",
                        lambda **kw: partite.append(kw["destinatario"]))

    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.patch("/auth/me", json={"email_assegnazioni": False,
                                   "email_promemoria": False}, headers=a)
    partite.clear()

    client.post("/auth/richiedi-reset", json={"email": "marco@a.it"})
    assert "marco@a.it" in partite
