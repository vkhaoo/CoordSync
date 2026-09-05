"""
Cancellazione di un account, con anonimizzazione.

La regola decisa: il lavoro resta alla squadra, l'identita' sparisce. Qui si
protegge sia il "resta" (non si perde la memoria di quello che e' stato fatto)
sia il "sparisce" (non si entra piu', il nome non compare piu').
"""
from datetime import datetime, timedelta

from tests.conftest import registra


def _login(client, email, password="password1"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _headers(client, email):
    tok = _login(client, email).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo="operatore"):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _headers(client, email)


def _id(client, admin, email):
    return [u for u in client.get("/utenti", headers=admin).json() if u["email"] == email][0]["id"]


# ---------- IL LAVORO RESTA ----------

def test_il_lavoro_resta_e_l_autore_diventa_anonimo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p["id"]},
                    headers=a).json()
    # Luca e' operatore: puo' commentare solo i lavori a lui assegnati.
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id(client, a, "luca@a.it")}, headers=a)
    client.post(f"/lavori/{l['id']}/commenti",
                json={"testo": "Manca la guaina da 25"}, headers=luca)
    m = client.post("/macchine", json={"nome": "Pressa"}, headers=a).json()
    client.post(f"/macchine/{m['id']}/voci",
                json={"tipo": "modifica", "titolo": "Sostituito sensore"}, headers=luca)

    assert client.delete("/auth/me", headers=luca).status_code == 204

    # il commento c'e' ancora, con il testo intatto
    commenti = client.get(f"/lavori/{l['id']}/commenti", headers=a).json()
    assert [c["testo"] for c in commenti] == ["Manca la guaina da 25"]
    assert commenti[0]["autore"]["nome"] == "Utente eliminato"

    # e la voce di storico pure
    voci = client.get(f"/macchine/{m['id']}/voci", headers=a).json()
    assert [v["titolo"] for v in voci] == ["Sostituito sensore"]
    assert voci[0]["autore"]["nome"] == "Utente eliminato"


# ---------- L'IDENTITA' SPARISCE ----------

def test_dopo_la_cancellazione_non_si_entra_piu(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")

    assert client.delete("/auth/me", headers=luca).status_code == 204
    assert _login(client, "luca@a.it").status_code == 401


def test_il_nome_e_l_email_spariscono_dall_elenco(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")
    client.delete("/auth/me", headers=luca)

    elenco = client.get("/utenti", headers=a).json()
    assert "Luca" not in [u["nome"] for u in elenco]
    assert "luca@a.it" not in [u["email"] for u in elenco]
    assert "Utente eliminato" in [u["nome"] for u in elenco]


def test_esce_dai_reparti_e_dai_lavori_assegnati(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")
    rep = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    client.post(f"/reparti/{rep['id']}/membri",
                json={"utente_id": _id(client, a, "luca@a.it")}, headers=a)
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id(client, a, "luca@a.it")}, headers=a)

    client.delete("/auth/me", headers=luca)

    # non e' piu' assegnato a niente...
    lavori = client.get(f"/lavori?progetto_id={p['id']}", headers=a).json()
    assert lavori[0]["assegnatari"] == []
    # ...e non e' piu' in nessun reparto
    anonimo = [u for u in client.get("/utenti", headers=a).json()
               if u["nome"] == "Utente eliminato"][0]
    assert anonimo["reparti"] == []


def test_gli_avvisi_ricevuti_spariscono(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id(client, a, "luca@a.it")}, headers=a)
    assert client.get("/notifiche", headers=luca).json()["non_lette"] == 1

    client.delete("/auth/me", headers=luca)

    from app.models.notifica import Notifica
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        assert db.query(Notifica).count() == 0
    finally:
        db.close()


# ---------- AGENDA ----------

