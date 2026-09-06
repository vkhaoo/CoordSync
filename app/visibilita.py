"""
Regole di visibilita': CHI puo' vedere COSA.

Tenute tutte qui, in un posto solo. E' il punto piu' delicato dell'app per la
sicurezza, perche' ci sono DUE livelli di isolamento annidati: prima l'azienda
(nessuno vede i dati di un'altra organizzazione), poi il reparto (dentro
l'azienda, non tutti vedono tutto).

Prima questa logica era copiata in quattro router: una copia sarebbe rimasta
indietro prima o poi, aprendo un buco. Ogni router deve passare da qui.
"""
from sqlalchemy import or_, true
from sqlalchemy.orm import Session

from app.models.assegnazione import assegnazione
from app.models.lavoro import Lavoro
from app.models.progetto import Progetto
from app.models.reparto import Reparto
from app.models.utente import Utente, RuoloUtente


def _guardando_con_gli_occhi_di(db: Session, utente: Utente, organizzazione_id: int):
    """Prepara un utente perche' le regole qui sotto valgano PER LUI.

    Serve a una domanda sola: "questa cosa, il collega che ho appena nominato,
    la vedeva gia'?". Le funzioni di questo file leggono org_attiva_id,
    ruolo_attivo, reparti e id di chi chiede: normalmente le riempie
    get_current_user su chi e' collegato, qui vanno riempite a mano su un
    altro.

    Restituisce None se quella persona in quest'azienda non ci lavora — ed e'
    la risposta piu' importante: vuol dire che non deve vedere niente.

    I due valori vengono RIMESSI com'erano (vedi chi chiama): sono proprieta'
    non mappate appoggiate all'oggetto, e lasciarle sporche vorrebbe dire che
    un controllo successivo, nella stessa richiesta, guarderebbe l'azienda
    sbagliata.
    """
    from app.appartenenze import ruolo_in
    ruolo = ruolo_in(db, utente, organizzazione_id)
    if ruolo is None:
        return None
    return ruolo


def vede_lavoro(db: Session, utente: Utente, organizzazione_id: int,
                lavoro_id: int) -> bool:
    """Quel lavoro, quella persona, lo vede gia'? (senza cambiarle niente)"""
    return _vede(db, utente, organizzazione_id,
                 lambda: lavoro_visibile(db, utente, lavoro_id) is not None)


def vede_macchina(db: Session, utente: Utente, organizzazione_id: int,
                  macchina_id: int) -> bool:
    """Quella macchina, quella persona, la vede gia'?"""
    return _vede(db, utente, organizzazione_id,
                 lambda: macchina_visibile(db, utente, macchina_id) is not None)


def _vede(db: Session, utente: Utente, organizzazione_id: int, domanda) -> bool:
    ruolo = _guardando_con_gli_occhi_di(db, utente, organizzazione_id)
    if ruolo is None:
        return False

    prima_org, prima_ruolo = utente._org_attiva_id, utente._ruolo_attivo
    try:
        utente._org_attiva_id = organizzazione_id
        utente._ruolo_attivo = ruolo
        return domanda()
    finally:
        utente._org_attiva_id, utente._ruolo_attivo = prima_org, prima_ruolo


def condizione_progetti_visibili(db: Session, current: Utente):
    """La condizione SQL "questo progetto posso vederlo".

    - admin: tutta la sua azienda, senza distinzioni di reparto;
    - tutti gli altri: i progetti che condividono almeno un reparto con me,
      piu' quelli SENZA alcun reparto (i "generali", visibili a tutta
      l'azienda), piu' quelli dove sono assegnato a un lavoro.

    L'ultima clausola e' una rete di sicurezza voluta: se un caposquadra ti da'
    un lavoro su un progetto di un altro reparto, non ha senso nascondertelo.

    Uso .any() (che diventa un EXISTS) e non una join: con i reparti multipli
    una join restituirebbe lo stesso progetto una volta per reparto in comune.
    """
    if current.ruolo_attivo == RuoloUtente.admin:
        return true()

    ids_reparti = [r.id for r in current.reparti]
    progetti_dove_sono_assegnato = (
        db.query(Lavoro.progetto_id)
        .join(assegnazione, assegnazione.c.lavoro_id == Lavoro.id)
        .filter(assegnazione.c.utente_id == current.id)
        .scalar_subquery()
    )
    return or_(
        ~Progetto.reparti.any(),                              # nessun reparto = generale
        Progetto.reparti.any(Reparto.id.in_(ids_reparti)),    # almeno uno in comune
        Progetto.id.in_(progetti_dove_sono_assegnato),
    )


