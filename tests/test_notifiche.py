"""
Avvisi in-app (la campanella).

Due cose da proteggere: nessuno deve ricevere l'avviso di un gesto suo (la
campanella suonerebbe a vuoto), e nessuno deve poter leggere gli avvisi di un
collega.
"""
from datetime import date, datetime, timedelta

from tests.conftest import registra


def _login(client, email):
    tok = client.post("/auth/login", json={"email": email, "password": "password1"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _crea_utente(client, admin, nome, email, ruolo):
    client.post("/utenti", json={"nome": nome, "email": email,
                                 "password": "password1", "ruolo": ruolo}, headers=admin)
    return _login(client, email)


def _id_utente(client, admin, email):
    return [u for u in client.get("/utenti", headers=admin).json() if u["email"] == email][0]["id"]


def _avvisi(client, headers):
    return client.get("/notifiche", headers=headers).json()


# ---------- ASSEGNAZIONE ----------

def test_assegnare_un_lavoro_avvisa_la_persona(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Cablaggio", "progetto_id": p["id"]},
                    headers=a).json()

    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "luca@a.it")}, headers=a)

    avvisi = _avvisi(client, luca)
    assert avvisi["non_lette"] == 1
    assert avvisi["notifiche"][0]["tipo"] == "assegnazione"
    assert "Marco" in avvisi["notifiche"][0]["testo"]
    assert "Cablaggio" in avvisi["notifiche"][0]["testo"]
    assert avvisi["notifiche"][0]["lavoro_id"] == l["id"]


def test_assegnarsi_da_soli_non_fa_suonare_la_campanella(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()

    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "marco@a.it")}, headers=a)
    assert _avvisi(client, a)["non_lette"] == 0


def test_riassegnare_due_volte_non_raddoppia_l_avviso(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    luca_id = _id_utente(client, a, "luca@a.it")

    for _ in range(3):
        client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": luca_id}, headers=a)
    assert _avvisi(client, luca)["non_lette"] == 1


# ---------- COMMENTI ----------

def test_un_commento_avvisa_gli_assegnatari_ma_non_chi_scrive(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    anna = _crea_utente(client, a, "Anna", "anna@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Quadro", "progetto_id": p["id"]}, headers=a).json()
    for email in ("luca@a.it", "anna@a.it"):
        client.post(f"/lavori/{l['id']}/assegnati",
                    json={"utente_id": _id_utente(client, a, email)}, headers=a)

    # Luca commenta: deve arrivare ad Anna, non a Luca stesso
    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "Manca la guaina"}, headers=luca)

    commenti_anna = [n for n in _avvisi(client, anna)["notifiche"] if n["tipo"] == "commento"]
    assert len(commenti_anna) == 1
    assert "Luca" in commenti_anna[0]["testo"] and "Manca la guaina" in commenti_anna[0]["testo"]
    assert [n for n in _avvisi(client, luca)["notifiche"] if n["tipo"] == "commento"] == []


def test_i_commenti_lunghi_vengono_accorciati(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "luca@a.it")}, headers=a)

    client.post(f"/lavori/{l['id']}/commenti", json={"testo": "x" * 300}, headers=a)
    testo = [n for n in _avvisi(client, luca)["notifiche"] if n["tipo"] == "commento"][0]["testo"]
    assert "..." in testo and len(testo) < 200


# ---------- AGENDA ----------

