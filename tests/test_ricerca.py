"""
Ricerca testuale su lavori e storico macchina.

Serve quando le liste diventano grosse. Due cose da proteggere: la ricerca non
deve far vedere roba di altri reparti o altre aziende, e i caratteri jolly di
LIKE non devono trasformarsi in un "mostrami tutto".
"""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


# ---------- LAVORI ----------

def _progetto_con_lavori(client, headers):
    p = client.post("/progetti", json={"nome": "P"}, headers=headers).json()
    for titolo, desc in [
        ("Cablaggio morsettiera XT1", "siglatura conduttori"),
        ("Programmazione PLC", "ciclo automatico della pressa"),
        ("Taratura valvola V3", None),
        ("Sostituzione inverter", "vecchio inverter in magazzino"),
    ]:
        client.post("/lavori", json={"titolo": titolo, "descrizione": desc,
                                     "progetto_id": p["id"]}, headers=headers)
    return p


def test_cerco_nel_titolo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto_con_lavori(client, a)
    trovati = client.get(f"/lavori?progetto_id={p['id']}&q=valvola", headers=a).json()
    assert [l["titolo"] for l in trovati] == ["Taratura valvola V3"]


def test_cerco_nella_descrizione(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto_con_lavori(client, a)
    trovati = client.get(f"/lavori?progetto_id={p['id']}&q=magazzino", headers=a).json()
    assert [l["titolo"] for l in trovati] == ["Sostituzione inverter"]


def test_ricerca_senza_distinzione_maiuscole(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto_con_lavori(client, a)
    for termine in ("PLC", "plc", "Plc"):
        trovati = client.get(f"/lavori?progetto_id={p['id']}&q={termine}", headers=a).json()
        assert [l["titolo"] for l in trovati] == ["Programmazione PLC"], termine


def test_ricerca_parziale_in_mezzo_alla_parola(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto_con_lavori(client, a)
    trovati = client.get(f"/lavori?progetto_id={p['id']}&q=morsett", headers=a).json()
    assert [l["titolo"] for l in trovati] == ["Cablaggio morsettiera XT1"]


def test_ricerca_vuota_non_filtra(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = _progetto_con_lavori(client, a)
    assert len(client.get(f"/lavori?progetto_id={p['id']}&q=", headers=a).json()) == 4
    # anche solo spazi: non e' una ricerca
    assert len(client.get(f"/lavori?progetto_id={p['id']}&q=%20%20", headers=a).json()) == 4


def test_i_caratteri_jolly_non_fanno_da_jolly(client):
    """Cercando la percentuale ci si aspettano i lavori che la contengono
    davvero, non tutti quanti."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    client.post("/lavori", json={"titolo": "Regolare al 50% di portata",
                                 "progetto_id": p["id"]}, headers=a)
    client.post("/lavori", json={"titolo": "Altro lavoro", "progetto_id": p["id"]}, headers=a)

    solo_percento = client.get(f"/lavori?progetto_id={p['id']}&q=%25", headers=a).json()
    assert [l["titolo"] for l in solo_percento] == ["Regolare al 50% di portata"]
    # e l'underscore non deve fare da "un carattere qualsiasi"
    assert client.get(f"/lavori?progetto_id={p['id']}&q=_", headers=a).json() == []


def test_la_ricerca_rispetta_i_reparti(client):
    """Il punto piu' importante: cercare non deve aggirare la visibilita'."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    dino = _crea_utente(client, a, "Dino", "dino@a.it", "caposquadra")
    rep = client.post("/reparti", json={"nome": "Riservato"}, headers=a).json()
    p = client.post("/progetti", json={"nome": "Segreto", "reparti_ids": [rep["id"]]},
                    headers=a).json()
    client.post("/lavori", json={"titolo": "Valvola segreta", "progetto_id": p["id"]}, headers=a)

    assert client.get("/lavori?q=valvola", headers=dino).json() == []
    assert [l["titolo"] for l in client.get("/lavori?q=valvola", headers=a).json()] == ["Valvola segreta"]


def test_la_ricerca_rispetta_le_aziende(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    client.post("/lavori", json={"titolo": "Valvola", "progetto_id": p["id"]}, headers=a)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    assert client.get("/lavori?q=valvola", headers=altra).json() == []


def test_ricerca_e_filtri_insieme(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    fatto = client.post("/lavori", json={"titolo": "Valvola A", "progetto_id": p["id"]},
                        headers=a).json()
    client.post("/lavori", json={"titolo": "Valvola B", "progetto_id": p["id"]}, headers=a)
    client.patch(f"/lavori/{fatto['id']}/stato", json={"stato": "fatto"}, headers=a)

    trovati = client.get(f"/lavori?progetto_id={p['id']}&q=valvola&stato=fatto", headers=a).json()
    assert [l["titolo"] for l in trovati] == ["Valvola A"]


# ---------- STORICO MACCHINA ----------

def _macchina_con_storico(client, headers):
    m = client.post("/macchine", json={"nome": "Pressa"}, headers=headers).json()
    sez = client.post(f"/macchine/{m['id']}/sezioni", json={"nome": "FAZ"}, headers=headers).json()
    client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "modifica", "titolo": "Sostituito inverter",
        "testo": "Rifatti i parametri di rampa"}, headers=headers)
    client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "analisi", "titolo": "Vibrazioni cuscinetto",
        "testo": "picco a 120 Hz", "sezioni_ids": [sez["id"]]}, headers=headers)
    client.post(f"/macchine/{m['id']}/voci", json={
        "tipo": "lavoro", "titolo": "Tarare valvola"}, headers=headers)
    return m, sez


def test_cerco_nello_storico_macchina(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, _ = _macchina_con_storico(client, a)
    trovati = client.get(f"/macchine/{m['id']}/voci?q=inverter", headers=a).json()
    assert [v["titolo"] for v in trovati] == ["Sostituito inverter"]


def test_cerco_nel_testo_della_voce(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, _ = _macchina_con_storico(client, a)
    trovati = client.get(f"/macchine/{m['id']}/voci?q=120 Hz", headers=a).json()
    assert [v["titolo"] for v in trovati] == ["Vibrazioni cuscinetto"]


def test_ricerca_dentro_una_sezione(client):
    """Cercando mentre sono dentro una sezione, cerco solo li'."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, sez = _macchina_con_storico(client, a)
    # "valvola" esiste nella macchina ma NON nella sezione FAZ
    assert client.get(f"/macchine/{m['id']}/voci?q=valvola", headers=a).json() != []
    assert client.get(f"/macchine/{m['id']}/voci?sezione_id={sez['id']}&q=valvola",
                      headers=a).json() == []
    # mentre "vibrazioni" c'e'
    trovati = client.get(f"/macchine/{m['id']}/voci?sezione_id={sez['id']}&q=vibrazioni",
                         headers=a).json()
    assert [v["titolo"] for v in trovati] == ["Vibrazioni cuscinetto"]


def test_ricerca_e_tipo_insieme(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, _ = _macchina_con_storico(client, a)
    assert client.get(f"/macchine/{m['id']}/voci?q=inverter&tipo=analisi", headers=a).json() == []
    assert len(client.get(f"/macchine/{m['id']}/voci?q=inverter&tipo=modifica", headers=a).json()) == 1


def test_non_cerco_nelle_macchine_che_non_vedo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, _ = _macchina_con_storico(client, a)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    assert client.get(f"/macchine/{m['id']}/voci?q=inverter", headers=altra).status_code == 404
