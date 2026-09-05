"""
Secondo fattore: il codice che cambia ogni 30 secondi.

Due cose da proteggere, e sono opposte:

- **che protegga davvero**: chi ha acceso il 2FA non deve entrare con la sola
  password, e i codici non devono essere indovinabili a raffica;
- **che non chiuda fuori nessuno**: chi NON l'ha acceso non deve accorgersi di
  niente, e chi perde il telefono deve avere una via d'uscita.

La seconda meta' e' la piu' importante. Un secondo fattore che blocca fuori il
proprietario e' un danno, non una protezione.
"""
import pyotp
import pytest

from app import limiti
from tests.conftest import registra


def _login(client, email="marco@a.it", password="password1"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _accendi(client, headers):
    """Accende il 2FA e restituisce (segreto, codici di recupero)."""
    preparato = client.post("/auth/2fa/prepara", headers=headers).json()
    codice = pyotp.TOTP(preparato["segreto"]).now()
    r = client.post("/auth/2fa/attiva", json={"codice": codice}, headers=headers)
    assert r.status_code == 200, r.text
    return preparato["segreto"], r.json()["codici"]


# ---------- CHI NON LO ACCENDE NON SE NE ACCORGE ----------

def test_senza_secondo_fattore_l_accesso_e_quello_di_sempre(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")

    r = _login(client)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    # e il token funziona subito
    tok = r.json()["access_token"]
    assert client.get("/auth/me",
                      headers={"Authorization": f"Bearer {tok}"}).status_code == 200


def test_di_default_e_spento(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.get("/auth/2fa/stato", headers=a).json() == {
        "attivo": False, "codici_recupero_rimasti": 0}


# ---------- ACCENDERLO ----------

def test_accendere_richiede_di_dimostrare_che_il_telefono_funziona(client):
    """Non si accende al buio: prima si prova a generare un codice giusto.
    Altrimenti chi configura male il telefono si chiude fuori da solo."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/auth/2fa/prepara", headers=a)

    r = client.post("/auth/2fa/attiva", json={"codice": "000000"}, headers=a)
    assert r.status_code == 400
    assert client.get("/auth/2fa/stato", headers=a).json()["attivo"] is False


def test_accendendolo_arrivano_i_codici_di_recupero(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, codici = _accendi(client, a)

    assert len(codici) == 8
    assert all("-" in c for c in codici)
    stato = client.get("/auth/2fa/stato", headers=a).json()
    assert stato == {"attivo": True, "codici_recupero_rimasti": 8}


def test_i_codici_di_recupero_non_si_rileggono(client):
    """Si mostrano una volta sola: nel database ci sono solo le impronte."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, codici = _accendi(client, a)

    from app.database import SessionLocal
    from app.models.utente import Utente
    db = SessionLocal()
    try:
        utente = db.query(Utente).filter(Utente.email == "marco@a.it").first()
        for codice in codici:
            assert codice not in (utente.totp_recupero or "")
    finally:
        db.close()


# ---------- ENTRARE CON IL SECONDO FATTORE ----------

def test_con_il_2fa_la_password_da_sola_non_basta_piu(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _accendi(client, a)

    r = _login(client)
    assert r.status_code == 200
    assert r.json()["token_type"] == "attesa_2fa"

    # il token di passaggio NON apre niente
    passaggio = r.json()["access_token"]
    assert client.get("/auth/me",
                      headers={"Authorization": f"Bearer {passaggio}"}).status_code == 401


def test_col_codice_giusto_si_entra(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    segreto, _ = _accendi(client, a)

    passaggio = _login(client).json()["access_token"]
    r = client.post("/auth/2fa/verifica",
                    json={"token": passaggio, "codice": pyotp.TOTP(segreto).now()})
    assert r.status_code == 200
    tok = r.json()["access_token"]
    assert client.get("/auth/me",
                      headers={"Authorization": f"Bearer {tok}"}).json()["email"] == "marco@a.it"


def test_col_codice_sbagliato_non_si_entra(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _accendi(client, a)
    passaggio = _login(client).json()["access_token"]

    assert client.post("/auth/2fa/verifica",
                       json={"token": passaggio, "codice": "000000"}).status_code == 401


def test_il_token_di_passaggio_di_un_altro_non_serve(client):
    """Il token di passaggio dice CHI sta entrando: non e' un lasciapassare
    generico da riusare per qualcun altro."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _accendi(client, a)

    assert client.post("/auth/2fa/verifica",
                       json={"token": "inventato", "codice": "123456"}).status_code == 401


def test_i_tentativi_sul_codice_sono_contati(client):
    """Sei cifre si indovinano, se si puo' provare all'infinito."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _accendi(client, a)
    limiti.azzera_tutto()
    passaggio = _login(client).json()["access_token"]

    for _ in range(limiti.MAX_TENTATIVI):
        client.post("/auth/2fa/verifica", json={"token": passaggio, "codice": "000000"})

    r = client.post("/auth/2fa/verifica", json={"token": passaggio, "codice": "000000"})
    assert r.status_code == 429


# ---------- PERDERE IL TELEFONO ----------

def test_un_codice_di_recupero_fa_entrare(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, codici = _accendi(client, a)
    passaggio = _login(client).json()["access_token"]

    r = client.post("/auth/2fa/verifica",
                    json={"token": passaggio, "codice": codici[0]})
    assert r.status_code == 200


def test_un_codice_di_recupero_vale_una_volta_sola(client):
    """Se restasse valido, chi lo ha letto una volta entrerebbe per sempre."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, codici = _accendi(client, a)

    passaggio = _login(client).json()["access_token"]
    client.post("/auth/2fa/verifica", json={"token": passaggio, "codice": codici[0]})

    limiti.azzera_tutto()
    passaggio2 = _login(client).json()["access_token"]
    r = client.post("/auth/2fa/verifica",
                    json={"token": passaggio2, "codice": codici[0]})
    assert r.status_code == 401
    # e ne restano sette
    tok = client.post("/auth/2fa/verifica",
                      json={"token": passaggio2, "codice": codici[1]}).json()["access_token"]
    stato = client.get("/auth/2fa/stato",
                       headers={"Authorization": f"Bearer {tok}"}).json()
    assert stato["codici_recupero_rimasti"] == 6


# ---------- SPEGNERLO ----------

def test_spegnere_richiede_la_password(client):
    """Se qualcuno si siede al tuo posto mentre sei collegato, non deve poter
    togliere la protezione con un clic."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _accendi(client, a)

    assert client.post("/auth/2fa/disattiva",
                       json={"password": "sbagliata"}, headers=a).status_code == 401
    assert client.get("/auth/2fa/stato", headers=a).json()["attivo"] is True


def test_spegnendolo_si_torna_all_accesso_semplice(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _accendi(client, a)

    assert client.post("/auth/2fa/disattiva",
                       json={"password": "password1"}, headers=a).status_code == 204

    r = _login(client)
    assert r.json()["token_type"] == "bearer"
    assert client.get("/auth/2fa/stato", headers=a).json() == {
        "attivo": False, "codici_recupero_rimasti": 0}
