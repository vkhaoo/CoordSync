"""
Test della duplicazione di un progetto.

La regola e' una sola e vale la pena ripeterla: si copia la STRUTTURA, non la
STORIA. Ogni test qui sotto verifica un pezzo di quella frase, e i piu'
importanti sono quelli che verificano cosa NON viene copiato — perche' un
progetto che nasce gia' mezzo fatto, o gia' in ritardo, o con venti avvisi
partiti, e' peggio di nessuna duplicazione.
"""
from datetime import date, timedelta

from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _utente(client, admin, nome, email, ruolo="operatore"):
    r = client.post("/utenti", json={"nome": nome, "email": email,
                                     "password": "password1", "ruolo": ruolo}, headers=admin)
    return r.json()["id"], _login(client, email)


def _modello(client, a):
    """Un progetto "modello" con dentro tutto quello che si puo' copiare."""
    p = client.post("/progetti", json={"nome": "Linea 3 - 2025",
                                       "descrizione": "Revamping completo",
                                       "link_documento": "https://drive.example/x"},
                    headers=a).json()
    l = client.post("/lavori", json={"titolo": "Cablaggio quadro",
                                     "descrizione": "come da schema",
                                     "priorita": "alta",
                                     "progetto_id": p["id"],
                                     "data_scadenza": date.today().isoformat()},
                    headers=a).json()
    client.post(f"/lavori/{l['id']}/sotto-attivita", json={"testo": "Stendere i cavi"}, headers=a)
    client.post(f"/lavori/{l['id']}/allegati",
                json={"url": "https://drive.example/schema.pdf", "titolo": "Schema"}, headers=a)
    client.post(f"/progetti/{p['id']}/allegati",
                json={"url": "https://drive.example/capitolato.pdf"}, headers=a)
    return p, l


def test_la_struttura_si_copia(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p, l = _modello(client, a)

    r = client.post(f"/progetti/{p['id']}/duplica", json={"nome": "Linea 3 - 2026"}, headers=a)
    assert r.status_code == 201
    copia = r.json()
    assert copia["nome"] == "Linea 3 - 2026"
    assert copia["descrizione"] == "Revamping completo"
    assert copia["link_documento"] == "https://drive.example/x"
    assert copia["id"] != p["id"]

    lavori = client.get(f"/lavori?progetto_id={copia['id']}", headers=a).json()
    assert [x["titolo"] for x in lavori] == ["Cablaggio quadro"]
    assert lavori[0]["priorita"] == "alta"
    assert lavori[0]["descrizione"] == "come da schema"
    # La checklist si copia, e i link anche: sono materiale di riferimento.
    assert [s["testo"] for s in lavori[0]["sotto_attivita"]] == ["Stendere i cavi"]
    assert [x["titolo"] for x in lavori[0]["allegati"]] == ["Schema"]
    # (i progetti si leggono dall'elenco: un GET del singolo non c'e')
    in_elenco = [x for x in client.get("/progetti", headers=a).json()
                 if x["id"] == copia["id"]][0]
    assert len(in_elenco["allegati"]) == 1


def test_la_copia_nasce_vuota_non_a_meta(client):
    """Stati, spunte e scadenze non si portano dietro: se no il progetto nuovo
    nascerebbe gia' mezzo completato, e gia' in ritardo."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p, l = _modello(client, a)
    client.patch(f"/lavori/{l['id']}/stato", json={"stato": "fatto"}, headers=a)
    passo = client.get(f"/lavori/{l['id']}/sotto-attivita", headers=a).json()[0]
    client.patch(f"/sotto-attivita/{passo['id']}", json={"completata": True}, headers=a)

    copia = client.post(f"/progetti/{p['id']}/duplica",
                        json={"nome": "Nuovo"}, headers=a).json()
    nuovo = client.get(f"/lavori?progetto_id={copia['id']}", headers=a).json()[0]

    assert nuovo["stato"] == "da_fare"
    assert nuovo["data_scadenza"] is None
    assert nuovo["completato_il"] is None
    assert nuovo["sotto_attivita"][0]["completata"] is False


def test_i_commenti_non_si_copiano(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p, l = _modello(client, a)
    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "andata cosi'"}, headers=a)

    copia = client.post(f"/progetti/{p['id']}/duplica", json={"nome": "N"}, headers=a).json()
    nuovo = client.get(f"/lavori?progetto_id={copia['id']}", headers=a).json()[0]
    assert client.get(f"/lavori/{nuovo['id']}/commenti", headers=a).json() == []


def test_gli_assegnatari_non_si_copiano_e_non_parte_nessun_avviso(client):
    """La scelta meno ovvia: spesso e' la stessa squadra. Ma copiarli farebbe
    partire subito venti avvisi per lavori che nessuno ha ancora dato a
    nessuno, e chi duplica lo fa proprio per ripianificare."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p, l = _modello(client, a)
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)
    prima = len(client.get("/notifiche", headers=gino).json()["notifiche"])

    copia = client.post(f"/progetti/{p['id']}/duplica", json={"nome": "N"}, headers=a).json()
    nuovo = client.get(f"/lavori?progetto_id={copia['id']}", headers=a).json()[0]

    assert nuovo["assegnatari"] == []
    assert len(client.get("/notifiche", headers=gino).json()["notifiche"]) == prima


def test_l_originale_non_si_tocca(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p, l = _modello(client, a)
    client.post(f"/progetti/{p['id']}/duplica", json={"nome": "N"}, headers=a)

    vecchi = client.get(f"/lavori?progetto_id={p['id']}", headers=a).json()
    assert len(vecchi) == 1
    assert vecchi[0]["data_scadenza"] is not None
    assert len(vecchi[0]["allegati"]) == 1


def test_i_reparti_si_copiano_tali_e_quali(client):
    """Chi puo' vedere l'originale puo' vedere la copia: ne' piu' ne' meno."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, dino = _utente(client, a, "Dino", "dino@a.it", "caposquadra")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    p = client.post("/progetti", json={"nome": "Riservato",
                                       "reparti_ids": [reparto["id"]]}, headers=a).json()

    copia = client.post(f"/progetti/{p['id']}/duplica", json={"nome": "Copia"}, headers=a).json()
    assert [r["nome"] for r in copia["reparti"]] == ["Automazione"]
    # Dino non e' di quel reparto: non vede ne' l'uno ne' l'altra.
    assert client.get("/progetti", headers=dino).json() == []


def test_un_operatore_non_duplica(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    _, op = _utente(client, a, "Op", "op@a.it")
    p, l = _modello(client, a)
    assert client.post(f"/progetti/{p['id']}/duplica",
                       json={"nome": "N"}, headers=op).status_code == 403


def test_non_si_duplica_il_progetto_di_un_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p, l = _modello(client, a)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    assert client.post(f"/progetti/{p['id']}/duplica",
                       json={"nome": "Rubato"}, headers=altra).status_code == 404
