"""Test dei permessi per ruolo su progetti, lavori e cambio stato."""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin_headers, nome, email, ruolo):
    client.post("/utenti", json={"nome": nome, "email": email, "password": "password1", "ruolo": ruolo},
                headers=admin_headers)
    return _login(client, email)


def test_operatore_non_crea_progetti(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _crea_utente(client, a, "Op", "op@a.it", "operatore")
    r = client.post("/progetti", json={"nome": "P"}, headers=op)
    assert r.status_code == 403


def test_caposquadra_crea_progetti_e_lavori(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    cs = _crea_utente(client, a, "Capo", "capo@a.it", "caposquadra")
    p = client.post("/progetti", json={"nome": "P"}, headers=cs)
    assert p.status_code == 201
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p.json()["id"]}, headers=cs)
    assert l.status_code == 201


def test_operatore_cambia_stato_solo_se_assegnato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _crea_utente(client, a, "Op", "op@a.it", "operatore")
    # admin crea progetto e lavoro
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    # operatore NON assegnato: cambio stato negato
    r = client.patch(f"/lavori/{l['id']}/stato", json={"stato": "in_corso"}, headers=op)
    assert r.status_code == 403

    # admin assegna l'operatore, poi l'operatore puo' cambiare stato
    op_id = [u for u in client.get("/utenti", headers=a).json() if u["email"] == "op@a.it"][0]["id"]
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": op_id}, headers=a)
    r = client.patch(f"/lavori/{l['id']}/stato", json={"stato": "in_corso"}, headers=op)
    assert r.status_code == 200
