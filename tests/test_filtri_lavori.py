"""
Test dei filtri e dell'ordinamento nell'elenco dei lavori.

Due cose contano piu' delle altre e hanno un test ciascuna:

- i filtri SOMMANO, non allargano: nessuno di loro puo' far comparire un
  lavoro che senza filtri non si vedrebbe;
- l'ordine per scadenza mette in fondo i lavori che una scadenza non ce
  l'hanno. Serve un caso esplicito perche' in SQL un NULL non e' ne' grande
  ne' piccolo, e PostgreSQL e SQLite lo mettono in punti diversi: senza,
  sviluppo e produzione darebbero elenchi diversi.
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


def _lavoro(client, headers, progetto, titolo, **extra):
    return client.post("/lavori", json={"titolo": titolo, "progetto_id": progetto,
                                        **extra}, headers=headers).json()


def _titoli(risposta):
    return [l["titolo"] for l in risposta.json()]


# ---------- FILTRO PER PERSONA ----------

def test_filtro_per_assegnatario(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, _ = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    suo = _lavoro(client, a, p["id"], "Quadro bordo macchina")
    _lavoro(client, a, p["id"], "Non suo")
    client.post(f"/lavori/{suo['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    assert _titoli(client.get(f"/lavori?assegnato_a={id_gino}", headers=a)) == ["Quadro bordo macchina"]


def test_solo_miei(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    suo = _lavoro(client, a, p["id"], "Il mio")
    _lavoro(client, a, p["id"], "Di nessuno")
    client.post(f"/lavori/{suo['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    assert _titoli(client.get("/lavori?solo_miei=true", headers=gino)) == ["Il mio"]
    # Per l'admin, che non e' assegnato a niente, "solo i miei" e' vuoto.
    assert _titoli(client.get("/lavori?solo_miei=true", headers=a)) == []


def test_solo_miei_vince_su_assegnato_a(client):
    """Chiedere insieme "i miei" e "quelli di un altro" non deve dare i suoi:
    se no il filtro diventerebbe un modo per guardare il carico altrui."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    suo = _lavoro(client, a, p["id"], "Di Gino")
    client.post(f"/lavori/{suo['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    assert _titoli(client.get(f"/lavori?solo_miei=true&assegnato_a={id_gino}", headers=a)) == []


def test_i_filtri_non_allargano_la_visibilita(client):
    """Il filtro per persona parte sempre da quello che gia' vedo."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, _ = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    suo = _lavoro(client, a, p["id"], "Riservato")
    client.post(f"/lavori/{suo['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    estraneo = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    assert client.get(f"/lavori?assegnato_a={id_gino}", headers=estraneo).json() == []


# ---------- FILTRI CHE SI SOMMANO ----------

def test_i_filtri_si_sommano(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, _ = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    giusto = _lavoro(client, a, p["id"], "Valvola da tarare")
    altro = _lavoro(client, a, p["id"], "Valvola da ordinare")
    for l in (giusto, altro):
        client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)
    client.patch(f"/lavori/{giusto['id']}/stato", json={"stato": "in_corso"}, headers=a)

    trovati = client.get(
        f"/lavori?assegnato_a={id_gino}&stato=in_corso&q=valvola", headers=a)
    assert _titoli(trovati) == ["Valvola da tarare"]


# ---------- ORDINAMENTO ----------

def test_ordine_per_scadenza_con_i_senza_data_in_fondo(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    oggi = date.today()

    _lavoro(client, a, p["id"], "Senza data")
    _lavoro(client, a, p["id"], "Fra una settimana",
            data_scadenza=(oggi + timedelta(days=7)).isoformat())
    _lavoro(client, a, p["id"], "Domani",
            data_scadenza=(oggi + timedelta(days=1)).isoformat())

    assert _titoli(client.get("/lavori?ordina=scadenza", headers=a)) == [
        "Domani", "Fra una settimana", "Senza data"]


def test_ordine_per_priorita(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    _lavoro(client, a, p["id"], "Con calma", priorita="bassa")
    _lavoro(client, a, p["id"], "Subito", priorita="urgente")
    _lavoro(client, a, p["id"], "Presto", priorita="alta")

    # L'ordine e' quello che conta davvero, non quello alfabetico
    # (alfabeticamente "alta" verrebbe prima di "urgente").
    assert _titoli(client.get("/lavori?ordina=priorita", headers=a)) == [
        "Subito", "Presto", "Con calma"]


def test_un_ordine_che_non_esiste_viene_rifiutato(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    assert client.get("/lavori?ordina=colore", headers=a).status_code == 422


def test_ordine_predefinito_conclusi_in_fondo_poi_per_priorita(client):
    """E' l'ordine che prima faceva il browser sulla lista gia' scaricata.
    Ora lo fa il server: e' l'unico posto in cui potra' restare giusto quando
    i lavori si scaricheranno a pagine."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()

    _lavoro(client, a, p["id"], "Normale", priorita="normale")
    urgente = _lavoro(client, a, p["id"], "Urgente ma fatto", priorita="urgente")
    _lavoro(client, a, p["id"], "Urgente", priorita="urgente")
    annullato = _lavoro(client, a, p["id"], "Annullato", priorita="urgente")

    client.patch(f"/lavori/{urgente['id']}/stato", json={"stato": "fatto"}, headers=a)
    client.patch(f"/lavori/{annullato['id']}/stato", json={"stato": "annullato"}, headers=a)

    # I due conclusi vanno in fondo anche se sono urgenti; fra i vivi comanda
    # la priorita'.
    titoli = _titoli(client.get("/lavori", headers=a))
    assert titoli[:2] == ["Urgente", "Normale"]
    assert set(titoli[2:]) == {"Urgente ma fatto", "Annullato"}
