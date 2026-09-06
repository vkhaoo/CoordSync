"""
Test dei commenti e delle checklist sulle VOCI del taccuino di una macchina.

Le due cose riusano le tabelle dei lavori di progetto invece di duplicarle,
quindi qui si verificano soprattutto tre rischi di quella scelta:

- che i due mondi non si MESCOLINO (i commenti di un lavoro non devono
  comparire su una macchina, e viceversa);
- che i permessi del taccuino — piu' aperti — non si allarghino per sbaglio
  anche ai lavori, dove restano quelli di prima;
- che l'isolamento fra aziende e reparti valga anche su questi indirizzi.
"""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _utente(client, admin, nome, email, ruolo):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


def _voce(client, headers, titolo="Perdita d'aria sulla FAZ", **extra):
    m = client.post("/macchine", json={"nome": "Pressa 1"}, headers=headers).json()
    v = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "lavoro", "titolo": titolo, "stato": "da_fare", **extra},
                    headers=headers).json()
    return m, v


# ---------- COMMENTI ----------

def test_si_discute_sotto_una_voce(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, v = _voce(client, a)

    r = client.post(f"/voci/{v['id']}/commenti",
                    json={"testo": "Ho ricontrollato la taratura, era a 6 bar"}, headers=a)
    assert r.status_code == 201
    assert r.json()["autore"]["nome"] == "Marco"

    lista = client.get(f"/voci/{v['id']}/commenti", headers=a).json()
    assert [c["testo"] for c in lista] == ["Ho ricontrollato la taratura, era a 6 bar"]


def test_anche_l_operatore_commenta_una_voce(client):
    """Sul taccuino non esistono assegnatari: chi trova il guasto e' chi passa
    di li'. Sui lavori invece l'operatore deve essere assegnato — regola
    diversa, e resta diversa."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _utente(client, a, "Op", "op@a.it", "operatore")
    m, v = _voce(client, a)

    assert client.post(f"/voci/{v['id']}/commenti",
                       json={"testo": "Fatto io stamattina"}, headers=op).status_code == 201


def test_i_due_mondi_non_si_mescolano(client):
    """Un commento scritto su una macchina non deve comparire su un lavoro che
    per caso ha lo stesso numero, e viceversa."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    lavoro = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    m, v = _voce(client, a)

    client.post(f"/lavori/{lavoro['id']}/commenti", json={"testo": "sul lavoro"}, headers=a)
    client.post(f"/voci/{v['id']}/commenti", json={"testo": "sulla macchina"}, headers=a)

    sul_lavoro = client.get(f"/lavori/{lavoro['id']}/commenti", headers=a).json()
    sulla_voce = client.get(f"/voci/{v['id']}/commenti", headers=a).json()
    assert [c["testo"] for c in sul_lavoro] == ["sul lavoro"]
    assert [c["testo"] for c in sulla_voce] == ["sulla macchina"]


def test_un_estraneo_non_legge_ne_scrive(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, v = _voce(client, a)
    client.post(f"/voci/{v['id']}/commenti", json={"testo": "riservato"}, headers=a)

    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    assert client.get(f"/voci/{v['id']}/commenti", headers=altra).status_code == 404
    assert client.post(f"/voci/{v['id']}/commenti",
                       json={"testo": "ciao"}, headers=altra).status_code == 404


def test_i_commenti_spariscono_con_la_voce(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, v = _voce(client, a)
    client.post(f"/voci/{v['id']}/commenti", json={"testo": "x"}, headers=a)

    assert client.delete(f"/voci/{v['id']}", headers=a).status_code == 204
    assert client.get(f"/voci/{v['id']}/commenti", headers=a).status_code == 404


# ---------- CHECKLIST ----------

def test_checklist_sotto_una_voce(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, v = _voce(client, a)

    r = client.post(f"/voci/{v['id']}/sotto-attivita",
                    json={"testo": "Ordinare la guarnizione"}, headers=a)
    assert r.status_code == 201
    assert r.json()["completata"] is False
    assert r.json()["voce_id"] == v["id"] and r.json()["lavoro_id"] is None

    client.post(f"/voci/{v['id']}/sotto-attivita", json={"testo": "Montarla"}, headers=a)
    lista = client.get(f"/voci/{v['id']}/sotto-attivita", headers=a).json()
    assert [p["testo"] for p in lista] == ["Ordinare la guarnizione", "Montarla"]


def test_la_checklist_viaggia_dentro_la_voce(client):
    """Serve a colpo d'occhio ("1 di 2"), quindi arriva gia' con la scheda,
    senza una seconda chiamata per ogni riga dello storico."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, v = _voce(client, a)
    client.post(f"/voci/{v['id']}/sotto-attivita", json={"testo": "Passo 1"}, headers=a)

    voci = client.get(f"/macchine/{m['id']}/voci", headers=a).json()
    assert [p["testo"] for p in voci[0]["sotto_attivita"]] == ["Passo 1"]

    scheda = client.get(f"/macchine/{m['id']}", headers=a).json()
    assert len(scheda["voci"][0]["sotto_attivita"]) == 1


def test_chiunque_veda_la_macchina_puo_spuntare(client):
    """La spunta la mette chi ha appena fatto la cosa, e sull'impianto e' chi
    passava di li': non c'e' un assegnatario da cui farsi autorizzare."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _utente(client, a, "Op", "op@a.it", "operatore")
    m, v = _voce(client, a)
    passo = client.post(f"/voci/{v['id']}/sotto-attivita",
                        json={"testo": "Ordinare la guarnizione"}, headers=a).json()

    r = client.patch(f"/sotto-attivita/{passo['id']}", json={"completata": True}, headers=op)
    assert r.status_code == 200 and r.json()["completata"] is True


def test_togliere_un_passo_e_modificare_la_voce(client):
    """Aggiungere un passo lo puo' fare chiunque; toglierlo no, perche' cambia
    la voce di qualcun altro."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _utente(client, a, "Op", "op@a.it", "operatore")
    m, v = _voce(client, a)   # la voce e' di Marco
    passo = client.post(f"/voci/{v['id']}/sotto-attivita", json={"testo": "X"}, headers=op).json()

    assert client.delete(f"/sotto-attivita/{passo['id']}", headers=op).status_code == 403
    # L'autore della voce si', e anche chi gestisce.
    assert client.delete(f"/sotto-attivita/{passo['id']}", headers=a).status_code == 204


def test_l_operatore_toglie_i_passi_dalle_proprie_voci(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _utente(client, a, "Op", "op@a.it", "operatore")
    m = client.post("/macchine", json={"nome": "Pressa 1"}, headers=a).json()
    mia = client.post(f"/macchine/{m['id']}/voci",
                      json={"tipo": "analisi", "titolo": "Misure mie"}, headers=op).json()
    passo = client.post(f"/voci/{mia['id']}/sotto-attivita",
                        json={"testo": "Rifare la prova"}, headers=op).json()

    assert client.delete(f"/sotto-attivita/{passo['id']}", headers=op).status_code == 204


def test_sui_lavori_i_permessi_restano_quelli_di_prima(client):
    """Il taccuino e' piu' aperto, ma quell'apertura non deve colare sui lavori:
    li' creare e togliere restano di admin e caposquadra."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    op = _utente(client, a, "Op", "op@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    lavoro = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    passo = client.post(f"/lavori/{lavoro['id']}/sotto-attivita",
                        json={"testo": "X"}, headers=a).json()

    assert client.post(f"/lavori/{lavoro['id']}/sotto-attivita",
                       json={"testo": "Y"}, headers=op).status_code == 403
    # E nemmeno spuntarlo: sul lavoro serve essere assegnati.
    assert client.patch(f"/sotto-attivita/{passo['id']}",
                        json={"completata": True}, headers=op).status_code == 403
    assert client.delete(f"/sotto-attivita/{passo['id']}", headers=op).status_code == 403


def test_estraneo_non_tocca_la_checklist_di_un_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, v = _voce(client, a)
    passo = client.post(f"/voci/{v['id']}/sotto-attivita", json={"testo": "X"}, headers=a).json()

    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    assert client.get(f"/voci/{v['id']}/sotto-attivita", headers=altra).status_code == 404
    assert client.post(f"/voci/{v['id']}/sotto-attivita",
                       json={"testo": "Y"}, headers=altra).status_code == 404
    assert client.patch(f"/sotto-attivita/{passo['id']}",
                        json={"completata": True}, headers=altra).status_code == 404
    assert client.delete(f"/sotto-attivita/{passo['id']}", headers=altra).status_code == 404


def test_la_checklist_sparisce_con_la_voce(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m, v = _voce(client, a)
    passo = client.post(f"/voci/{v['id']}/sotto-attivita", json={"testo": "X"}, headers=a).json()

    assert client.delete(f"/voci/{v['id']}", headers=a).status_code == 204
    assert client.patch(f"/sotto-attivita/{passo['id']}",
                        json={"completata": True}, headers=a).status_code == 404


def test_fuori_dal_mio_reparto_non_esiste(client):
    """La visibilita' passa sempre dalla macchina: una checklist non diventa la
    porta di servizio per sbirciare un reparto che non e' il mio."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    dino = _utente(client, a, "Dino", "dino@a.it", "caposquadra")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    m = client.post("/macchine", json={"nome": "Riservata", "reparti_ids": [reparto["id"]]},
                    headers=a).json()
    v = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": "Misure"}, headers=a).json()
    passo = client.post(f"/voci/{v['id']}/sotto-attivita", json={"testo": "X"}, headers=a).json()

    # Dino non e' di quel reparto: per lui la macchina non esiste, e nemmeno
    # quello che ci sta appeso.
    assert client.get(f"/voci/{v['id']}/commenti", headers=dino).status_code == 404
    assert client.patch(f"/sotto-attivita/{passo['id']}",
                        json={"completata": True}, headers=dino).status_code == 404
