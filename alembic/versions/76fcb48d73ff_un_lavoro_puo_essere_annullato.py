"""un lavoro puo' essere annullato

Scritta a mano: l'autogenerate NON vede i cambiamenti di un enum, quindi
questa migrazione non sarebbe mai comparsa da sola.

I DUE DATABASE SI COMPORTANO IN MODO DIVERSO, ed e' tutto il punto:

- su PostgreSQL (produzione) 'statolavoro' e' un TIPO vero, e un valore nuovo
  si aggiunge con ALTER TYPE. Senza questa riga, in produzione il salvataggio
  fallirebbe — mentre in locale, su SQLite, funzionerebbe benissimo: il caso
  peggiore, un errore che i test non possono vedere;
- su SQLite la colonna e' un semplice VARCHAR senza vincolo, quindi non c'e'
  niente da fare e la migrazione passa senza toccare nulla.

IL RITORNO INDIETRO. Su PostgreSQL un valore da un tipo enum non si toglie
(servirebbe ricreare il tipo e riscrivere la colonna: molto piu' pericoloso
del problema che risolve). Quindi il downgrade lascia il valore nel tipo — e'
inerte, nessuno lo scrive piu' — ma prima rimette i lavori annullati "in
attesa", perche' il codice vecchio quel valore non sa leggerlo e andrebbe in
errore aprendo il progetto. Nessun lavoro viene cancellato: cambia solo la sua
etichetta, e viene detto a voce alta quanti sono.

Revision ID: 76fcb48d73ff
Revises: 1d2df4eddd14
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '76fcb48d73ff'
down_revision: Union[str, Sequence[str], None] = '1d2df4eddd14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    legame = op.get_bind()
    if legame.dialect.name == "postgresql":
        # IF NOT EXISTS: cosi' rilanciarla non fa danni.
        op.execute("ALTER TYPE statolavoro ADD VALUE IF NOT EXISTS 'annullato'")
    # Su SQLite non c'e' niente da fare: la colonna e' VARCHAR senza vincolo.


def downgrade() -> None:
    legame = op.get_bind()

    quanti = legame.execute(
        sa.text("SELECT COUNT(*) FROM lavori WHERE stato = 'annullato'")
    ).scalar() or 0

    if quanti:
        legame.execute(
            sa.text("UPDATE lavori SET stato = 'in_attesa' WHERE stato = 'annullato'")
        )
        print(
            f"\nATTENZIONE: {quanti} lavori erano annullati e sono tornati "
            "\"in attesa\".\n"
            "Nessuno e' stato cancellato: e' cambiata solo l'etichetta, perche' "
            "il codice a cui si sta\ntornando il valore 'annullato' non lo sa "
            "leggere e andrebbe in errore aprendo il progetto.\n"
        )

    # Il valore resta dentro il tipo di PostgreSQL: toglierlo vorrebbe dire
    # ricreare il tipo e riscrivere la colonna, molto piu' rischioso del
    # problema che risolve. Resta li' inerte, e nessuno lo scrive piu'.
