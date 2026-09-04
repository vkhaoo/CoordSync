"""
Test della scheda macchina: macchine, sezioni, voci del taccuino e allegati.

Punti chiave verificati: la scheda e' un mondo a se' (non riusa i lavori di
progetto), il collegamento fra i due mondi e' facoltativo, e la visibilita'
segue i reparti come per i progetti.
"""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


def _macchina(client, headers, nome="Pressa 1", **extra):
    return client.post("/macchine", json={"nome": nome, **extra}, headers=headers).json()


# ---------- MACCHINE ----------

def test_crea_ed_elenca_macchina(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = client.post("/macchine", json={"nome": "Pressa 1",
                                       "descrizione": "Modello X, matricola 12345"}, headers=a)
    assert r.status_code == 201
    assert r.json()["descrizione"] == "Modello X, matricola 12345"
    assert [m["nome"] for m in client.get("/macchine", headers=a).json()] == ["Pressa 1"]


def test_operatore_non_crea_macchine(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _crea_utente(client, a, "Op", "op@a.it", "operatore")
    assert client.post("/macchine", json={"nome": "X"}, headers=op).status_code == 403


def test_macchine_isolate_fra_aziende(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    assert client.get("/macchine", headers=altra).json() == []
    assert client.get(f"/macchine/{m['id']}", headers=altra).status_code == 404
    assert client.delete(f"/macchine/{m['id']}", headers=altra).status_code == 404


def test_macchine_seguono_il_reparto(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    dino = _crea_utente(client, a, "Dino", "dino@a.it", "caposquadra")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()

    riservata = _macchina(client, a, nome="Riservata", reparto_id=reparto["id"])
    _macchina(client, a, nome="Generale")

    # Dino non e' nel reparto: vede solo quella senza reparto.
    assert [m["nome"] for m in client.get("/macchine", headers=dino).json()] == ["Generale"]
    assert client.get(f"/macchine/{riservata['id']}", headers=dino).status_code == 404


# ---------- SEZIONI ----------

def test_sezioni_con_nomi_liberi(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    for i, nome in enumerate(["Confezione", "Finizione", "FAZ"]):
        r = client.post(f"/macchine/{m['id']}/sezioni", json={"nome": nome, "ordine": i}, headers=a)
        assert r.status_code == 201

    scheda = client.get(f"/macchine/{m['id']}", headers=a).json()
    assert [s["nome"] for s in scheda["sezioni"]] == ["Confezione", "Finizione", "FAZ"]


def test_eliminare_una_sezione_non_cancella_le_voci(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    sez = client.post(f"/macchine/{m['id']}/sezioni", json={"nome": "Confezione"}, headers=a).json()
    client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "modifica", "titolo": "Sostituito sensore", "sezioni_ids": [sez["id"]],
    }, headers=a)

    assert client.delete(f"/sezioni/{sez['id']}", headers=a).status_code == 204
    # La voce resta nella macchina, ha solo perso la sezione.
    voci = client.get(f"/macchine/{m['id']}/voci", headers=a).json()
    assert len(voci) == 1 and voci[0]["sezioni"] == []


# ---------- VOCI ----------

def test_voce_nel_generale_in_sezione_o_in_entrambi(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    sez = client.post(f"/macchine/{m['id']}/sezioni", json={"nome": "FAZ"}, headers=a).json()

    solo_generale = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "informazione", "titolo": "PLC S7-1200", "in_generale": True}, headers=a).json()
    solo_sezione = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "analisi", "titolo": "Vibrazioni", "in_generale": False,
        "sezioni_ids": [sez["id"]]}, headers=a).json()
    entrambi = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "modifica", "titolo": "Nuovo inverter", "in_generale": True,
        "sezioni_ids": [sez["id"]]}, headers=a).json()

    assert solo_generale["in_generale"] is True and solo_generale["sezioni"] == []
    assert solo_sezione["in_generale"] is False and len(solo_sezione["sezioni"]) == 1
    assert entrambi["in_generale"] is True and len(entrambi["sezioni"]) == 1


def test_voce_lavoro_ha_stato_le_altre_no(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)

    lavoro = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "lavoro", "titolo": "Tarare valvola", "stato": "da_fare"}, headers=a).json()
    assert lavoro["stato"] == "da_fare"

    # Su un'analisi lo stato non ha senso: viene azzerato anche se lo mando.
    analisi = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "analisi", "titolo": "Misure", "stato": "da_fare"}, headers=a).json()
    assert analisi["stato"] is None


def test_avanzamento_di_una_voce_lavoro(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    v = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "lavoro", "titolo": "Tarare valvola", "stato": "da_fare"}, headers=a).json()

    for stato in ["in_corso", "fatto"]:
        r = client.patch(f"/voci/{v['id']}", json={"stato": stato}, headers=a)
        assert r.status_code == 200 and r.json()["stato"] == stato


def test_filtri_sullo_storico(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    sez = client.post(f"/macchine/{m['id']}/sezioni", json={"nome": "FAZ"}, headers=a).json()
    client.post(f"/macchine/{m['id']}/voci", json={"tipo": "lavoro", "titolo": "L"}, headers=a)
    client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "guasto" if False else "modifica", "titolo": "M",
        "sezioni_ids": [sez["id"]]}, headers=a)

    # Senza filtri: lo storico completo.
    assert len(client.get(f"/macchine/{m['id']}/voci", headers=a).json()) == 2
    # Per tipo e per sezione.
    assert len(client.get(f"/macchine/{m['id']}/voci?tipo=lavoro", headers=a).json()) == 1
    assert len(client.get(f"/macchine/{m['id']}/voci?sezione_id={sez['id']}", headers=a).json()) == 1


