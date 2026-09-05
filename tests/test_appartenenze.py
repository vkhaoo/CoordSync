"""
Le tessere di appartenenza: chi lavora dove, e con che ruolo.

Primo strato del multi-azienda. Qui si verifica solo che la tessera nasca
insieme all'utente e resti allineata: il comportamento dell'app non cambia
ancora di una virgola, ed e' voluto. Una migrazione che sposta dati e una che
cambia logica non devono viaggiare insieme, se no quando qualcosa va storto
non si sa quale delle due incolpare.
"""
from app.database import SessionLocal
from app.models.appartenenza import Appartenenza
from tests.conftest import registra


def _tessere(email: str) -> list[Appartenenza]:
    """Le tessere di una persona, lette direttamente dal database."""
    db = SessionLocal()
    try:
        from app.models.utente import Utente
        utente = db.query(Utente).filter(Utente.email == email).first()
        if utente is None:
            return []
        return list(db.query(Appartenenza)
                    .filter(Appartenenza.utente_id == utente.id).all())
    finally:
        db.close()


def _login(client, email, password="password1"):
    tok = client.post("/auth/login",
                      json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _id(client, admin, email):
    return [u for u in client.get("/utenti", headers=admin).json()
            if u["email"] == email][0]["id"]


# ---------- LA TESSERA NASCE CON L'UTENTE ----------

def test_chi_registra_un_azienda_ne_diventa_membro_admin(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")

    tessere = _tessere("marco@a.it")
    assert len(tessere) == 1
    assert tessere[0].ruolo.value == "admin"


def test_un_collega_creato_dall_admin_ha_la_sua_tessera(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it",
                                 "password": "password1", "ruolo": "caposquadra"},
                headers=a)

    tessere = _tessere("luca@a.it")
    assert len(tessere) == 1
    assert tessere[0].ruolo.value == "caposquadra"
    # ed e' l'azienda di chi l'ha creato, non un'altra
    assert tessere[0].organizzazione_id == _tessere("marco@a.it")[0].organizzazione_id


def test_anche_chi_arriva_per_invito_ha_la_tessera(client):
    """L'invitato nasce senza password: la tessera pero' deve esserci
    subito, se no accettando l'invito entrerebbe e non vedrebbe niente."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti/invita", json={"nome": "Anna", "email": "anna@a.it",
                                        "ruolo": "operatore"}, headers=a)

    tessere = _tessere("anna@a.it")
    assert len(tessere) == 1
    assert tessere[0].ruolo.value == "operatore"


def test_due_aziende_diverse_hanno_tessere_diverse(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")
    registra(client, "Azienda B", "Bruno", "bruno@b.it")

    org_marco = _tessere("marco@a.it")[0].organizzazione_id
    org_bruno = _tessere("bruno@b.it")[0].organizzazione_id
    assert org_marco != org_bruno


# ---------- LA TESSERA RESTA ALLINEATA ----------

def test_cambiare_ruolo_cambia_anche_la_tessera(client):
    """Il ruolo vive sulla tessera: se cambiasse solo sulla riga dell'utente,
    il giorno che si guarda la tessera si leggerebbe quello vecchio."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it",
                                 "password": "password1", "ruolo": "operatore"},
                headers=a)

    client.patch(f"/utenti/{_id(client, a, 'luca@a.it')}/ruolo",
                 json={"ruolo": "caposquadra"}, headers=a)

    assert _tessere("luca@a.it")[0].ruolo.value == "caposquadra"


# ---------- NIENTE E' CAMBIATO PER CHI USA L'APP ----------

def test_l_app_si_comporta_esattamente_come_prima(client):
    """Rete di sicurezza dello strato 1: le tessere esistono ma non le usa
    ancora nessuno, quindi permessi e visibilita' devono essere identici."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    client.post("/utenti", json={"nome": "Luca", "email": "luca@a.it",
                                 "password": "password1", "ruolo": "operatore"},
                headers=a)
    luca = _login(client, "luca@a.it")
    p = client.post("/progetti", json={"nome": "Linea 3"}, headers=a).json()

    # l'admin crea, l'operatore no
    assert client.post("/progetti", json={"nome": "Suo"}, headers=luca).status_code == 403
    # e un estraneo non vede niente
    altra = registra(client, "Azienda B", "Bruno", "bruno@b.it")
    assert client.get("/progetti", headers=altra).json() == []
    assert [x["nome"] for x in client.get("/progetti", headers=a).json()] == ["Linea 3"]
    # L'elenco dei lavori filtra per visibilita': a chi non deve vedere quel
    # progetto torna vuoto (non un errore, ma nemmeno una riga di dati).
    assert client.get(f"/lavori?progetto_id={p['id']}", headers=altra).json() == []
