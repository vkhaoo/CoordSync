"""
Correggere i propri dati: il nome e l'indirizzo email.

E' il diritto di rettifica, ed era l'ultimo scoperto: si poteva scaricare
tutto e cancellarsi, ma non correggere un nome scritto male.

Le due cose seguono strade diverse ed e' voluto. Il nome cambia subito, perche'
non apre nessuna porta. L'email no: e' la chiave con cui si entra e l'unico
modo di recuperare la password, quindi un errore di battitura chiuderebbe fuori
dal proprio account senza rimedio. Per quella si passa da un link mandato al
nuovo indirizzo — l'unico modo di dimostrare che quella casella esiste davvero
ed e' tua.
"""
import pytest

from tests.conftest import registra


@pytest.fixture()
def email_spedite(monkeypatch):
    spedite = []

    def finta(destinatario, oggetto, corpo, corpo_html=None):
        spedite.append({"a": destinatario, "corpo": corpo})
        return True

    monkeypatch.setattr("app.notifiche.invia_email", finta)
    monkeypatch.setattr("app.routers.auth.invia_email", finta)
    return spedite


def _link(corpo: str) -> str:
    for pezzo in corpo.split():
        if "cambio_email_token=" in pezzo:
            return pezzo.split("cambio_email_token=")[1]
    raise AssertionError("nessun link di cambio email")


def _accedi(client, email, password="password1"):
    return client.post("/auth/login", json={"email": email, "password": password})


# ---------- IL NOME ----------

def test_correggere_il_proprio_nome(client):
    a = registra(client, "Azienda A", "Marco Ross", "marco@a.it")

    r = client.patch("/auth/me", json={"nome": "Marco Rossi"}, headers=a)
    assert r.status_code == 200
    assert r.json()["nome"] == "Marco Rossi"
    assert client.get("/auth/me", headers=a).json()["nome"] == "Marco Rossi"


def test_il_nome_nuovo_si_vede_anche_ai_colleghi(client):
    a = registra(client, "Azienda A", "Marco Ross", "marco@a.it")
    client.patch("/auth/me", json={"nome": "Marco Rossi"}, headers=a)

    assert [u["nome"] for u in client.get("/utenti", headers=a).json()] == ["Marco Rossi"]


def test_un_nome_vuoto_non_si_salva(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.patch("/auth/me", json={"nome": "   "}, headers=a).status_code == 400
    assert client.get("/auth/me", headers=a).json()["nome"] == "Marco"


def test_si_corregge_solo_il_proprio(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    # Senza sessione: si azzerano anche i cookie, se no resterebbe quello
    # lasciato dalla registrazione e la richiesta risulterebbe collegata.
    client.cookies.clear()

    assert client.patch("/auth/me", json={"nome": "Chiunque"}).status_code == 401


# ---------- L'EMAIL: SI CHIEDE, NON SI IMPONE ----------

def test_chiedere_il_cambio_non_cambia_ancora_niente(client, email_spedite):
    """Il punto piu' importante: finche' non si apre il link si entra ancora
    con l'indirizzo di prima. Un errore di battitura non chiude fuori."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")

    r = client.post("/auth/cambia-email",
                    json={"password": "password1", "nuova_email": "nuovo@a.it"},
                    headers=a)
    assert r.status_code == 202

    assert client.get("/auth/me", headers=a).json()["email"] == "marco@a.it"
    assert _accedi(client, "marco@a.it").status_code == 200
    assert _accedi(client, "nuovo@a.it").status_code == 401


def test_l_email_di_conferma_va_al_nuovo_indirizzo(client, email_spedite):
    """Va mandata li' e non al vecchio: e' la casella nuova che deve
    dimostrare di esistere."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    email_spedite.clear()

    client.post("/auth/cambia-email",
                json={"password": "password1", "nuova_email": "nuovo@a.it"}, headers=a)

    assert len(email_spedite) == 1
    assert email_spedite[0]["a"] == "nuovo@a.it"


def test_aprendo_il_link_il_cambio_diventa_vero(client, email_spedite):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    email_spedite.clear()
    client.post("/auth/cambia-email",
                json={"password": "password1", "nuova_email": "nuovo@a.it"}, headers=a)

    r = client.post("/auth/conferma-email",
                    json={"token": _link(email_spedite[0]["corpo"])})
    assert r.status_code == 200

    # da adesso si entra con quello nuovo, e non piu' col vecchio
    assert _accedi(client, "nuovo@a.it").status_code == 200
    assert _accedi(client, "marco@a.it").status_code == 401
    # ed e' verificato: il link e' arrivato proprio li'
    assert client.get("/auth/me", headers=a).json()["email_verificata"] is True


def test_serve_la_password(client, email_spedite):
    """Cambiare indirizzo vuol dire spostare l'account: non deve poterlo fare
    chi si siede al tuo posto mentre sei collegato."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    email_spedite.clear()   # la registrazione ne ha gia' mandata una (la verifica)

    r = client.post("/auth/cambia-email",
                    json={"password": "sbagliata", "nuova_email": "nuovo@a.it"},
                    headers=a)
    assert r.status_code == 401
    assert email_spedite == []


def test_non_si_prende_l_indirizzo_di_un_altro(client, email_spedite):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    b = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    email_spedite.clear()

    r = client.post("/auth/cambia-email",
                    json={"password": "password1", "nuova_email": "marco@a.it"},
                    headers=b)
    assert r.status_code == 409
    assert email_spedite == []


def test_chiedere_il_proprio_indirizzo_non_ha_senso(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/auth/cambia-email",
                    json={"password": "password1", "nuova_email": "marco@a.it"},
                    headers=a)
    assert r.status_code == 400


def test_un_link_inventato_non_cambia_niente(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.post("/auth/conferma-email",
                       json={"token": "roba-inventata"}).status_code == 400
    assert client.get("/auth/me", headers=a).json()["email"] == "marco@a.it"


def test_se_nel_frattempo_qualcuno_si_prende_l_indirizzo(client, email_spedite):
    """Fra la richiesta e il clic puo' passare un'ora: si ricontrolla al
    momento di applicare, se no due account finirebbero con la stessa email."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    email_spedite.clear()
    client.post("/auth/cambia-email",
                json={"password": "password1", "nuova_email": "conteso@a.it"}, headers=a)
    token = _link(email_spedite[0]["corpo"])

    # qualcun altro si registra con quell'indirizzo prima che Marco confermi
    client.post("/auth/register", json={"nome": "Altro", "email": "conteso@a.it",
                                        "password": "password1"})

    r = client.post("/auth/conferma-email", json={"token": token})
    assert r.status_code == 409
    assert client.get("/auth/me", headers=a).json()["email"] == "marco@a.it"


def test_il_token_del_cambio_non_apre_l_account(client, email_spedite):
    """Come tutti i token di scopo: serve a una cosa sola."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    email_spedite.clear()
    client.post("/auth/cambia-email",
                json={"password": "password1", "nuova_email": "nuovo@a.it"}, headers=a)
    token = _link(email_spedite[0]["corpo"])

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
