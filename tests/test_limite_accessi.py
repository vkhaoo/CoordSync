"""
Limite ai tentativi di accesso (contro chi prova le password a raffica).

Il conteggio sta in memoria e viene azzerato fra un test e l'altro dalla
fixture in conftest, altrimenti i test si farebbero inciampare a vicenda.
"""
from app import limiti
from tests.conftest import registra


def _accedi(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_dopo_troppi_errori_arriva_il_blocco(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")

    # I primi tentativi sbagliati rispondono col solito 401.
    for _ in range(limiti.MAX_TENTATIVI):
        assert _accedi(client, "marco@a.it", "sbagliata9").status_code == 401

    # Superata la soglia si viene fermati, con l'indicazione di quanto aspettare.
    r = _accedi(client, "marco@a.it", "sbagliata9")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) > 0


def test_il_blocco_vale_anche_con_la_password_giusta(client):
    """Chi e' stato bloccato non passa nemmeno indovinando: e' proprio il
    punto, altrimenti il limite non servirebbe a niente."""
    registra(client, "Azienda A", "Marco", "marco@a.it")
    for _ in range(limiti.MAX_TENTATIVI):
        _accedi(client, "marco@a.it", "sbagliata9")

    assert _accedi(client, "marco@a.it", "password1").status_code == 429


def test_un_accesso_riuscito_azzera_il_conto(client):
    registra(client, "Azienda A", "Marco", "marco@a.it")

    # qualche errore, ma sotto la soglia
    for _ in range(limiti.MAX_TENTATIVI - 1):
        _accedi(client, "marco@a.it", "sbagliata9")

    assert _accedi(client, "marco@a.it", "password1").status_code == 200
    # ricomincia da capo: posso di nuovo sbagliare fino alla soglia
    for _ in range(limiti.MAX_TENTATIVI - 1):
        assert _accedi(client, "marco@a.it", "sbagliata9").status_code == 401


def test_email_inesistente_conta_comunque(client):
    """Anche provare email a caso deve costare: e' il modo in cui si cercano
    gli account esistenti."""
    for _ in range(limiti.MAX_TENTATIVI):
        assert _accedi(client, "nessuno@x.it", "qualcosa1").status_code == 401
    assert _accedi(client, "nessuno@x.it", "qualcosa1").status_code == 429


def test_il_blocco_di_un_email_non_ferma_le_altre(client):
    """Il contatore per indirizzo di rete e' piu' largo di quello per email:
    con la soglia a 10, bloccare un'email sola non deve bloccare un collega
    che accede correttamente."""
    registra(client, "Azienda A", "Marco", "marco@a.it")

    for _ in range(limiti.MAX_TENTATIVI - 1):
        _accedi(client, "vittima@a.it", "sbagliata9")

    # Marco, che non ha sbagliato niente, entra senza problemi.
    assert _accedi(client, "marco@a.it", "password1").status_code == 200


def test_i_tentativi_vecchi_non_contano_piu(client):
    """La finestra e' scorrevole: quello che e' successo mezz'ora fa non pesa."""
    from datetime import datetime, timedelta, timezone
    registra(client, "Azienda A", "Marco", "marco@a.it")

    for _ in range(limiti.MAX_TENTATIVI):
        _accedi(client, "marco@a.it", "sbagliata9")
    assert _accedi(client, "marco@a.it", "password1").status_code == 429

    # Sposto indietro i fallimenti oltre la finestra, come se fosse passato il tempo.
    vecchio = datetime.now(timezone.utc) - limiti.FINESTRA - timedelta(minutes=1)
    for chiave in list(limiti._fallimenti):
        limiti._fallimenti[chiave] = [vecchio] * limiti.MAX_TENTATIVI

    assert _accedi(client, "marco@a.it", "password1").status_code == 200
