"""
Creazione degli avvisi in-app (la campanella).

Tenuta qui e non sparsa nei router, per due motivi: la regola "non avvisare
mai se stesso" vale sempre e va scritta una volta sola, e cosi' i router
restano leggibili (una riga: "avvisa queste persone di questo fatto").

NB: app/notifiche.py manda le EMAIL, questo file crea gli avvisi DENTRO l'app.

Gli avvisi NON aggiungono visibilita': si mandano solo a chi quella cosa la
puo' gia' vedere (gli assegnatari di un lavoro, i partecipanti a un impegno),
quindi non diventano una scorciatoia per sbirciare oltre il proprio reparto.
"""
from sqlalchemy.orm import Session

from app.models.notifica import Notifica, TipoAvviso
from app.models.utente import Utente


def avvisa(db: Session, destinatari, tipo: TipoAvviso, testo: str,
           mittente: Utente | None = None, lavoro_id: int | None = None,
           impegno_id: int | None = None) -> list[Notifica]:
    """Crea un avviso per ogni destinatario.

    Chi provoca il fatto non riceve l'avviso del proprio gesto: assegnarsi un
    lavoro da soli o commentare non deve far suonare la propria campanella.

    NON fa commit: lo fa il router insieme al resto, cosi' se l'operazione
    fallisce non restano in giro avvisi di cose mai avvenute.
    """
    creati = []
    gia_visti = set()

    for persona in destinatari:
        if persona is None:
            continue
        if mittente is not None and persona.id == mittente.id:
            continue
        if persona.id in gia_visti:      # niente doppioni se una persona compare due volte
            continue
        gia_visti.add(persona.id)

        avviso = Notifica(tipo=tipo, testo=testo, utente_id=persona.id,
                          lavoro_id=lavoro_id, impegno_id=impegno_id)
        db.add(avviso)
        creati.append(avviso)

    return creati
