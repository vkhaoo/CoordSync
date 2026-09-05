"""
Ricerca unica: una parola sola cercata in tutta l'app.

La cosa importante non e' che trovi: e' che **non trovi quello che non si deve
vedere**. Una ricerca che attraversa tutto e' il posto piu' facile dove
scavalcare per sbaglio i confini fra aziende e fra reparti, perche' tocca
cinque tabelle in un colpo. Meta' di questo file serve a quello.
"""
from datetime import datetime, timedelta

from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login",
                      json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo="caposquadra"):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


def _id_utente(client, admin, email):
    return [u for u in client.get("/utenti", headers=admin).json()
            if u["email"] == email][0]["id"]


def _cerca(client, headers, q):
    r = client.get(f"/ricerca?q={q}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- TROVA DAPPERTUTTO ----------

def test_trova_la_stessa_parola_in_ogni_angolo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Revisione valvola"}, headers=a).json()
    client.post("/lavori", json={"titolo": "Smontare la valvola V7",
                                 "progetto_id": p["id"]}, headers=a)
    # "Banco valvole" NON verrebbe trovato cercando "valvola": si cerca il
    # testo cosi' com'e', senza capire che valvola e valvole sono la stessa
    # parola. E' un limite noto e voluto (vedi il commento in ricerca.py).
    m = client.post("/macchine", json={"nome": "Banco prova valvola"}, headers=a).json()
    client.post(f"/macchine/{m['id']}/voci",
                json={"tipo": "analisi", "titolo": "Perdita dalla valvola"}, headers=a)
    quando = (datetime.now() + timedelta(days=2)).replace(microsecond=0).isoformat()
    client.post("/agenda", json={"titolo": "Collaudo valvola", "inizio": quando}, headers=a)

    r = _cerca(client, a, "valvola")

    assert [x["nome"] for x in r["progetti"]] == ["Revisione valvola"]
    assert [x["titolo"] for x in r["lavori"]] == ["Smontare la valvola V7"]
    assert [x["nome"] for x in r["macchine"]] == ["Banco prova valvola"]
    assert [x["titolo"] for x in r["voci"]] == ["Perdita dalla valvola"]
    assert [x["titolo"] for x in r["impegni"]] == ["Collaudo valvola"]


def test_i_risultati_dicono_dove_sono(client):
    """Un titolo da solo non basta a orientarsi: serve sapere in che progetto
    o su che macchina sta."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Linea 3"}, headers=a).json()
    client.post("/lavori", json={"titolo": "Cablaggio XT1", "progetto_id": p["id"]}, headers=a)
    m = client.post("/macchine", json={"nome": "Pressa"}, headers=a).json()
    client.post(f"/macchine/{m['id']}/voci",
                json={"tipo": "modifica", "titolo": "Cablaggio rifatto"}, headers=a)

    r = _cerca(client, a, "cablaggio")
    assert r["lavori"][0]["progetto"] == "Linea 3"
    assert r["lavori"][0]["progetto_id"] == p["id"]
    assert r["voci"][0]["macchina"] == "Pressa"


def test_cerca_anche_nelle_descrizioni(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Linea 3"}, headers=a).json()
    client.post("/lavori", json={"titolo": "Quadro", "progetto_id": p["id"],
                                 "descrizione": "morsettiera siglata"}, headers=a)

    assert [x["titolo"] for x in _cerca(client, a, "morsettiera")["lavori"]] == ["Quadro"]


def test_niente_da_trovare_non_e_un_errore(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    r = _cerca(client, a, "qualcosachenonesiste")
    assert r == {"progetti": [], "lavori": [], "macchine": [], "voci": [], "impegni": []}


def test_una_lettera_sola_non_si_cerca(client):
    """Con un carattere tornerebbe mezzo database: non aiuta e costa."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.get("/ricerca?q=v", headers=a).status_code == 422


def test_i_caratteri_jolly_non_fanno_danni(client):
    """Cercare '%' deve cercare il carattere per cento, non restituire tutto."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/progetti", json={"nome": "Sconto 50% fornitore"}, headers=a)
    client.post("/progetti", json={"nome": "Linea 3"}, headers=a)

    r = _cerca(client, a, "50%")
    assert [x["nome"] for x in r["progetti"]] == ["Sconto 50% fornitore"]


def test_senza_accesso_non_si_cerca(client):
    assert client.get("/ricerca?q=valvola").status_code == 403


# ---------- NON TROVA QUELLO CHE NON SI DEVE VEDERE ----------

def test_non_si_cerca_in_casa_d_altri(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Segreto industriale"}, headers=a).json()
    client.post("/lavori", json={"titolo": "Segreto anche questo",
                                 "progetto_id": p["id"]}, headers=a)
    client.post("/macchine", json={"nome": "Macchina segreta"}, headers=a)

    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    r = _cerca(client, altra, "segret")

    assert r["progetti"] == [] and r["lavori"] == [] and r["macchine"] == []


def test_la_ricerca_non_scavalca_i_reparti(client):
    """Il punto piu' delicato: cercare non deve diventare la scorciatoia per
    vedere quello che i reparti nascondono."""
    admin = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, admin, "Anna", "anna@a.it")
    automazione = client.post("/reparti", json={"nome": "Automazione"}, headers=admin).json()
    digitale = client.post("/reparti", json={"nome": "Digitale"}, headers=admin).json()
    client.post(f"/reparti/{automazione['id']}/membri",
                json={"utente_id": _id_utente(client, admin, "anna@a.it")}, headers=admin)

    # roba del reparto di Anna, roba dell'altro reparto, e roba generale
    client.post("/progetti", json={"nome": "Valvola mia",
                                   "reparti_ids": [automazione["id"]]}, headers=admin)
    client.post("/progetti", json={"nome": "Valvola altrui",
                                   "reparti_ids": [digitale["id"]]}, headers=admin)
    client.post("/progetti", json={"nome": "Valvola di tutti"}, headers=admin)
    client.post("/macchine", json={"nome": "Valvoliera riservata",
                                   "reparti_ids": [digitale["id"]]}, headers=admin)

    r = _cerca(client, anna, "valvol")

    assert sorted(x["nome"] for x in r["progetti"]) == ["Valvola di tutti", "Valvola mia"]
    assert r["macchine"] == []
    # e l'admin invece vede tutto
    assert len(_cerca(client, admin, "valvol")["progetti"]) == 3


def test_non_si_trova_lo_storico_di_una_macchina_che_non_vedo(client):
    admin = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, admin, "Anna", "anna@a.it")
    digitale = client.post("/reparti", json={"nome": "Digitale"}, headers=admin).json()
    m = client.post("/macchine", json={"nome": "Pressa",
                                       "reparti_ids": [digitale["id"]]}, headers=admin).json()
    client.post(f"/macchine/{m['id']}/voci",
                json={"tipo": "analisi", "titolo": "Perdita d'aria"}, headers=admin)

    assert _cerca(client, anna, "perdita")["voci"] == []
    assert [v["titolo"] for v in _cerca(client, admin, "perdita")["voci"]] == ["Perdita d'aria"]


def test_l_agenda_degli_altri_non_si_cerca(client):
    """Chi partecipa a una riunione la trova; gli altri non devono nemmeno
    sapere che esiste."""
    admin = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, admin, "Anna", "anna@a.it")
    quando = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
    client.post("/agenda", json={"titolo": "Riunione riservata", "inizio": quando},
                headers=admin)

    assert _cerca(client, anna, "riservata")["impegni"] == []
    assert len(_cerca(client, admin, "riservata")["impegni"]) == 1


def test_l_invitato_a_una_riunione_la_trova(client):
    admin = registra(client, "Azienda A", "Marco", "marco@a.it")
    anna = _crea_utente(client, admin, "Anna", "anna@a.it")
    quando = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
    ids = [_id_utente(client, admin, "marco@a.it"), _id_utente(client, admin, "anna@a.it")]
    client.post("/agenda", json={"titolo": "Riunione di cantiere", "inizio": quando,
                                 "partecipanti_ids": ids}, headers=admin)

    assert [i["titolo"] for i in _cerca(client, anna, "cantiere")["impegni"]] == ["Riunione di cantiere"]
