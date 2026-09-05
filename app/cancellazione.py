"""
Cancellazione di un account, con anonimizzazione.

Decisione presa: **il lavoro resta, la persona sparisce**. Un commento scritto
due anni fa spiega ancora perche' quel quadro e' cablato cosi'; cancellarlo
insieme alla persona farebbe perdere alla squadra una memoria che le serve.
Quello che sparisce e' l'identita': nome, email, e la possibilita' di entrare.

Perche' NON si cancella davvero la riga dell'utente: mezzo database punta a
quella riga (commenti, voci di storico, allegati, chi ha completato un lavoro,
chi organizza una riunione). Cancellarla per davvero significherebbe o perdere
quei dati, o riempire tutto di riferimenti vuoti da gestire in venti punti
diversi. Svuotare la riga ottiene lo stesso risultato per chi guarda, senza
rompere niente.

Cosa sparisce comunque, perche' e' roba personale e non serve a nessun altro:
gli avvisi ricevuti, gli impegni che riguardavano solo lui, l'appartenenza ai
reparti e le assegnazioni ai lavori.
"""
from sqlalchemy.orm import Session

from app.models.appartenenza import Appartenenza  # noqa: F401  (serve la relazione)
from app.models.impegno import Impegno
from app.models.notifica import Notifica
from app.models.utente import Utente

NOME_ANONIMO = "Utente eliminato"


def anonimizza(db: Session, utente: Utente) -> None:
    """Svuota l'identita' di un utente lasciando in piedi il suo lavoro.

    NON fa commit: lo fa chi chiama, insieme al resto.
    """
    # 1) Gli avvisi ricevuti: personali, non servono a nessun altro.
    db.query(Notifica).filter(Notifica.utente_id == utente.id).delete(
        synchronize_session=False)

    # 2) L'agenda. Gli impegni dove era l'unico partecipante erano roba sua e
    #    spariscono; dalle riunioni con altri esce soltanto, cosi' la riunione
    #    resta in piedi per chi c'era.
    for impegno in list(db.query(Impegno).filter(
            Impegno.partecipanti.any(Utente.id == utente.id)).all()):
        altri = [p for p in impegno.partecipanti if p.id != utente.id]
        if altri:
            impegno.partecipanti = altri
        else:
            db.delete(impegno)

    # 3) Non e' piu' responsabile di niente, non fa piu' parte di nessun
    #    reparto e non e' piu' membro di nessuna azienda. Le tessere vanno
    #    tolte a mano: la riga dell'utente non viene cancellata (si svuota
    #    soltanto), quindi il CASCADE del database non scatta.
    utente.lavori = []
    utente.reparti = []
    utente.appartenenze = []

    # 4) L'identita' se ne va. L'email deve restare unica (c'e' un vincolo), ma
    #    non deve piu' dire chi era: ci metto l'id, che non e' un dato personale.
    #
    #    Il dominio non e' uno di quelli riservati (.local, .invalid): il
    #    validatore delle email li rifiuta, e siccome l'email esce anche in
    #    lettura, l'elenco utenti sarebbe andato in errore. Questo e' un
    #    sottodominio che non esiste e non ricevera' mai niente.
    utente.nome = NOME_ANONIMO
    utente.email = f"eliminato-{utente.id}@utenti-eliminati.coordsync"
    utente.password_hash = None      # senza password non si entra piu'
    utente.email_verificata = False
    utente.deve_cambiare_password = False


def e_ultimo_admin(db: Session, utente: Utente) -> bool:
    """True se e' l'ultimo admin rimasto della sua azienda.

    Serve a non lasciare un'azienda senza timone: senza admin nessuno potrebbe
    piu' gestire utenti, reparti e permessi, e non ci sarebbe modo di rimediare
    dall'interno dell'app.
    """
    from app.models.utente import RuoloUtente

    if utente.ruolo != RuoloUtente.admin:
        return False
    quanti = (
        db.query(Utente)
        .filter(Utente.organizzazione_id == utente.organizzazione_id,
                Utente.ruolo == RuoloUtente.admin,
                Utente.id != utente.id,
                Utente.password_hash.isnot(None))   # gli anonimizzati non contano
        .count()
    )
    return quanti == 0