def test_operatore_puo_scrivere_ma_non_toccare_le_voci_altrui(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _crea_utente(client, a, "Op", "op@a.it", "operatore")
    m = _macchina(client, a)

    # Un operatore che trova un guasto deve poterlo annotare.
    sua = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "lavoro", "titolo": "Trovata perdita d'aria"}, headers=op)
    assert sua.status_code == 201
    assert sua.json()["autore"]["nome"] == "Op"

    # La sua puo' modificarla...
    assert client.patch(f"/voci/{sua.json()['id']}", json={"titolo": "X"}, headers=op).status_code == 200
    # ...ma non quella di un altro.
    altrui = client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "modifica", "titolo": "Mia"}, headers=a).json()
    assert client.patch(f"/voci/{altrui['id']}", json={"titolo": "X"}, headers=op).status_code == 403
    assert client.delete(f"/voci/{altrui['id']}", headers=op).status_code == 403


def test_non_posso_usare_la_sezione_di_un_altra_macchina(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m1 = _macchina(client, a, nome="Pressa 1")
    m2 = _macchina(client, a, nome="Pressa 2")
    sez2 = client.post(f"/macchine/{m2['id']}/sezioni", json={"nome": "FAZ"}, headers=a).json()

    r = client.post(f"/macchine/{m1['id']}/voci", json={
        "tipo": "modifica", "titolo": "X", "sezioni_ids": [sez2["id"]]}, headers=a)
    assert r.status_code == 404


def test_voci_invisibili_fuori_dal_reparto(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    dino = _crea_utente(client, a, "Dino", "dino@a.it", "caposquadra")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    m = _macchina(client, a, nome="Riservata", reparto_id=reparto["id"])
    v = client.post(f"/macchine/{m['id']}/voci", json={"tipo": "modifica", "titolo": "X"},
                    headers=a).json()

    assert client.get(f"/macchine/{m['id']}/voci", headers=dino).status_code == 404
    assert client.post(f"/macchine/{m['id']}/voci", json={"tipo": "modifica", "titolo": "Y"},
                       headers=dino).status_code == 404
    assert client.patch(f"/voci/{v['id']}", json={"titolo": "Z"}, headers=dino).status_code == 404


# ---------- COLLEGAMENTO FACOLTATIVO CON PROGETTI E LAVORI ----------

def test_progetto_e_lavoro_possono_puntare_a_una_macchina(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)

    p = client.post("/progetti", json={"nome": "Revamping", "macchina_id": m["id"]}, headers=a)
    assert p.status_code == 201 and p.json()["macchina_id"] == m["id"]

    l = client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p.json()["id"],
                                     "macchina_id": m["id"]}, headers=a)
    assert l.status_code == 201 and l.json()["macchina_id"] == m["id"]


def test_il_collegamento_e_facoltativo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Senza macchina"}, headers=a)
    assert p.status_code == 201 and p.json()["macchina_id"] is None


def test_non_posso_collegare_una_macchina_che_non_vedo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    r = client.post("/progetti", json={"nome": "Furbata", "macchina_id": m["id"]}, headers=altra)
    assert r.status_code == 404


def test_eliminare_la_macchina_non_cancella_progetti_e_lavori(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    p = client.post("/progetti", json={"nome": "Revamping", "macchina_id": m["id"]},
                    headers=a).json()

    assert client.delete(f"/macchine/{m['id']}", headers=a).status_code == 204
    # Il progetto resta, ha solo perso il riferimento.
    rimasti = client.get("/progetti", headers=a).json()
    assert len(rimasti) == 1 and rimasti[0]["macchina_id"] is None


# ---------- ALLEGATI ----------

def test_allegati_su_ogni_scheda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    sez = client.post(f"/macchine/{m['id']}/sezioni", json={"nome": "FAZ"}, headers=a).json()
    voce = client.post(f"/macchine/{m['id']}/voci", json={"tipo": "modifica", "titolo": "X"},
                       headers=a).json()
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    for percorso in [f"/macchine/{m['id']}/allegati", f"/sezioni/{sez['id']}/allegati",
                     f"/voci/{voce['id']}/allegati", f"/progetti/{p['id']}/allegati",
                     f"/lavori/{l['id']}/allegati"]:
        r = client.post(percorso, json={"url": "https://esempio.it/foto.jpg",
                                        "titolo": "Foto quadro"}, headers=a)
        assert r.status_code == 201, percorso
        assert r.json()["titolo"] == "Foto quadro"

    # E si rileggono dentro la scheda.
    scheda = client.get(f"/macchine/{m['id']}", headers=a).json()
    assert len(scheda["allegati"]) == 1
    assert len(scheda["sezioni"][0]["allegati"]) == 1
    assert len(client.get(f"/lavori?progetto_id={p['id']}", headers=a).json()[0]["allegati"]) == 1


def test_allegato_eliminabile_da_chi_lo_ha_messo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _crea_utente(client, a, "Op", "op@a.it", "operatore")
    m = _macchina(client, a)

    mio = client.post(f"/macchine/{m['id']}/allegati", json={"url": "https://x.it"},
                      headers=op).json()
    altrui = client.post(f"/macchine/{m['id']}/allegati", json={"url": "https://y.it"},
                         headers=a).json()

    assert client.delete(f"/allegati/{altrui['id']}", headers=op).status_code == 403
    assert client.delete(f"/allegati/{mio['id']}", headers=op).status_code == 204


def test_allegati_spariscono_con_la_macchina(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = _macchina(client, a)
    alle = client.post(f"/macchine/{m['id']}/allegati", json={"url": "https://x.it"},
                       headers=a).json()
    client.delete(f"/macchine/{m['id']}", headers=a)
    # Niente righe orfane: l'allegato non c'e' piu'.
    assert client.delete(f"/allegati/{alle['id']}", headers=a).status_code == 404
