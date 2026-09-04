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


def test_completamento_registra_data_e_autore(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    # passo a "fatto": deve registrare completato_il e completato_da
    r = client.patch(f"/lavori/{l['id']}/stato", json={"stato": "fatto"}, headers=a).json()
    assert r["completato_il"] is not None
    assert r["completato_da"]["email"] == "marco@a.it"

    # torno indietro: i dati di completamento si azzerano
    r2 = client.patch(f"/lavori/{l['id']}/stato", json={"stato": "in_corso"}, headers=a).json()
    assert r2["completato_il"] is None
    assert r2["completato_da"] is None


def test_modifica_ed_elimina_lavoro(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p1 = client.post("/progetti", json={"nome": "P1"}, headers=a).json()
    p2 = client.post("/progetti", json={"nome": "P2"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Nome sbagliato", "progetto_id": p1["id"]}, headers=a).json()

    # rinomino e sposto nell'altro progetto
    r = client.patch(f"/lavori/{l['id']}", json={"titolo": "Nome giusto", "progetto_id": p2["id"]}, headers=a)
    assert r.status_code == 200
    assert r.json()["titolo"] == "Nome giusto"
    assert r.json()["progetto_id"] == p2["id"]

    # elimino
    assert client.delete(f"/lavori/{l['id']}", headers=a).status_code == 204


def test_cambia_priorita_dopo_la_creazione(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    assert l["priorita"] == "normale"   # default alla creazione

    r = client.patch(f"/lavori/{l['id']}", json={"priorita": "urgente"}, headers=a)
    assert r.status_code == 200 and r.json()["priorita"] == "urgente"
    # e la nuova priorita' resta anche rileggendo l'elenco
    letto = client.get(f"/lavori?progetto_id={p['id']}", headers=a).json()[0]
    assert letto["priorita"] == "urgente"


def test_priorita_inesistente_rifiutata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    assert client.patch(f"/lavori/{l['id']}", json={"priorita": "altissima"},
                        headers=a).status_code == 422


def test_operatore_non_cambia_priorita(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _crea_utente(client, a, "Op", "op@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    # nemmeno se e' assegnato: la priorita' la decide chi gestisce
    op_id = [u for u in client.get("/utenti", headers=a).json() if u["email"] == "op@a.it"][0]["id"]
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": op_id}, headers=a)
    assert client.patch(f"/lavori/{l['id']}", json={"priorita": "urgente"},
                        headers=op).status_code == 403


def test_operatore_non_modifica_ne_elimina_lavoro(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Op", "email": "op@a.it", "password": "password1",
                                 "ruolo": "operatore"}, headers=a)
    tok = client.post("/auth/login", json={"email": "op@a.it", "password": "password1"}).json()["access_token"]
    op = {"Authorization": f"Bearer {tok}"}
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    assert client.patch(f"/lavori/{l['id']}", json={"titolo": "X"}, headers=op).status_code == 403
    assert client.delete(f"/lavori/{l['id']}", headers=op).status_code == 403


def test_elimina_progetto_a_cascata(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    # aggiungo una sotto-attivita' per verificare la cascata profonda
    client.post(f"/lavori/{l['id']}/sotto-attivita", json={"testo": "X"}, headers=a)

    # elimino il progetto
    assert client.delete(f"/progetti/{p['id']}", headers=a).status_code == 204
    # il progetto non c'e' piu'
    assert client.get("/progetti", headers=a).json() == []
    # e nemmeno i suoi lavori (la sotto-attivita' del lavoro darebbe 404 sul lavoro)
    assert client.get(f"/lavori/{l['id']}/sotto-attivita", headers=a).status_code == 404


def test_rinomina_progetto(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Nome vecchio"}, headers=a).json()
    r = client.patch(f"/progetti/{p['id']}", json={"nome": "Nome nuovo"}, headers=a)
    assert r.status_code == 200 and r.json()["nome"] == "Nome nuovo"


def test_operatore_non_elimina_progetto(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Op", "email": "op@a.it", "password": "password1",
                                 "ruolo": "operatore"}, headers=a)
    tok = client.post("/auth/login", json={"email": "op@a.it", "password": "password1"}).json()["access_token"]
    op = {"Authorization": f"Bearer {tok}"}
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    assert client.delete(f"/progetti/{p['id']}", headers=op).status_code == 403
