"""
Allegati: i link appesi alle schede (progetto, lavoro, macchina, sezione, voce).

Sono link e non file veri perche' il piano gratuito non ha uno spazio dove
tenere i file. La cosa da proteggere non e' il link in se': e' che appendere
un allegato non diventi un modo per toccare (o scoprire l'esistenza di) una
scheda che non si dovrebbe vedere. Percio' ogni endpoint qui sotto ha la sua
prova con un utente di un'altra azienda.
"""
from tests.conftest import registra

LINK = "https://drive.example.com/schema-quadro.pdf"


def _login(client, email):
    tok = client.post("/auth/login",
                      json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _scenario(client):
    """Un'azienda con un progetto, un lavoro, una macchina, una sezione e una voce."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "Linea 3"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p["id"]},
                    headers=a).json()
    m = client.post("/macchine", json={"nome": "Pressa"}, headers=a).json()
    s = client.post(f"/macchine/{m['id']}/sezioni", json={"nome": "Confezione"},
                    headers=a).json()
    v = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "modifica", "titolo": "Sostituito sensore"},
                    headers=a).json()
    return a, p, l, m, s, v


# ---------- SI ATTACCA A TUTTO ----------

def test_link_su_progetto_e_lavoro(client):
    a, p, l, _, _, _ = _scenario(client)

    r = client.post(f"/progetti/{p['id']}/allegati",
                    json={"url": LINK, "titolo": "Schema"}, headers=a)
    assert r.status_code == 201
    assert r.json()["titolo"] == "Schema"

    r = client.post(f"/lavori/{l['id']}/allegati", json={"url": LINK}, headers=a)
    assert r.status_code == 201
    # Senza titolo si mostrera' il link: il campo resta vuoto, non inventato.
    assert r.json()["titolo"] is None


def test_link_su_macchina_sezione_e_voce(client):
    a, _, _, m, s, v = _scenario(client)

    for percorso in (f"/macchine/{m['id']}/allegati",
                     f"/sezioni/{s['id']}/allegati",
                     f"/voci/{v['id']}/allegati"):
        assert client.post(percorso, json={"url": LINK}, headers=a).status_code == 201

    # E si ritrovano leggendo la scheda, ognuno appeso dove e' stato messo.
    scheda = client.get(f"/macchine/{m['id']}", headers=a).json()
    assert [x["url"] for x in scheda["allegati"]] == [LINK]
    assert [x["url"] for x in scheda["sezioni"][0]["allegati"]] == [LINK]


# ---------- NON SI ATTACCA A QUELLO DEGLI ALTRI ----------

def test_un_estraneo_non_appende_niente(client):
    """Il 404 (e non il 403) e' voluto: a chi non deve vedere una scheda non si
    dice nemmeno che esiste."""
    a, p, l, m, s, v = _scenario(client)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    percorsi = [
        f"/progetti/{p['id']}/allegati",
        f"/lavori/{l['id']}/allegati",
        f"/macchine/{m['id']}/allegati",
        f"/sezioni/{s['id']}/allegati",
        f"/voci/{v['id']}/allegati",
    ]
    for percorso in percorsi:
        r = client.post(percorso, json={"url": LINK}, headers=altra)
        assert r.status_code == 404, percorso


def test_un_estraneo_non_cancella_un_allegato(client):
    a, _, _, m, _, _ = _scenario(client)
    allegato = client.post(f"/macchine/{m['id']}/allegati",
                           json={"url": LINK}, headers=a).json()
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")

    assert client.delete(f"/allegati/{allegato['id']}", headers=altra).status_code == 404
    # ed e' ancora al suo posto
    scheda = client.get(f"/macchine/{m['id']}", headers=a).json()
    assert len(scheda["allegati"]) == 1


def test_chi_ci_lavora_puo_toglierlo(client):
    a, _, _, m, _, _ = _scenario(client)
    allegato = client.post(f"/macchine/{m['id']}/allegati",
                           json={"url": LINK}, headers=a).json()

    assert client.delete(f"/allegati/{allegato['id']}", headers=a).status_code == 204
    assert client.get(f"/macchine/{m['id']}", headers=a).json()["allegati"] == []
