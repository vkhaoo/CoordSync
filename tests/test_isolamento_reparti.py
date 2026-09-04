"""
Isolamento fra REPARTI dentro la stessa azienda.

Gemello di test_isolamento.py (che protegge il confine fra aziende), ma su un
piano piu' fine: qui tutti sono colleghi della stessa organizzazione, e quello
che deve reggere e' il secondo livello di isolamento.
"""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


def _id_utente(client, admin, email):
    return [u for u in client.get("/utenti", headers=admin).json() if u["email"] == email][0]["id"]


def _scenario(client):
    """Azienda con due reparti: Automazione (Anna) e Digitale (Dino).

    Ogni reparto ha un suo progetto; in piu' c'e' un progetto "generale"
    senza reparto. Restituisce tutto il necessario ai test.
    """
    admin = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, admin, "Anna", "anna@a.it", "caposquadra")
    dino = _crea_utente(client, admin, "Dino", "dino@a.it", "caposquadra")

    automazione = client.post("/reparti", json={"nome": "Automazione"}, headers=admin).json()
    digitale = client.post("/reparti", json={"nome": "Digitale"}, headers=admin).json()

    client.post(f"/reparti/{automazione['id']}/membri",
                json={"utente_id": _id_utente(client, admin, "anna@a.it")}, headers=admin)
    client.post(f"/reparti/{digitale['id']}/membri",
                json={"utente_id": _id_utente(client, admin, "dino@a.it")}, headers=admin)

    p_auto = client.post("/progetti", json={"nome": "Quadro", "reparto_id": automazione["id"]},
                         headers=admin).json()
    p_digi = client.post("/progetti", json={"nome": "Sito", "reparto_id": digitale["id"]},
                         headers=admin).json()
    p_gen = client.post("/progetti", json={"nome": "Generale"}, headers=admin).json()

    return {"admin": admin, "anna": anna, "dino": dino, "automazione": automazione,
            "digitale": digitale, "p_auto": p_auto, "p_digi": p_digi, "p_gen": p_gen}


# ---------- PROGETTI ----------

def test_vedo_solo_i_progetti_del_mio_reparto_piu_i_generali(client):
    s = _scenario(client)
    nomi = {p["nome"] for p in client.get("/progetti", headers=s["anna"]).json()}
    assert nomi == {"Quadro", "Generale"}   # niente "Sito": e' di un altro reparto


def test_admin_vede_tutti_i_progetti_dell_azienda(client):
    s = _scenario(client)
    nomi = {p["nome"] for p in client.get("/progetti", headers=s["admin"]).json()}
    assert nomi == {"Quadro", "Sito", "Generale"}


def test_senza_reparti_vedo_solo_i_generali(client):
    s = _scenario(client)
    solo = _crea_utente(client, s["admin"], "Solo", "solo@a.it", "caposquadra")
    nomi = {p["nome"] for p in client.get("/progetti", headers=solo).json()}
    assert nomi == {"Generale"}


def test_utente_in_due_reparti_li_vede_entrambi(client):
    s = _scenario(client)
    # Anna entra anche in Digitale: da quel momento vede pure quei progetti.
    client.post(f"/reparti/{s['digitale']['id']}/membri",
                json={"utente_id": _id_utente(client, s["admin"], "anna@a.it")}, headers=s["admin"])
    nomi = {p["nome"] for p in client.get("/progetti", headers=s["anna"]).json()}
    assert nomi == {"Quadro", "Sito", "Generale"}


def test_non_posso_toccare_il_progetto_di_un_altro_reparto(client):
    s = _scenario(client)
    pid = s["p_digi"]["id"]
    # Rispondiamo 404 (non 403): non riveliamo nemmeno che quel progetto esiste.
    assert client.patch(f"/progetti/{pid}", json={"nome": "Rubato"}, headers=s["anna"]).status_code == 404
    assert client.delete(f"/progetti/{pid}", headers=s["anna"]).status_code == 404


def test_non_posso_mettere_un_progetto_in_un_reparto_non_mio(client):
    s = _scenario(client)
    r = client.post("/progetti", json={"nome": "Furbata", "reparto_id": s["digitale"]["id"]},
                    headers=s["anna"])
    assert r.status_code == 404


def test_admin_puo_usare_qualsiasi_reparto(client):
    s = _scenario(client)
    r = client.post("/progetti", json={"nome": "Nuovo", "reparto_id": s["digitale"]["id"]},
                    headers=s["admin"])
    assert r.status_code == 201 and r.json()["reparto_id"] == s["digitale"]["id"]


# ---------- LAVORI, COMMENTI, CHECKLIST ----------

def test_non_vedo_i_lavori_di_un_altro_reparto(client):
    s = _scenario(client)
    lavoro = client.post("/lavori", json={"titolo": "Segreto", "progetto_id": s["p_digi"]["id"]},
                         headers=s["admin"]).json()

    # non compaiono nell'elenco generale...
    titoli = {l["titolo"] for l in client.get("/lavori", headers=s["anna"]).json()}
    assert "Segreto" not in titoli
    # ...ne' chiedendo esplicitamente quel progetto
    assert client.get(f"/lavori?progetto_id={s['p_digi']['id']}", headers=s["anna"]).json() == []
    # e non si puo' toccare il singolo lavoro
    assert client.patch(f"/lavori/{lavoro['id']}/stato", json={"stato": "fatto"},
                        headers=s["anna"]).status_code == 404
    assert client.delete(f"/lavori/{lavoro['id']}", headers=s["anna"]).status_code == 404