def test_essere_messo_in_una_riunione_avvisa(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    quando = datetime.combine(date.today() + timedelta(days=1),
                              datetime.min.time()).replace(hour=10).isoformat()
    marco_id = _id_utente(client, a, "marco@a.it")
    luca_id = _id_utente(client, a, "luca@a.it")

    client.post("/agenda", json={"titolo": "Riunione di cantiere", "inizio": quando,
                                 "partecipanti_ids": [marco_id, luca_id]}, headers=a)

    avvisi = [n for n in _avvisi(client, luca)["notifiche"] if n["tipo"] == "impegno"]
    assert len(avvisi) == 1
    assert "Riunione di cantiere" in avvisi[0]["testo"]
    # e l'organizzatore non avvisa se stesso
    assert [n for n in _avvisi(client, a)["notifiche"] if n["tipo"] == "impegno"] == []


def test_aggiungere_qualcuno_dopo_avvisa_solo_lui(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    anna = _crea_utente(client, a, "Anna", "anna@a.it", "operatore")
    quando = datetime.combine(date.today() + timedelta(days=1),
                              datetime.min.time()).replace(hour=10).isoformat()
    ids = {e: _id_utente(client, a, e) for e in ("marco@a.it", "luca@a.it", "anna@a.it")}

    i = client.post("/agenda", json={"titolo": "R", "inizio": quando,
                                     "partecipanti_ids": [ids["marco@a.it"], ids["luca@a.it"]]},
                    headers=a).json()
    assert len([n for n in _avvisi(client, luca)["notifiche"] if n["tipo"] == "impegno"]) == 1

    # aggiungo Anna: Luca non deve ricevere un secondo avviso
    client.patch(f"/agenda/{i['id']}", json={
        "partecipanti_ids": [ids["marco@a.it"], ids["luca@a.it"], ids["anna@a.it"]]}, headers=a)

    assert len([n for n in _avvisi(client, luca)["notifiche"] if n["tipo"] == "impegno"]) == 1
    assert len([n for n in _avvisi(client, anna)["notifiche"] if n["tipo"] == "impegno"]) == 1


# ---------- LETTURA E GESTIONE ----------

def test_segno_letto_e_il_conteggio_cala(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    luca_id = _id_utente(client, a, "luca@a.it")
    for titolo in ("A", "B"):
        l = client.post("/lavori", json={"titolo": titolo, "progetto_id": p["id"]},
                        headers=a).json()
        client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": luca_id}, headers=a)

    assert _avvisi(client, luca)["non_lette"] == 2
    primo = _avvisi(client, luca)["notifiche"][0]["id"]
    assert client.patch(f"/notifiche/{primo}", headers=luca).status_code == 200
    assert _avvisi(client, luca)["non_lette"] == 1

    # e l'azzeramento in blocco
    r = client.post("/notifiche/segna-tutte-lette", headers=luca)
    assert r.status_code == 200 and r.json()["non_lette"] == 0


def test_filtro_solo_non_lette(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    luca_id = _id_utente(client, a, "luca@a.it")
    for titolo in ("A", "B"):
        l = client.post("/lavori", json={"titolo": titolo, "progetto_id": p["id"]},
                        headers=a).json()
        client.post(f"/lavori/{l['id']}/assegnati", json={"utente_id": luca_id}, headers=a)

    primo = _avvisi(client, luca)["notifiche"][0]["id"]
    client.patch(f"/notifiche/{primo}", headers=luca)
    solo = client.get("/notifiche?solo_non_lette=true", headers=luca).json()
    assert len(solo["notifiche"]) == 1


def test_non_leggo_gli_avvisi_di_un_collega(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "luca@a.it")}, headers=a)

    suo = _avvisi(client, luca)["notifiche"][0]["id"]
    # nemmeno l'admin puo' toccarlo: un avviso e' personale
    assert client.patch(f"/notifiche/{suo}", headers=a).status_code == 404
    assert client.delete(f"/notifiche/{suo}", headers=a).status_code == 404
    assert _avvisi(client, a)["notifiche"] == []


def test_posso_cancellare_i_miei(client):
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "L", "progetto_id": p["id"]}, headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "luca@a.it")}, headers=a)

    mio = _avvisi(client, luca)["notifiche"][0]["id"]
    assert client.delete(f"/notifiche/{mio}", headers=luca).status_code == 204
    assert _avvisi(client, luca)["notifiche"] == []


def test_cancellare_il_lavoro_non_cancella_l_avviso(client):
    """L'avviso racconta un fatto avvenuto: resta leggibile anche se il lavoro
    non c'e' piu', semplicemente non porta piu' da nessuna parte."""
    a = registra(client, "Azienda A", "Marco", "marco@a.it")
    luca = _crea_utente(client, a, "Luca", "luca@a.it", "operatore")
    p = client.post("/progetti", json={"nome": "P"}, headers=a).json()
    l = client.post("/lavori", json={"titolo": "Sparira", "progetto_id": p["id"]},
                    headers=a).json()
    client.post(f"/lavori/{l['id']}/assegnati",
                json={"utente_id": _id_utente(client, a, "luca@a.it")}, headers=a)

    client.delete(f"/lavori/{l['id']}", headers=a)

    avvisi = _avvisi(client, luca)["notifiche"]
    assert len(avvisi) == 1
    assert "Sparira" in avvisi[0]["testo"]      # il testo resta
    assert avvisi[0]["lavoro_id"] is None       # ma il collegamento no
