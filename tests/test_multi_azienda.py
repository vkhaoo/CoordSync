"""
Un utente che lavora per piu' aziende.

E' la modifica piu' delicata mai fatta al progetto: prima "in che azienda sei"
era scritto sulla riga dell'utente e non poteva sbagliarsi, adesso arriva dal
token e va verificato ogni volta. Se il controllo saltasse, chiunque potrebbe
fabbricarsi un token con dentro l'azienda di qualcun altro.

Per questo qui si prova soprattutto quello che NON deve succedere.
"""
import pytest

from app.security import crea_token
from tests.conftest import registra


def _login(client, email, password="password1"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def email_spedite(monkeypatch):
    """Intercetta le email invece di spedirle: dentro c'e' il link d'invito."""
    spedite = []

    def finta(destinatario, oggetto, corpo, corpo_html=None):
        spedite.append({"a": destinatario, "oggetto": oggetto, "corpo": corpo})
        return True

    # Si intercetta anche il nome importato dentro il router: utenti.py fa
    # "from app.notifiche import invia_email", quindi ha una sua copia del
    # riferimento e sostituire solo l'originale non basterebbe.
    monkeypatch.setattr("app.notifiche.invia_email", finta)
    monkeypatch.setattr("app.routers.utenti.invia_email", finta)
    return spedite


def _link_invito(corpo: str) -> str:
    """Pesca il token dal corpo dell'email."""
    for pezzo in corpo.split():
        if "invito_azienda_token=" in pezzo:
            return pezzo.split("invito_azienda_token=")[1]
    raise AssertionError("nessun link d'invito nell'email")


def _due_aziende(client, email_spedite):
    """Marco ha l'Azienda A. Bruno ha l'Azienda B e invita Marco da lui."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    b = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    client.post("/progetti", json={"nome": "Roba di A"}, headers=a)
    client.post("/progetti", json={"nome": "Roba di B"}, headers=b)
    email_spedite.clear()
    r = client.post("/utenti/invita",
                    json={"nome": "Marco", "email": "marco@a.it", "ruolo": "caposquadra"},
                    headers=b)
    return a, b, r


# ---------- L'INVITO A CHI HA GIA' UN ACCOUNT ----------

def test_invitare_chi_ha_gia_un_account_non_crea_niente(client, email_spedite):
    """Finche' non accetta, per quell'azienda quella persona non esiste."""
    a, b, r = _due_aziende(client, email_spedite)

    assert r.status_code == 202          # preso in carico, non "creato"
    assert len(email_spedite) == 1
    assert email_spedite[0]["a"] == "marco@a.it"
    # nell'elenco dei colleghi di B non c'e' ancora nessun Marco
    assert [u["nome"] for u in client.get("/utenti", headers=b).json()] == ["Bruno"]


def test_finche_non_accetta_non_vede_niente_dell_altra_azienda(client, email_spedite):
    """L'invito si vede, ma non apre niente: e' il punto piu' importante di
    tutto il meccanismo degli inviti in attesa."""
    a, b, _ = _due_aziende(client, email_spedite)

    assert [p["nome"] for p in client.get("/progetti", headers=a).json()] == ["Roba di A"]

    aziende = client.get("/auth/aziende", headers=a).json()
    per_nome = {x["nome"]: x for x in aziende}
    assert per_nome["Azienda A"]["invito"] is False
    assert per_nome["Azienda B"]["invito"] is True     # solo un invito, non un posto dove sono

    # e non ci si puo' nemmeno spostare dentro
    assert client.post("/auth/cambia-azienda",
                       json={"organizzazione_id": per_nome["Azienda B"]["id"]},
                       headers=a).status_code == 404


def test_accettando_l_azienda_si_aggiunge(client, email_spedite):
    a, b, _ = _due_aziende(client, email_spedite)
    token = _link_invito(email_spedite[0]["corpo"])

    r = client.post("/auth/accetta-invito-azienda", json={"token": token})
    assert r.status_code == 200
    assert r.json() == {"azienda": "Azienda B", "ruolo": "caposquadra"}

    aziende = client.get("/auth/aziende", headers=a).json()
    assert sorted(x["nome"] for x in aziende) == ["Azienda A", "Azienda B"]
    # e i ruoli sono diversi: admin a casa sua, caposquadra da Bruno
    per_nome = {x["nome"]: x for x in aziende}
    assert per_nome["Azienda A"]["ruolo"] == "admin"
    assert per_nome["Azienda B"]["ruolo"] == "caposquadra"
    assert per_nome["Azienda A"]["attiva"] is True


def test_un_invito_falso_non_apre_niente(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.post("/auth/accetta-invito-azienda",
                       json={"token": "roba-inventata"}).status_code == 400


def test_non_si_invita_due_volte_la_stessa_persona(client, email_spedite):
    a, b, _ = _due_aziende(client, email_spedite)
    client.post("/auth/accetta-invito-azienda",
                json={"token": _link_invito(email_spedite[0]["corpo"])})

    r = client.post("/utenti/invita",
                    json={"nome": "Marco", "email": "marco@a.it", "ruolo": "operatore"},
                    headers=b)
    assert r.status_code == 409
    assert "gia' parte" in r.json()["detail"]


# ---------- CAMBIARE AZIENDA ----------

def _marco_in_due_aziende(client, email_spedite):
    a, b, _ = _due_aziende(client, email_spedite)
    client.post("/auth/accetta-invito-azienda",
                json={"token": _link_invito(email_spedite[0]["corpo"])})
    aziende = client.get("/auth/aziende", headers=a).json()
    id_b = [x["id"] for x in aziende if x["nome"] == "Azienda B"][0]
    return a, b, id_b


def test_cambiando_azienda_cambia_quello_che_si_vede(client, email_spedite):
    """Il cuore della cosa: due mondi separati, si passa dall'uno all'altro
    senza rifare l'accesso e senza mai vederli insieme."""
    a, b, id_b = _marco_in_due_aziende(client, email_spedite)

    nuovo = client.post("/auth/cambia-azienda", json={"organizzazione_id": id_b},
                        headers=a).json()["access_token"]
    da_b = _headers(nuovo)

    assert [p["nome"] for p in client.get("/progetti", headers=da_b).json()] == ["Roba di B"]
    # e il token di prima continua a vedere solo l'azienda A
    assert [p["nome"] for p in client.get("/progetti", headers=a).json()] == ["Roba di A"]


def test_il_ruolo_cambia_con_l_azienda(client, email_spedite):
    """Admin a casa propria, caposquadra da Bruno: i permessi devono seguire."""
    a, b, id_b = _marco_in_due_aziende(client, email_spedite)
    da_b = _headers(client.post("/auth/cambia-azienda", json={"organizzazione_id": id_b},
                                headers=a).json()["access_token"])

    assert client.get("/auth/me", headers=a).json()["ruolo"] == "admin"
    assert client.get("/auth/me", headers=da_b).json()["ruolo"] == "caposquadra"
    # da caposquadra puo' creare progetti ma non utenti
    assert client.post("/progetti", json={"nome": "Suo"}, headers=da_b).status_code == 201
    assert client.post("/utenti", json={"nome": "X", "email": "x@b.it",
                                        "password": "password1", "ruolo": "operatore"},
                       headers=da_b).status_code == 403


def test_non_si_passa_a_un_azienda_di_cui_non_si_fa_parte(client, email_spedite):
    """404 e non 403: a chi non ci lavora non si dice nemmeno che esiste."""
    a, b, _ = _due_aziende(client, email_spedite)   # invito mandato ma NON accettato
    id_b = client.get("/auth/aziende", headers=b).json()[0]["id"]

    assert client.post("/auth/cambia-azienda", json={"organizzazione_id": id_b},
                       headers=a).status_code == 404


def test_un_token_fabbricato_a_mano_non_apre_le_porte(client, email_spedite):
    """Il controllo che regge tutto: il token DICE un'azienda, la tessera
    CONFERMA. Qui il token e' firmato bene (e' l'app stessa a farlo), ma la
    tessera non c'e': non deve passare."""
    a, b, _ = _due_aziende(client, email_spedite)
    id_b = client.get("/auth/aziende", headers=b).json()[0]["id"]
    marco_id = client.get("/auth/me", headers=a).json()["id"]

    falso = _headers(crea_token(marco_id, id_b))
    r = client.get("/progetti", headers=falso)
    assert r.status_code == 403
    assert "non fai" in r.json()["detail"].lower()


def test_i_token_vecchi_continuano_a_funzionare(client):
    """Chi era gia' collegato quando e' uscito il multi-azienda ha in tasca un
    token senza azienda dentro: deve continuare a lavorare come prima, non
    ritrovarsi buttato fuori."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/progetti", json={"nome": "Roba di A"}, headers=a)
    marco_id = client.get("/auth/me", headers=a).json()["id"]

    vecchio = _headers(crea_token(marco_id))    # senza organizzazione: come prima
    assert [p["nome"] for p in client.get("/progetti", headers=vecchio).json()] == ["Roba di A"]


# ---------- FAR USCIRE QUALCUNO ----------

def test_chi_lavora_anche_altrove_esce_solo_da_qui(client, email_spedite):
    """Un amministratore non deve poter cancellare un account che serve anche
    a un'altra azienda: lo toglie dalla sua e basta."""
    a, b, id_b = _marco_in_due_aziende(client, email_spedite)
    marco_id = client.get("/auth/me", headers=a).json()["id"]

    assert client.delete(f"/utenti/{marco_id}", headers=b).status_code == 204

    # da Bruno non c'e' piu'...
    assert [u["nome"] for u in client.get("/utenti", headers=b).json()] == ["Bruno"]
    # ...ma il suo account e' vivo e lavora ancora a casa sua
    assert _login(client, "marco@a.it").status_code == 200
    aziende = client.get("/auth/aziende", headers=a).json()
    assert [x["nome"] for x in aziende] == ["Azienda A"]


def test_chi_lavora_solo_qui_viene_anonimizzato_come_prima(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it",
                                 "password": "password1", "ruolo": "operatore"}, headers=a)
    luca_id = [u for u in client.get("/utenti", headers=a).json()
               if u["email"] == "luca@a.it"][0]["id"]

    assert client.delete(f"/utenti/{luca_id}", headers=a).status_code == 204
    assert _login(client, "luca@a.it").status_code == 401


