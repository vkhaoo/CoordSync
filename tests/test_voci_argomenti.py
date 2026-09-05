"""
Raggruppamento delle voci di una macchina per argomento.

Lo storico di una macchina era un elenco piatto: l'analisi di un problema, la
modifica che l'ha risolto e il lavoro che e' servito stavano su tre righe che
non si sapevano collegate. Ora una voce puo' stare SOTTO un'altra, come i
lavori stanno sotto un progetto.

Le due cose che questi test proteggono:
- **un solo livello**, se no la scheda diventa un albero in cui non si ritrova
  piu' niente;
- **cancellare un argomento non cancella la storia**: le voci che stavano sotto
  restano, sciolte. In una scheda che vive per anni sarebbe il danno peggiore.
"""
from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login",
                      json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _voce(client, headers, macchina_id, titolo, tipo="analisi", **extra):
    return client.post(f"/macchine/{macchina_id}/voci",
                       json={"tipo": tipo, "titolo": titolo, **extra},
                       headers=headers).json()


def _scenario(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    m = client.post("/macchine", json={"nome": "Pressa"}, headers=a).json()
    argomento = _voce(client, a, m["id"], "Perdita d'aria sulla FAZ")
    return a, m, argomento


# ---------- RAGGRUPPARE ----------

def test_una_voce_sta_sotto_un_argomento(client):
    a, m, argomento = _scenario(client)

    figlia = _voce(client, a, m["id"], "Sostituita guarnizione", tipo="modifica",
                   genitore_id=argomento["id"])
    assert figlia["genitore_id"] == argomento["id"]

    # e si ritrova leggendo lo storico
    voci = client.get(f"/macchine/{m['id']}/voci", headers=a).json()
    per_titolo = {v["titolo"]: v["genitore_id"] for v in voci}
    assert per_titolo["Sostituita guarnizione"] == argomento["id"]
    assert per_titolo["Perdita d'aria sulla FAZ"] is None


def test_si_puo_spostare_una_voce_sotto_un_argomento_dopo(client):
    """Quasi sempre l'argomento si capisce dopo: prima si scrive l'analisi,
    poi ci si accorge che quella modifica c'entrava."""
    a, m, argomento = _scenario(client)
    sciolta = _voce(client, a, m["id"], "Ritarata valvola", tipo="modifica")

    r = client.patch(f"/voci/{sciolta['id']}",
                     json={"genitore_id": argomento["id"]}, headers=a)
    assert r.status_code == 200
    assert r.json()["genitore_id"] == argomento["id"]


def test_si_puo_staccare_una_voce_dall_argomento(client):
    a, m, argomento = _scenario(client)
    figlia = _voce(client, a, m["id"], "Sostituita guarnizione",
                   genitore_id=argomento["id"])

    r = client.patch(f"/voci/{figlia['id']}", json={"genitore_id": None}, headers=a)
    assert r.status_code == 200
    assert r.json()["genitore_id"] is None


def test_modificare_altro_non_stacca_la_voce(client):
    """Cambiare il titolo non deve far cadere il raggruppamento: il campo
    assente e il campo a null sono cose diverse."""
    a, m, argomento = _scenario(client)
    figlia = _voce(client, a, m["id"], "Sostituita guarnizione",
                   genitore_id=argomento["id"])

    r = client.patch(f"/voci/{figlia['id']}", json={"titolo": "Guarnizione nuova"},
                     headers=a)
    assert r.json()["genitore_id"] == argomento["id"]


# ---------- UN SOLO LIVELLO ----------

def test_non_si_annida_piu_di_un_livello(client):
    a, m, argomento = _scenario(client)
    figlia = _voce(client, a, m["id"], "Sostituita guarnizione",
                   genitore_id=argomento["id"])

    r = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "lavoro", "titolo": "Nipote",
                          "genitore_id": figlia["id"]}, headers=a)
    assert r.status_code == 400
    assert "livello" in r.json()["detail"]


def test_un_argomento_con_voci_sotto_non_diventa_figlia(client):
    """L'altra strada per arrivare a due livelli: prendere un argomento che ha
    gia' roba sotto e infilarlo sotto un altro."""
    a, m, argomento = _scenario(client)
    _voce(client, a, m["id"], "Sostituita guarnizione", genitore_id=argomento["id"])
    altro = _voce(client, a, m["id"], "Manutenzione programmata")

    r = client.patch(f"/voci/{argomento['id']}",
                     json={"genitore_id": altro["id"]}, headers=a)
    assert r.status_code == 400
    assert "sotto di se" in r.json()["detail"]


def test_una_voce_non_sta_sotto_se_stessa(client):
    a, m, argomento = _scenario(client)
    r = client.patch(f"/voci/{argomento['id']}",
                     json={"genitore_id": argomento["id"]}, headers=a)
    assert r.status_code == 400


def test_l_argomento_dev_essere_della_stessa_macchina(client):
    a, m, argomento = _scenario(client)
    altra_macchina = client.post("/macchine", json={"nome": "Banco prova"}, headers=a).json()

    r = client.post(f"/macchine/{altra_macchina['id']}/voci",
                    json={"tipo": "lavoro", "titolo": "Sbagliata",
                          "genitore_id": argomento["id"]}, headers=a)
    assert r.status_code == 400
    assert "questa macchina" in r.json()["detail"]


def test_non_si_usa_come_argomento_una_voce_di_un_altra_azienda(client):
    a, m, argomento = _scenario(client)
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    sua = client.post("/macchine", json={"nome": "Sua"}, headers=altra).json()

    r = client.post(f"/macchine/{sua['id']}/voci",
                    json={"tipo": "lavoro", "titolo": "Spia",
                          "genitore_id": argomento["id"]}, headers=altra)
    assert r.status_code == 400


# ---------- CANCELLARE NON DISTRUGGE LA STORIA ----------

def test_cancellare_l_argomento_lascia_le_voci_sotto(client):
    a, m, argomento = _scenario(client)
    _voce(client, a, m["id"], "Sostituita guarnizione", genitore_id=argomento["id"])
    _voce(client, a, m["id"], "Ritarata valvola", genitore_id=argomento["id"])

    assert client.delete(f"/voci/{argomento['id']}", headers=a).status_code == 204

    voci = client.get(f"/macchine/{m['id']}/voci", headers=a).json()
    assert sorted(v["titolo"] for v in voci) == ["Ritarata valvola", "Sostituita guarnizione"]
    # sono tornate sciolte, non sono sparite con l'argomento
    assert all(v["genitore_id"] is None for v in voci)