def progetti_visibili(db: Session, current: Utente):
    """Query dei progetti che vedo: filtro azienda + filtro reparto."""
    return (
        db.query(Progetto)
        .filter(Progetto.organizzazione_id == current.org_attiva_id,
                condizione_progetti_visibili(db, current))
    )


def progetto_visibile(db: Session, current: Utente, progetto_id: int) -> Progetto | None:
    """Il progetto, ma solo se posso vederlo. Altrimenti None (-> 404)."""
    return progetti_visibili(db, current).filter(Progetto.id == progetto_id).first()


def lavori_visibili(db: Session, current: Utente):
    """Query dei lavori che vedo: un lavoro si vede se si vede il suo progetto."""
    return (
        db.query(Lavoro).join(Progetto)
        .filter(Progetto.organizzazione_id == current.org_attiva_id,
                condizione_progetti_visibili(db, current))
    )


def lavoro_visibile(db: Session, current: Utente, lavoro_id: int) -> Lavoro | None:
    """Il lavoro, ma solo se posso vederlo. Altrimenti None (-> 404)."""
    return lavori_visibili(db, current).filter(Lavoro.id == lavoro_id).first()


def macchine_visibili(db: Session, current: Utente):
    """Query delle macchine che vedo.

    Stessa idea dei progetti, ma piu' semplice: sulle macchine non esistono
    assegnatari, quindi non c'e' la rete di sicurezza. L'admin vede tutto;
    gli altri vedono le macchine dei propri reparti piu' quelle senza reparto.
    """
    from app.models.macchina import Macchina

    query = db.query(Macchina).filter(
        Macchina.organizzazione_id == current.org_attiva_id)
    if current.ruolo_attivo == RuoloUtente.admin:
        return query

    ids_reparti = [r.id for r in current.reparti]
    return query.filter(or_(
        ~Macchina.reparti.any(),
        Macchina.reparti.any(Reparto.id.in_(ids_reparti)),
    ))


def macchina_visibile(db: Session, current: Utente, macchina_id: int):
    """La macchina, ma solo se posso vederla. Altrimenti None (-> 404)."""
    from app.models.macchina import Macchina
    return macchine_visibili(db, current).filter(Macchina.id == macchina_id).first()


def reparti_assegnabili(db: Session, current: Utente, reparti_ids: list[int] | None) -> bool:
    """Posso mettere un progetto o una macchina in QUESTI reparti?

    Devono essere tutti della mia azienda. L'admin puo' usarli tutti; gli altri
    solo quelli di cui fanno parte, altrimenti un caposquadra potrebbe spostare
    un progetto in un reparto che non e' suo (e magari perderlo di vista).
    Lista vuota o None significa "generale": sempre ammesso.
    """
    if not reparti_ids:
        return True

    from app.models.reparto import Reparto as R
    trovati = (
        db.query(R)
        .filter(R.id.in_(set(reparti_ids)),
                R.organizzazione_id == current.org_attiva_id)
        .all()
    )
    # Se anche uno solo non e' della mia azienda, rifiuto tutto.
    if len(trovati) != len(set(reparti_ids)):
        return False
    if current.ruolo_attivo == RuoloUtente.admin:
        return True

    miei = {r.id for r in current.reparti}
    return all(r.id in miei for r in trovati)


def carica_reparti(db: Session, current: Utente, reparti_ids: list[int]):
    """Gli oggetti Reparto da collegare, gia' verificati come assegnabili.
    Da usare SEMPRE dopo reparti_assegnabili()."""
    if not reparti_ids:
        return []
    return (
        db.query(Reparto)
        .filter(Reparto.id.in_(set(reparti_ids)),
                Reparto.organizzazione_id == current.org_attiva_id)
        .all()
    )
