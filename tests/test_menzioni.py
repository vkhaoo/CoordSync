"""
Test delle menzioni: scrivere @Mario in un commento per tirarlo dentro.

Il rischio vero non e' sbagliare a riconoscere un nome, e' che una menzione
diventi un modo per FAR SAPERE che esiste qualcosa che non si dovrebbe vedere:
basterebbe scrivere il nome di un collega di un altro reparto per fargli
comparire in campanella un lavoro riservato, con tanto di titolo e di link.
Per questo il test piu' importante di questo file e' quello sul reparto.
"""
from tests.conftest import registra
from app.menzioni import trova_menzionati


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _utente(client, admin, nome, email, ruolo="operatore"):
    r = client.post("/utenti", json={"nome": nome, "email": email,
                                     "password": "password1", "ruolo": ruolo}, headers=admin)
    return r.json()["id"], _login(client, email)


def _avvisi(client, headers):
    return client.get("/notifiche", headers=headers).json()["notifiche"]


# ---------- IL RICONOSCIMENTO DEL NOME (senza database) ----------

class _Finto:
    def __init__(self, id, nome):
        self.id, self.nome = id, nome


def test_riconosce_il_nome_intero_e_quello_di_battesimo():
    gente = [_Finto(1, "Marco Rossi"), _Finto(2, "Gino Bianchi")]
    assert [p.id for p in trova_menzionati("ci pensa @Marco Rossi", gente)] == [1]
    assert [p.id for p in trova_menzionati("@Gino puoi guardare?", gente)] == [2]


def test_con_due_nomi_uguali_il_solo_battesimo_non_basta():
    """Un avviso a caso e' peggio di nessun avviso: chi scrive crederebbe di
    aver chiamato qualcuno, e quel qualcuno non lo saprebbe mai."""
    gente = [_Finto(1, "Marco Rossi"), _Finto(2, "Marco Bianchi")]
    assert trova_menzionati("@Marco guarda qua", gente) == []
    # Col cognome invece si capisce chi e'.
    assert [p.id for p in trova_menzionati("@Marco Bianchi guarda qua", gente)] == [2]


def test_il_nome_piu_lungo_vince():
    gente = [_Finto(1, "Marco"), _Finto(2, "Marco Rossi")]
    assert [p.id for p in trova_menzionati("@Marco Rossi", gente)] == [2]


def test_accenti_e_maiuscole_non_contano():
    gente = [_Finto(1, "Nicolò")]
    assert [p.id for p in trova_menzionati("@nicolo puoi passare?", gente)] == [1]


def test_senza_chiocciola_non_e_una_menzione():
    gente = [_Finto(1, "Marco")]
    assert trova_menzionati("ne parlavo con Marco ieri", gente) == []


# ---------- DENTRO L'APP ----------

def test_nominare_qualcuno_gli_fa_suonare_la_campanella(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Quadro bordo macchina",
                                     "progetto_id": p["id"]}, headers=a).json()

    client.post(f"/lavori/{l['id']}/commenti",
                json={"testo": "@Gino puoi controllare la taratura?"}, headers=a)

    avvisi = _avvisi(client, gino)
    assert len(avvisi) == 1
    assert avvisi[0]["tipo"] == "menzione"
    assert "ti ha nominato" in avvisi[0]["testo"]
    assert avvisi[0]["lavoro_id"] == l["id"]


def test_una_menzione_non_fa_vedere_niente_di_nuovo(client):
    """IL TEST CHE CONTA. Gino non e' del reparto: quel lavoro non lo vede, e
    scrivere il suo nome non deve cambiarlo."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    p = client.post("/progetti", json={"nome": "Riservato",
                                       "reparti_ids": [reparto["id"]]}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Segreto industriale",
                                     "progetto_id": p["id"]}, headers=a).json()

    client.post(f"/lavori/{l['id']}/commenti",
                json={"testo": "@Gino guarda qua"}, headers=a)

    assert _avvisi(client, gino) == []
    # E il lavoro resta invisibile: la menzione non e' una scorciatoia.
    assert client.get("/lavori", headers=gino).json() == []


def test_chi_e_gia_avvisato_come_assegnatario_non_riceve_due_campanelle(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": id_gino}, headers=a)

    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "@Gino fatto?"}, headers=a)

    # Uno solo, quello dell'assegnazione al commento: due per lo stesso
    # commento sarebbero rumore.
    commenti = [n for n in _avvisi(client, gino) if n["tipo"] in ("commento", "menzione")]
    assert len(commenti) == 1
    assert commenti[0]["tipo"] == "commento"


def test_nominarsi_da_soli_non_suona(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "@Marco ricordati"}, headers=a)
    assert client.get("/notifiche", headers=a).json()["non_lette"] == 0


def test_le_menzioni_valgono_anche_sulle_macchine(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    m = client.post("/macchine", json={"nome": "Pressa 1"}, headers=a).json()
    v = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": "Vibrazioni"}, headers=a).json()

    client.post(f"/voci/{v['id']}/commenti",
                json={"testo": "@Gino te la ricordi questa?"}, headers=a)

    avvisi = _avvisi(client, gino)
    assert len(avvisi) == 1 and avvisi[0]["tipo"] == "menzione"
    assert avvisi[0]["macchina_id"] == m["id"]


def test_su_una_macchina_di_un_altro_reparto_la_menzione_tace(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    id_gino, gino = _utente(client, a, "Gino", "gino@a.it")
    reparto = client.post("/reparti", json={"nome": "Automazione"}, headers=a).json()
    m = client.post("/macchine", json={"nome": "Riservata",
                                       "reparti_ids": [reparto["id"]]}, headers=a).json()
    v = client.post(f"/macchine/{m['id']}/voci",
                    json={"tipo": "analisi", "titolo": "Misure"}, headers=a).json()

    client.post(f"/voci/{v['id']}/commenti", json={"testo": "@Gino guarda"}, headers=a)
    assert _avvisi(client, gino) == []


def test_non_si_nomina_qualcuno_di_un_altra_azienda(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    altra = registra(client, "Azienda B", "Gino", "gino@b.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "@Gino ciao"}, headers=a)
    assert _avvisi(client, altra) == []
