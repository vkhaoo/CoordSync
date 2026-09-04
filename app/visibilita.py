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
from app.models.utente import Utente, RuoloUtente


def condizione_progetti_visibili(db: Session, current: Utente):
    """La condizione SQL "questo progetto posso vederlo".

    - admin: tutta la sua azienda, senza distinzioni di reparto;
    - tutti gli altri: i progetti dei propri reparti, piu' quelli SENZA reparto
      (i "generali", visibili a tutta l'azienda), piu' quelli dove sono
      assegnato a un lavoro.

    L'ultima clausola e' una rete di sicurezza voluta: se un caposquadra ti da'
    un lavoro su un progetto di un altro reparto, non ha senso nascondertelo.
    """
    if current.ruolo == RuoloUtente.admin:
        return true()

    ids_reparti = [r.id for r in current.reparti]
    progetti_dove_sono_assegnato = (
        db.query(Lavoro.progetto_id)
        .join(assegnazione, assegnazione.c.lavoro_id == Lavoro.id)
        .filter(assegnazione.c.utente_id == current.id)
        .scalar_subquery()
    )
    return or_(
        Progetto.reparto_id.is_(None),
        Progetto.reparto_id.in_(ids_reparti),
        Progetto.id.in_(progetti_dove_sono_assegnato),
    )


def progetti_visibili(db: Session, current: Utente):
    """Query dei progetti che vedo: filtro azienda + filtro reparto."""
    return (
        db.query(Progetto)
        .filter(Progetto.organizzazione_id == current.organizzazione_id,
                condizione_progetti_visibili(db, current))
    )


def progetto_visibile(db: Session, current: Utente, progetto_id: int) -> Progetto | None:
    """Il progetto, ma solo se posso vederlo. Altrimenti None (-> 404)."""
    return progetti_visibili(db, current).filter(Progetto.id == progetto_id).first()


def lavori_visibili(db: Session, current: Utente):
    """Query dei lavori che vedo: un lavoro si vede se si vede il suo progetto."""
    return (
        db.query(Lavoro).join(Progetto)
        .filter(Progetto.organizzazione_id == current.organizzazione_id,
                condizione_progetti_visibili(db, current))
    )


def lavoro_visibile(db: Session, current: Utente, lavoro_id: int) -> Lavoro | None:
    """Il lavoro, ma solo se posso vederlo. Altrimenti None (-> 404)."""
    return lavori_visibili(db, current).filter(Lavoro.id == lavoro_id).first()


def reparto_assegnabile(db: Session, current: Utente, reparto_id: int | None) -> bool:
    """Posso mettere un progetto in questo reparto?

    Solo reparti della mia azienda. L'admin puo' usarli tutti; gli altri solo
    quelli di cui fanno parte, altrimenti un caposquadra potrebbe spostare un
    progetto in un reparto che non e' suo (e magari perderlo di vista).
    None significa "progetto generale": sempre ammesso.
    """
    if reparto_id is None:
        return True

    from app.models.reparto import Reparto
    reparto = (
        db.query(Reparto)
        .filter(Reparto.id == reparto_id,
                Reparto.organizzazione_id == current.organizzazione_id)
        .first()
    )
    if reparto is None:
        return False
    if current.ruolo == RuoloUtente.admin:
        return True
    return any(r.id == reparto_id for r in current.reparti)