def test_l_ultimo_admin_di_un_altra_azienda_blocca_la_cancellazione(client, email_spedite):
    """Marco e' l'unico admin di A: anche lavorando anche per B, non puo'
    andarsene lasciando A senza timone."""
    a, b, id_b = _marco_in_due_aziende(client, email_spedite)

    r = client.delete("/auth/me", headers=a)
    assert r.status_code == 409
    assert "Azienda A" in r.json()["detail"]


# ---------- RISPONDERE ALL'INVITO DA DENTRO L'APP ----------

def test_accettare_l_invito_senza_passare_dall_email(client, email_spedite):
    """L'email puo' perdersi o finire nello spam: l'invito e' scritto, quindi
    si trova comunque nel menu delle proprie aziende."""
    a, b, _ = _due_aziende(client, email_spedite)
    id_b = [x["id"] for x in client.get("/auth/aziende", headers=a).json()
            if x["invito"]][0]

    r = client.post("/auth/inviti/accetta", json={"organizzazione_id": id_b}, headers=a)
    assert r.status_code == 200
    assert r.json()["nome"] == "Azienda B"

    # ora ci si puo' andare davvero
    assert client.post("/auth/cambia-azienda", json={"organizzazione_id": id_b},
                       headers=a).status_code == 200


def test_rifiutare_l_invito_lo_fa_sparire(client, email_spedite):
    a, b, _ = _due_aziende(client, email_spedite)
    id_b = [x["id"] for x in client.get("/auth/aziende", headers=a).json()
            if x["invito"]][0]

    assert client.post("/auth/inviti/rifiuta", json={"organizzazione_id": id_b},
                       headers=a).status_code == 204

    assert [x["nome"] for x in client.get("/auth/aziende", headers=a).json()] == ["Azienda A"]
    # e chi aveva invitato puo' sempre riprovare
    assert client.post("/utenti/invita",
                       json={"nome": "Marco", "email": "marco@a.it", "ruolo": "operatore"},
                       headers=b).status_code == 202


def test_non_si_accetta_l_invito_di_qualcun_altro(client, email_spedite):
    """Il filtro sull'utente e' la parte importante: senza, basterebbe
    indovinare l'id dell'azienda per infilarsi dentro."""
    a, b, _ = _due_aziende(client, email_spedite)
    id_b = [x["id"] for x in client.get("/auth/aziende", headers=a).json()
            if x["invito"]][0]
    terza = registra(client, "Azienda C", "Carla", "carla@c.it")

    assert client.post("/auth/inviti/accetta", json={"organizzazione_id": id_b},
                       headers=terza).status_code == 404
    assert client.post("/auth/inviti/rifiuta", json={"organizzazione_id": id_b},
                       headers=terza).status_code == 404


def test_chi_e_solo_invitato_non_compare_fra_i_colleghi(client, email_spedite):
    """Non deve finire nel menu "assegna a": potrebbe ancora dire di no."""
    a, b, _ = _due_aziende(client, email_spedite)
    assert [u["nome"] for u in client.get("/utenti", headers=b).json()] == ["Bruno"]
