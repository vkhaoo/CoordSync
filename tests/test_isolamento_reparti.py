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

    p_auto = client.post("/progetti", json={"nome": "Quadro", "reparti_ids": [automazione["id"]]},
                         headers=admin).json()
    p_digi = client.post("/progetti", json={"nome": "Sito", "reparti_ids": [digitale["id"]]},
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
    r = client.post("/progetti", json={"nome": "Furbata", "reparti_ids": [s["digitale"]["id"]]},
                    headers=s["anna"])
    assert r.status_code == 404


def test_admin_puo_usare_qualsiasi_reparto(client):
    s = _scenario(client)
    r = client.post("/progetti", json={"nome": "Nuovo", "reparti_ids": [s["digitale"]["id"]]},
                    headers=s["admin"])
    assert r.status_code == 201 and [x["id"] for x in r.json()["reparti"]] == [s["digitale"]["id"]]


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
    assert len(quadro) == 1 and quadro[0]["reparti"] == []


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


# ---------- PROGETTI E MACCHINE IN PIU' REPARTI ----------

def test_progetto_condiviso_fra_due_reparti_si_vede_da_entrambi(client):
    """Una linea seguita sia da Automazione sia da Digitale non appartiene a
    uno solo dei due: la vedono tutti e due."""
    s = _scenario(client)
    condiviso = client.post("/progetti", json={
        "nome": "Linea condivisa",
        "reparti_ids": [s["automazione"]["id"], s["digitale"]["id"]],
    }, headers=s["admin"])
    assert condiviso.status_code == 201
    assert len(condiviso.json()["reparti"]) == 2

    for chi in ("anna", "dino"):
        nomi = [p["nome"] for p in client.get("/progetti", headers=s[chi]).json()]
        assert "Linea condivisa" in nomi
        # e compare UNA VOLTA SOLA, non una per reparto in comune
        assert nomi.count("Linea condivisa") == 1


def test_chi_e_in_entrambi_i_reparti_non_vede_doppioni(client):
    s = _scenario(client)
    # Anna entra anche in Digitale, poi creo un progetto in entrambi i reparti.
    client.post(f"/reparti/{s['digitale']['id']}/membri",
                json={"utente_id": _id_utente(client, s["admin"], "anna@a.it")}, headers=s["admin"])
    client.post("/progetti", json={"nome": "Doppio",
                                   "reparti_ids": [s["automazione"]["id"], s["digitale"]["id"]]},
                headers=s["admin"])

    nomi = [p["nome"] for p in client.get("/progetti", headers=s["anna"]).json()]
    assert nomi.count("Doppio") == 1


def test_aggiungere_e_togliere_reparti_a_un_progetto(client):
    s = _scenario(client)
    pid = s["p_auto"]["id"]

    # aggiungo anche Digitale: ora lo vede pure Dino
    r = client.patch(f"/progetti/{pid}", json={
        "reparti_ids": [s["automazione"]["id"], s["digitale"]["id"]]}, headers=s["admin"])
    assert r.status_code == 200 and len(r.json()["reparti"]) == 2
    assert "Quadro" in {p["nome"] for p in client.get("/progetti", headers=s["dino"]).json()}

    # lista vuota = torna generale, lo vedono tutti
    r = client.patch(f"/progetti/{pid}", json={"reparti_ids": []}, headers=s["admin"])
    assert r.json()["reparti"] == []
    solo = _crea_utente(client, s["admin"], "Solo", "solo@a.it", "operatore")
    assert "Quadro" in {p["nome"] for p in client.get("/progetti", headers=solo).json()}


def test_basta_un_reparto_non_mio_per_rifiutare_tutto(client):
    """Se nella lista c'e' anche un solo reparto che non e' mio, rifiuto:
    non voglio accettare a meta' e lasciare il progetto dove non deve stare."""
    s = _scenario(client)
    r = client.post("/progetti", json={
        "nome": "Meta e meta",
        "reparti_ids": [s["automazione"]["id"], s["digitale"]["id"]],
    }, headers=s["anna"])   # Anna e' solo in Automazione
    assert r.status_code == 404
    assert "Meta e meta" not in {p["nome"] for p in client.get("/progetti", headers=s["admin"]).json()}


def test_macchina_condivisa_fra_due_reparti(client):
    s = _scenario(client)
    m = client.post("/macchine", json={
        "nome": "Linea 3",
        "reparti_ids": [s["automazione"]["id"], s["digitale"]["id"]],
    }, headers=s["admin"])
    assert m.status_code == 201 and len(m.json()["reparti"]) == 2

    for chi in ("anna", "dino"):
        nomi = [x["nome"] for x in client.get("/macchine", headers=s[chi]).json()]
        assert nomi.count("Linea 3") == 1


def test_reparto_di_un_altra_azienda_rifiutato(client):
    s = _scenario(client)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    suo = client.post("/reparti", json={"nome": "Loro"}, headers=altra).json()
    r = client.post("/progetti", json={"nome": "X", "reparti_ids": [suo["id"]]}, headers=s["admin"])
    assert r.status_code == 404


def test_eliminare_un_reparto_lo_toglie_solo_da_dove_serve(client):
    """Il progetto condiviso resta, e conserva l'altro reparto."""
    s = _scenario(client)
    p = client.post("/progetti", json={
        "nome": "Condiviso",
        "reparti_ids": [s["automazione"]["id"], s["digitale"]["id"]],
    }, headers=s["admin"]).json()

    assert client.delete(f"/reparti/{s['digitale']['id']}", headers=s["admin"]).status_code == 204

    rimasti = client.get("/progetti", headers=s["admin"]).json()
    condiviso = [x for x in rimasti if x["nome"] == "Condiviso"][0]
    assert [r["nome"] for r in condiviso["reparti"]] == ["Automazione"]


# ---------- TOGLIERE QUALCUNO DA UN REPARTO ----------

def test_togliere_un_membro_gli_toglie_anche_la_vista(client):
    """Non basta che sparisca dall'elenco del reparto: da quel momento non
    deve piu' vedere i progetti che vedeva grazie a quel reparto. E' lo
    stesso controllo dell'ingresso, guardato al contrario."""
    s = _scenario(client)
    anna_id = _id_utente(client, s["admin"], "anna@a.it")

    # prima: Anna vede il progetto di Automazione
    assert "Quadro" in {p["nome"] for p in client.get("/progetti", headers=s["anna"]).json()}

    r = client.delete(f"/reparti/{s['automazione']['id']}/membri/{anna_id}",
                      headers=s["admin"])
    assert r.status_code == 200

    # non risulta piu' fra i reparti di Anna...
    anna = [u for u in client.get("/utenti", headers=s["admin"]).json()
            if u["email"] == "anna@a.it"][0]
    assert anna["reparti"] == []

    # ...e dopo, le resta solo il generale
    assert {p["nome"] for p in client.get("/progetti", headers=s["anna"]).json()} == {"Generale"}


def test_togliere_due_volte_non_da_errore(client):
    """Ripetere l'operazione porta allo stesso risultato: non e' un guasto,
    e' gia' fatto. Utile se qualcuno clicca due volte."""
    s = _scenario(client)
    anna_id = _id_utente(client, s["admin"], "anna@a.it")
    percorso = f"/reparti/{s['automazione']['id']}/membri/{anna_id}"

    assert client.delete(percorso, headers=s["admin"]).status_code == 200
    assert client.delete(percorso, headers=s["admin"]).status_code == 200


def test_solo_l_admin_toglie_dai_reparti(client):
    """Un caposquadra coordina il lavoro, non decide chi sta in che reparto."""
    s = _scenario(client)
    dino_id = _id_utente(client, s["admin"], "dino@a.it")

    r = client.delete(f"/reparti/{s['digitale']['id']}/membri/{dino_id}", headers=s["anna"])
    assert r.status_code == 403
    # e Dino e' ancora dentro
    assert "Sito" in {p["nome"] for p in client.get("/progetti", headers=s["dino"]).json()}


def test_non_si_toccano_i_reparti_di_un_altra_azienda(client):
    s = _scenario(client)
    anna_id = _id_utente(client, s["admin"], "anna@a.it")
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    r = client.delete(f"/reparti/{s['automazione']['id']}/membri/{anna_id}", headers=altra)
    assert r.status_code == 404
