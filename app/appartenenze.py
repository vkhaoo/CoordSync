"""
Le tessere di appartenenza, tenute in un posto solo.

Chi crea un utente non deve ricordarsi di creargli anche la tessera: se lo
dimentica una volta sola, quella persona entra e non vede niente. Qui c'e' una
funzione che fa le due cose insieme, e tutti passano da li'.
"""
from sqlalchemy.orm import Session

from app.models.appartenenza import Appartenenza
from app.models.utente import RuoloUtente, Utente


def iscrivi(db: Session, utente: Utente, organizzazione_id: int,
            ruolo: RuoloUtente) -> Appartenenza:
    """Rende un utente membro di un'azienda con un certo ruolo.

    Se la tessera c'e' gia' aggiorna solo il ruolo, invece di lasciar
    esplodere la chiave primaria: chiamarla due volte non deve essere un
    errore, e cambiare ruolo a qualcuno passa da qui.
    """
    esistente = (
        db.query(Appartenenza)
        .filter(Appartenenza.utente_id == utente.id,
                Appartenenza.organizzazione_id == organizzazione_id)
        .first()
    )
    if esistente is not None:
        esistente.ruolo = ruolo
        return esistente

    tessera = Appartenenza(utente_id=utente.id,
                           organizzazione_id=organizzazione_id,
                           ruolo=ruolo)
    db.add(tessera)
    return tessera


def condizione_membro(organizzazione_id: int):
    """Condizione "questo utente lavora in quest'azienda", da usare nelle query.

    Prima bastava guardare `utenti.organizzazione_id`: adesso non basta piu',
    perche' una persona puo' lavorare qui pur essendo nata altrove. Si guarda
    la tessera.

    Si usa `.any()` (un EXISTS) e non una join: con la join, chi ha piu'
    tessere tornerebbe una volta per ognuna.
    """
    return Utente.appartenenze.any(
        Appartenenza.organizzazione_id == organizzazione_id)


def ruolo_in(db: Session, utente: Utente, organizzazione_id: int) -> RuoloUtente | None:
    """Che ruolo ha questa persona in quest'azienda, o None se non ci lavora.

    E' il controllo su cui poggia tutto l'isolamento quando si cambia azienda:
    None qui vuol dire "non deve vedere niente di questo posto".
    """
    tessera = (
        db.query(Appartenenza)
        .filter(Appartenenza.utente_id == utente.id,
                Appartenenza.organizzazione_id == organizzazione_id)
        .first()
    )
    return tessera.ruolo if tessera is not None else None


def aziende_di(db: Session, utente: Utente) -> list[Appartenenza]:
    """Tutte le aziende di cui fa parte, per la schermata di scelta."""
    return (
        db.query(Appartenenza)
        .filter(Appartenenza.utente_id == utente.id)
        .all()
    )
