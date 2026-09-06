"""
Test della correzione e della rimozione dei commenti.

Il punto delicato e' che i due permessi NON sono lo stesso permesso:
correggere e' solo di chi ha scritto (riscrivere le parole di un altro non e'
moderazione), togliere lo puo' fare anche chi gestisce (se qualcuno scrive una
cosa fuori posto, qualcuno deve poterla togliere).
"""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _utente(client, admin, nome, email, ruolo="operatore"):
    r = client.post("/utenti", json={"nome": nome, "email": email,
                                     "password": "password1", "ruolo": ruolo}, headers=admin)
    return r.json()["id"], _login(client, email)


def _lavoro_con_commento(client, admin, autore, testo="prima versione"):
    p = client.post("/progetti", json={"nome": "P"}, headers=admin).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=admin).json()
    c = client.post(f"/lavori/{l['id']}/commenti", json={"testo": testo}, headers=autore).json()
    return l, c


def test_correggo_il_mio_commento_e_si_vede_che_l_ho_fatto(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    l, c = _lavoro_con_commento(client, a, a)
    assert c["modificato_il"] is None

    r = client.patch(f"/commenti/{c['id']}", json={"testo": "era a 6 bar, non 8"}, headers=a)
    assert r.status_code == 200
    assert r.json()["testo"] == "era a 6 bar, non 8"
    # La correzione si dichiara: riscrivere in silenzio cambierebbe la storia.
    assert r.json()["modificato_il"] is not None

    letto = client.get(f"/lavori/{l['id']}/commenti", headers=a).json()[0]
    assert letto["modificato_il"] is not None


def test_nessuno_riscrive_le_parole_di_un_altro_nemmeno_l_admin(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)
    c = client.post(f"/lavori/{l['id']}/commenti", json={"testo": "suo"}, headers=gino).json()

    assert client.patch(f"/commenti/{c['id']}", json={"testo": "no"}, headers=a).status_code == 403
    assert client.get(f"/lavori/{l['id']}/commenti", headers=a).json()[0]["testo"] == "suo"


def test_togliere_il_proprio_commento(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    l, c = _lavoro_con_commento(client, a, a)

    assert client.delete(f"/commenti/{c['id']}", headers=a).status_code == 204
    assert client.get(f"/lavori/{l['id']}/commenti", headers=a).json() == []


def test_chi_gestisce_puo_togliere_il_commento_di_un_altro(client):
    """Il permesso in piu' serve: una cosa fuori posto qualcuno deve poterla
    togliere. Ma resta un TOGLIERE, non un riscrivere."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)
    c = client.post(f"/lavori/{l['id']}/commenti", json={"testo": "fuori posto"}, headers=gino).json()

    assert client.delete(f"/commenti/{c['id']}", headers=a).status_code == 204


def test_un_operatore_non_tocca_i_commenti_altrui(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    l, c = _lavoro_con_commento(client, a, a, "dell'admin")
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    assert client.patch(f"/commenti/{c['id']}", json={"testo": "x"}, headers=gino).status_code == 403
    assert client.delete(f"/commenti/{c['id']}", headers=gino).status_code == 403


def test_vale_anche_per_i_commenti_di_macchina(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = client.post("/macchine", json={"nome": "Pressa 1"}, headers=a).json()
    v = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": "Misure"}, headers=a).json()
    c = client.post(f"/voci/{v['id']}/commenti", json={"testo": "6 bar"}, headers=a).json()

    r = client.patch(f"/commenti/{c['id']}", json={"testo": "8 bar"}, headers=a)
    assert r.status_code == 200 and r.json()["testo"] == "8 bar"
    assert client.delete(f"/commenti/{c['id']}", headers=a).status_code == 204
    assert client.get(f"/voci/{v['id']}/commenti", headers=a).json() == []


def test_un_estraneo_non_vede_e_non_tocca(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    l, c = _lavoro_con_commento(client, a, a)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    # 404 e non 403: per lui quel commento non esiste proprio.
    assert client.patch(f"/commenti/{c['id']}", json={"testo": "x"}, headers=altra).status_code == 404
    assert client.delete(f"/commenti/{c['id']}", headers=altra).status_code == 404


def test_fuori_dal_mio_reparto_il_commento_non_esiste(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, dino = _utente(client, a, "Dino", "dino@a.it", "caposquadra")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    m = client.post("/macchine", json={"nome": "Riservata", "reparti_ids": [reparto["id"]]},
                    headers=a).json()
    v = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": "Misure"}, headers=a).json()
    c = client.post(f"/voci/{v['id']}/commenti", json={"testo": "riservato"}, headers=a).json()

    # Dino gestisce, ma quel reparto non e' suo: nemmeno togliere.
    assert client.delete(f"/commenti/{c['id']}", headers=dino).status_code == 404