def test_non_leggo_ne_scrivo_commenti_di_un_altro_reparto(client):
    s = _scenario(client)
    lavoro = client.post("/lavori", json={"titolo": "Segreto", "progetto_id": s["p_digi"]["id"]},
                         headers=s["admin"]).json()
    assert client.get(f"/lavori/{lavoro['id']}/commenti", headers=s["anna"]).status_code == 404
    assert client.post(f"/lavori/{lavoro['id']}/commenti", json={"testo": "ciao"},
                       headers=s["anna"]).status_code == 404


def test_non_vedo_ne_tocco_la_checklist_di_un_altro_reparto(client):
    s = _scenario(client)
    lavoro = client.post("/lavori", json={"titolo": "Segreto", "progetto_id": s["p_digi"]["id"]},
                         headers=s["admin"]).json()
    voce = client.post(f"/lavori/{lavoro['id']}/sotto-attivita", json={"testo": "X"},
                       headers=s["admin"]).json()

    assert client.get(f"/lavori/{lavoro['id']}/sotto-attivita", headers=s["anna"]).status_code == 404
    assert client.patch(f"/sotto-attivita/{voce['id']}", json={"completata": True},
                        headers=s["anna"]).status_code == 404
    assert client.delete(f"/sotto-attivita/{voce['id']}", headers=s["anna"]).status_code == 404


def test_non_posso_assegnare_su_un_lavoro_di_un_altro_reparto(client):
    s = _scenario(client)
    lavoro = client.post("/lavori", json={"titolo": "Segreto", "progetto_id": s["p_digi"]["id"]},
                         headers=s["admin"]).json()
    r = client.post(f"/lavori/{lavoro['id']}/assegnati",
                    json={"utente_id": _id_utente(client, s["admin"], "anna@a.it")}, headers=s["anna"])
    assert r.status_code == 404


def test_se_sono_assegnato_vedo_il_lavoro_anche_fuori_dal_mio_reparto(client):
    """Rete di sicurezza: un lavoro che mi hanno dato non deve sparirmi."""
    s = _scenario(client)
    lavoro = client.post("/lavori", json={"titolo": "Trasversale", "progetto_id": s["p_digi"]["id"]},
                         headers=s["admin"]).json()
    client.post(f"/lavori/{lavoro['id']}/assegnati",
                json={"utente_id": _id_utente(client, s["admin"], "anna@a.it")}, headers=s["admin"])

    titoli = {l["titolo"] for l in client.get("/lavori", headers=s["anna"]).json()}
    assert "Trasversale" in titoli
    nomi = {p["nome"] for p in client.get("/progetti", headers=s["anna"]).json()}
    assert "Sito" in nomi


# ---------- GESTIONE DEI REPARTI ----------

def test_solo_admin_gestisce_i_reparti(client):
    s = _scenario(client)
    assert client.post("/reparti", json={"nome": "Abusivo"}, headers=s["anna"]).status_code == 403
    assert client.patch(f"/reparti/{s['automazione']['id']}", json={"nome": "X"},
                        headers=s["anna"]).status_code == 403
    assert client.delete(f"/reparti/{s['automazione']['id']}", headers=s["anna"]).status_code == 403
    assert client.post(f"/reparti/{s['automazione']['id']}/membri", json={"utente_id": 1},
                       headers=s["anna"]).status_code == 403


def test_eliminare_un_reparto_non_cancella_i_progetti(client):
    s = _scenario(client)
    assert client.delete(f"/reparti/{s['automazione']['id']}", headers=s["admin"]).status_code == 204

    # Il progetto resta, ed e' tornato "generale" (senza reparto).
    progetti = client.get("/progetti", headers=s["admin"]).json()
    quadro = [p for p in progetti if p["nome"] == "Quadro"]
    assert len(quadro) == 1 and quadro[0]["reparto_id"] is None


def test_reparti_isolati_fra_aziende_diverse(client):
    """Il primo livello di isolamento deve reggere anche sui reparti."""
    s = _scenario(client)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    assert client.get("/reparti", headers=altra).json() == []
    assert client.patch(f"/reparti/{s['automazione']['id']}", json={"nome": "X"},
                        headers=altra).status_code == 404
    assert client.post(f"/reparti/{s['automazione']['id']}/membri", json={"utente_id": 1},
                       headers=altra).status_code == 404


def test_non_posso_mettere_nel_reparto_uno_di_un_altra_azienda(client):
    s = _scenario(client)
    registra(client, "Azienda B", "Bruno", "bruno@b.it")
    estraneo = client.post("/auth/login", json={"email": "bruno@b.it", "password": "password1"})
    # ricavo l'id di Bruno dal suo stesso token
    suo = client.get("/auth/me", headers={
        "Authorization": f"Bearer {estraneo.json()['access_token']}"}).json()

    r = client.post(f"/reparti/{s['automazione']['id']}/membri",
                    json={"utente_id": suo["id"]}, headers=s["admin"])
    assert r.status_code == 404
