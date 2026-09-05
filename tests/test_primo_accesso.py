"""
Come si entra in CoordSync la prima volta.

Iscriversi e aprire un'azienda erano la stessa cosa, e non tornava: chi veniva
invitato da qualcun altro doveva comunque farsi un'azienda propria, che poi
restava li' vuota. Adesso sono due gesti separati, e le strade sono due:

- **apro io un'azienda**: mi iscrivo, e dalla schermata di scelta la creo;
- **mi invitano**: l'account nasce dall'invito, e di aziende non ne creo mai
  nessuna.

In mezzo c'e' uno stato che prima non poteva esistere — un account che non
appartiene a niente — e questo file serve soprattutto a proteggere quello: chi
ci si trova non deve vedere dati di nessuno, e non deve nemmeno restare
bloccato senza capire cosa fare.
"""
from tests.conftest import registra, registra_solo_account


def _login(client, email, password="password1"):
    return client.post("/auth/login", json={"email": email, "password": password})


# ---------- L'ACCOUNT NASCE DA SOLO ----------

def test_iscriversi_non_crea_nessuna_azienda(client):
    r = client.post("/auth/register", json={
        "nome": "Marco", "email": "marco@a.it", "password": "password1"})
    assert r.status_code == 201

    io = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/auth/aziende", headers=io).json() == []
    assert client.get("/auth/me", headers=io).json()["organizzazione_id"] is None


def test_senza_azienda_non_si_vede_niente(client):
    """Il 409 e' scelto apposta: non e' "non hai il permesso" ne' "non esiste",
    e' "manca un passaggio". Il frontend lo riconosce e apre la schermata di
    scelta invece di mostrare una pagina vuota."""
    io = registra_solo_account(client, "Marco", "marco@a.it")

    for metodo, percorso in [("get", "/progetti"), ("get", "/macchine"),
                             ("get", "/utenti"), ("get", "/reparti"),
                             ("get", "/notifiche")]:
        r = getattr(client, metodo)(percorso, headers=io)
        assert r.status_code == 409, f"{percorso} -> {r.status_code}"
        assert "nessuna azienda" in r.json()["detail"]


def test_senza_azienda_il_proprio_profilo_funziona(client):
    """Le poche cose che devono funzionare in quel momento: sapere chi sono,
    vedere le mie aziende (nessuna), crearne una."""
    io = registra_solo_account(client, "Marco", "marco@a.it")

    assert client.get("/auth/me", headers=io).status_code == 200
    assert client.get("/auth/aziende", headers=io).status_code == 200
    assert client.get("/auth/2fa/stato", headers=io).status_code == 200


# ---------- PRIMA STRADA: ME LA CREO ----------

def test_creare_la_prima_azienda_mi_rende_amministratore(client):
    io = registra_solo_account(client, "Marco", "marco@a.it")

    r = client.post("/auth/aziende", json={"nome": "Elettro Rossi"}, headers=io)
    assert r.status_code == 201
    assert r.json()["nome"] == "Elettro Rossi"

    # il token che torna punta gia' li' dentro
    dentro = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = client.get("/auth/me", headers=dentro).json()
    assert me["ruolo"] == "admin"
    assert me["organizzazione_id"] == r.json()["id"]
    # e da li' si lavora
    assert client.post("/progetti", json={"nome": "Linea 3"},
                       headers=dentro).status_code == 201


def test_un_nome_vuoto_non_fa_un_azienda(client):
    io = registra_solo_account(client, "Marco", "marco@a.it")
    assert client.post("/auth/aziende", json={"nome": "   "},
                       headers=io).status_code == 400


def test_si_puo_aprire_una_seconda_azienda(client):
    """Chi apre un'attivita' nuova non deve rifarsi un account."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")

    r = client.post("/auth/aziende", json={"nome": "Azienda B"}, headers=a)
    assert r.status_code == 201

    aziende = client.get("/auth/aziende", headers=a).json()
    assert sorted(x["nome"] for x in aziende) == ["Azienda A", "Azienda B"]
    assert all(x["ruolo"] == "admin" for x in aziende)


def test_rientrando_si_torna_nell_azienda_di_casa(client):
    """Chiudendo e riaprendo non si deve ricominciare dalla schermata di
    scelta: la prima azienda diventa il punto di partenza."""
    registra(client, "Azienda A", "Marco", "marco@a.it")

    token = _login(client, "marco@a.it").json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["organizzazione_id"] is not None
    assert me["ruolo"] == "admin"


# ---------- SECONDA STRADA: MI INVITANO ----------

def test_chi_arriva_per_invito_non_crea_nessuna_azienda(client):
    """La strada di chi entra chiamato da qualcun altro: l'account nasce
    dall'invito, e resta con una sola azienda — quella di chi l'ha invitato."""
    a = registra(client, "Elettro Rossi", "Marco", "marco@a.it")
    client.post("/utenti/invita", json={"nome": "Anna", "email": "anna@a.it",
                                        "ruolo": "operatore"}, headers=a)

    # Anna sceglie la sua password dal link e entra (il flusso degli inviti
    # esistenti non cambia).
    from app.security import crea_token_scopo
    from app.routers.auth import SCOPO_INVITO
    anna_id = [u for u in client.get("/utenti", headers=a).json()
               if u["email"] == "anna@a.it"][0]["id"]
    token = crea_token_scopo(anna_id, SCOPO_INVITO, 60)
    assert client.post("/auth/accetta-invito",
                       json={"token": token, "password": "password1"}).status_code == 200

    sua = {"Authorization": f"Bearer {_login(client, 'anna@a.it').json()['access_token']}"}
    aziende = client.get("/auth/aziende", headers=sua).json()
    assert [x["nome"] for x in aziende] == ["Elettro Rossi"]
    assert aziende[0]["ruolo"] == "operatore"
    # e vede il posto di lavoro, senza essersi mai creata niente
    assert client.get("/progetti", headers=sua).status_code == 200