def test_gli_impegni_personali_spariscono_le_riunioni_restano(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")
    quando = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
    marco_id, luca_id = _id(client, a, "marco@a.it"), _id(client, a, "luca@a.it")

    # un impegno solo suo, e una riunione con Marco
    client.post("/agenda", json={"titolo": "Solo mio", "inizio": quando}, headers=luca)
    client.post("/agenda", json={"titolo": "Riunione", "inizio": quando,
                                 "partecipanti_ids": [marco_id, luca_id]}, headers=a)

    client.delete("/auth/me", headers=luca)

    dal = (datetime.now() - timedelta(days=1)).date()
    al = (datetime.now() + timedelta(days=10)).date()
    agenda = client.get(f"/agenda?dal={dal}&al={al}&ambito=azienda", headers=a).json()
    titoli = [i["titolo"] for i in agenda["impegni"]]

    assert "Solo mio" not in titoli        # era roba sua
    assert "Riunione" in titoli            # ma la riunione resta a chi c'era
    riunione = [i for i in agenda["impegni"] if i["titolo"] == "Riunione"][0]
    assert [p["nome"] for p in riunione["partecipanti"]] == ["Marco"]


# ---------- L'ULTIMO AMMINISTRATORE ----------

def test_l_ultimo_admin_non_puo_andarsene(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_utente(client, a, "Luca", "luca@a.it")   # un operatore non basta

    r = client.delete("/auth/me", headers=a)
    assert r.status_code == 409
    assert "amministratore" in r.json()["detail"]
    # e infatti entra ancora
    assert _login(client, "marco@a.it").status_code == 200


def test_con_due_admin_uno_puo_andarsene(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, a, "Anna", "anna@a.it", ruolo="admin")

    assert client.delete("/auth/me", headers=anna).status_code == 204
    assert _login(client, "marco@a.it").status_code == 200


# ---------- CANCELLAZIONE DA PARTE DELL'ADMIN ----------

def test_l_admin_fa_uscire_un_collega(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_utente(client, a, "Luca", "luca@a.it")
    luca_id = _id(client, a, "luca@a.it")

    assert client.delete(f"/utenti/{luca_id}", headers=a).status_code == 204
    assert _login(client, "luca@a.it").status_code == 401


def test_l_operatore_non_cancella_nessuno(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")
    anna = _crea_utente(client, a, "Anna", "anna@a.it")

    assert client.delete(f"/utenti/{_id(client, a, 'anna@a.it')}",
                         headers=luca).status_code == 403


def test_l_admin_non_cancella_se_stesso_dall_elenco(client):
    """Per andarsene c'e' la voce nel proprio profilo: cosi' non capita per
    sbaglio cliccando nell'elenco degli utenti."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.delete(f"/utenti/{_id(client, a, 'marco@a.it')}", headers=a)
    assert r.status_code == 400


def test_non_si_cancella_qualcuno_di_un_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_utente(client, a, "Luca", "luca@a.it")
    luca_id = _id(client, a, "luca@a.it")
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    assert client.delete(f"/utenti/{luca_id}", headers=altra).status_code == 404
    assert _login(client, "luca@a.it").status_code == 200   # sta benissimo


def test_non_si_cancella_due_volte(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _crea_utente(client, a, "Luca", "luca@a.it")
    luca_id = _id(client, a, "luca@a.it")

    assert client.delete(f"/utenti/{luca_id}", headers=a).status_code == 204
    assert client.delete(f"/utenti/{luca_id}", headers=a).status_code == 404


def test_chi_se_ne_va_non_e_piu_membro_di_nessuna_azienda(client):
    """La tessera va tolta a mano: la riga dell'utente non viene cancellata,
    quindi il database non la porta via da solo."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it")
    luca_id = _id(client, a, "luca@a.it")

    client.delete("/auth/me", headers=luca)

    from app.models.appartenenza import Appartenenza
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        assert db.query(Appartenenza).filter(
            Appartenenza.utente_id == luca_id).count() == 0
        # e quella di Marco invece c'e' ancora
        assert db.query(Appartenenza).count() == 1
    finally:
        db.close()
