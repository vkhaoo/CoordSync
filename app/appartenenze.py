"""
Le tessere di appartenenza, tenute in un posto solo.

Chi crea un utente non deve ricordarsi di creargli anche la tessera: se lo
dimentica una volta sola, quella persona entra e non vede niente. Qui c'e' una
funzione che fa le due cose insieme, e tutti passano da li'.
"""
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.appartenenza import Appartenenza, StatoAppartenenza
from app.models.utente import RuoloUtente, Utente


def iscrivi(db: Session, utente: Utente, organizzazione_id: int,
            ruolo: RuoloUtente,
            stato: StatoAppartenenza = StatoAppartenenza.attiva) -> Appartenenza:
    """Rende un utente membro di un'azienda con un certo ruolo.

    Se la tessera c'e' gia' aggiorna ruolo e stato, invece di lasciar
    esplodere la chiave primaria: chiamarla due volte non deve essere un
    errore, e sia il cambio ruolo sia l'accettazione di un invito passano
    da qui.
    """
    esistente = (
        db.query(Appartenenza)
        .filter(Appartenenza.utente_id == utente.id,
                Appartenenza.organizzazione_id == organizzazione_id)
        .first()
    )
    if esistente is not None:
        esistente.ruolo = ruolo
        esistente.stato = stato
        return esistente

    tessera = Appartenenza(utente_id=utente.id,
                           organizzazione_id=organizzazione_id,
                           ruolo=ruolo, stato=stato)
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
    return Utente.appartenenze.any(sa.and_(
        Appartenenza.organizzazione_id == organizzazione_id,
        Appartenenza.stato == StatoAppartenenza.attiva))


def ruolo_in(db: Session, utente: Utente, organizzazione_id: int) -> RuoloUtente | None:
    """Che ruolo ha questa persona in quest'azienda, o None se non ci lavora.

    E' il controllo su cui poggia tutto l'isolamento quando si cambia azienda:
    None qui vuol dire "non deve vedere niente di questo posto".
    """
    tessera = (
        db.query(Appartenenza)
        .filter(Appartenenza.utente_id == utente.id,
                Appartenenza.organizzazione_id == organizzazione_id,
                # SOLO le tessere attive. Un invito in attesa compare
                # nell'elenco delle proprie aziende ma non apre niente:
                # togliere questa riga vorrebbe dire far entrare chiunque
                # sia stato invitato, anche senza aver mai risposto.
                Appartenenza.stato == StatoAppartenenza.attiva)
        .first()
    )
    return tessera.ruolo if tessera is not None else None


def aziende_di(db: Session, utente: Utente,
               solo_attive: bool = True) -> list[Appartenenza]:
    """Le aziende di cui fa parte.

    Di default solo quelle vere. Con solo_attive=False tornano anche gli
    inviti in attesa, che servono alla schermata di scelta: li' vanno
    mostrati, ma come qualcosa a cui rispondere, non come un posto dove si
    e' gia' dentro.
    """
    query = db.query(Appartenenza).filter(Appartenenza.utente_id == utente.id)
    if solo_attive:
        query = query.filter(Appartenenza.stato == StatoAppartenenza.attiva)
    return query.all()
