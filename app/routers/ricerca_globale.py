"""
Ricerca unica: una domanda sola, risposte da tutta l'app.

Le ricerche che esistevano erano legate a un posto: dentro i lavori di UN
progetto, dentro lo storico di UNA macchina. Vanno benissimo quando si sa gia'
dove guardare — ma spesso non si sa. Ci si ricorda "la valvola V7" e non in
quale progetto, in quale macchina o in che riunione se ne era parlato.

Qui si cerca dappertutto in un colpo. Due punti fermi:

- **la ricerca non aggiunge visibilita'.** Ogni pezzo passa dai soliti filtri
  di visibilita.py: chi non vede un progetto non lo trova cercando, e un
  risultato non deve nemmeno rivelare che quella cosa esiste. C'e' un test
  apposta;
- **si cerca nel database e si riportano poche righe per tipo.** Chi cerca
  vuole arrivare a una cosa, non leggere trecento risultati: se quello che
  cerca non c'e' nei primi, conviene che scriva qualcosa di piu' preciso.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.impegno import Impegno
from app.models.lavoro import Lavoro
from app.models.macchina import Macchina
from app.models.progetto import Progetto
from app.models.utente import Utente
from app.models.voce_macchina import VoceMacchina
from app.ricerca import condizione_testo
from app.visibilita import lavori_visibili, macchine_visibili, progetti_visibili

router = APIRouter(prefix="/ricerca", tags=["ricerca"])

# Quanti risultati per tipo. Cinque bastano a capire se si e' sulla strada
# giusta senza trasformare la tendina in una seconda pagina da leggere.
QUANTI = 5


class RisultatoProgetto(BaseModel):
    id: int
    nome: str


class RisultatoLavoro(BaseModel):
    id: int
    titolo: str
    progetto_id: int
    progetto: str        # il nome del progetto: da solo un titolo non basta a orientarsi


class RisultatoMacchina(BaseModel):
    id: int
    nome: str


class RisultatoVoce(BaseModel):
    id: int
    titolo: str
    macchina_id: int
    macchina: str


class RisultatoImpegno(BaseModel):
    id: int
    titolo: str
    inizio: str


class Risultati(BaseModel):
    progetti: list[RisultatoProgetto] = []
    lavori: list[RisultatoLavoro] = []
    macchine: list[RisultatoMacchina] = []
    voci: list[RisultatoVoce] = []
    impegni: list[RisultatoImpegno] = []


@router.get("", response_model=Risultati)
def cerca_dappertutto(q: str = Query(..., min_length=2),
                      db: Session = Depends(get_db),
                      current: Utente = Depends(get_current_user)):
    """Cerca la stessa parola in progetti, lavori, macchine, storico e agenda.

    Il minimo di due caratteri non e' un capriccio: con una lettera sola
    tornerebbe mezzo database, che non aiuta nessuno e costa a tutti.
    """
    vuoto = Risultati()
    if not q.strip():
        return vuoto

    # --- progetti ---
    # progetti_visibili() e non la sola condizione sui reparti: dentro c'e'
    # anche il filtro sull'azienda, e senza quello si cercherebbe pure in
    # casa d'altri.
    progetti = (
        progetti_visibili(db, current)
        .filter(condizione_testo([Progetto.nome, Progetto.descrizione], q))
        .order_by(Progetto.nome)
        .limit(QUANTI)
        .all()
    )

    # --- lavori (titolo e descrizione) ---
    lavori = (
        lavori_visibili(db, current)
        .filter(condizione_testo([Lavoro.titolo, Lavoro.descrizione], q))
        .order_by(Lavoro.id.desc())
        .limit(QUANTI)
        .all()
    )

    # --- macchine ---
    macchine = (
        macchine_visibili(db, current)
        .filter(condizione_testo([Macchina.nome, Macchina.descrizione], q))
        .order_by(Macchina.nome)
        .limit(QUANTI)
        .all()
    )

    # --- voci di storico: visibili se lo e' la loro macchina ---
    ids_macchine_visibili = [m.id for m in macchine_visibili(db, current).all()]
    voci = (
        db.query(VoceMacchina)
        .filter(VoceMacchina.macchina_id.in_(ids_macchine_visibili),
                condizione_testo([VoceMacchina.titolo, VoceMacchina.testo], q))
        .order_by(VoceMacchina.creato_il.desc())
        .limit(QUANTI)
        .all()
    )

    # --- agenda: solo i MIEI impegni ---
    # L'agenda degli altri non si cerca: chi partecipa a una riunione la trova,
    # gli altri non devono sapere che esiste.
    impegni = (
        db.query(Impegno)
        .filter(Impegno.partecipanti.any(Utente.id == current.id),
                condizione_testo([Impegno.titolo, Impegno.note, Impegno.luogo], q))
        .order_by(Impegno.inizio.desc())
        .limit(QUANTI)
        .all()
    )

    return Risultati(
        progetti=[RisultatoProgetto(id=p.id, nome=p.nome) for p in progetti],
        lavori=[RisultatoLavoro(id=l.id, titolo=l.titolo, progetto_id=l.progetto_id,
                                progetto=l.progetto.nome if l.progetto else "")
                for l in lavori],
        macchine=[RisultatoMacchina(id=m.id, nome=m.nome) for m in macchine],
        voci=[RisultatoVoce(id=v.id, titolo=v.titolo, macchina_id=v.macchina_id,
                            macchina=v.macchina.nome if v.macchina else "")
              for v in voci],
        impegni=[RisultatoImpegno(id=i.id, titolo=i.titolo, inizio=i.inizio.isoformat())
                 for i in impegni],
    )
