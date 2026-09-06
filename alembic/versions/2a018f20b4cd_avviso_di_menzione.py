"""avviso di menzione

Scritta a mano, come quella dello stato 'annullato': l'autogenerate non vede i
cambiamenti di un enum, e i due database si comportano in modo diverso. Su
PostgreSQL 'tipoavviso' e' un TIPO vero e il valore nuovo vuole ALTER TYPE;
senza, in produzione il salvataggio fallirebbe mentre in locale, su SQLite,
funzionerebbe benissimo.

Tornando indietro il valore resta nel tipo (toglierlo vorrebbe dire ricreare
il tipo e riscrivere la colonna), ma gli avvisi di menzione diventano avvisi
di 'commento': e' il loro parente piu' vicino — parlano davvero di un commento
appena scritto — e il codice vecchio 'menzione' non lo sa leggere, quindi la
campanella andrebbe in errore. Nessun avviso viene cancellato: cambia solo
l'etichetta, e viene detto quanti sono.

Revision ID: 2a018f20b4cd
Revises: 610a925a90e0
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2a018f20b4cd'
down_revision: Union[str, Sequence[str], None] = '610a925a90e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE tipoavviso ADD VALUE IF NOT EXISTS 'menzione'")
    # Su SQLite la colonna e' un VARCHAR senza vincolo: niente da fare.


def downgrade() -> None:
    legame = op.get_bind()
    quanti = legame.execute(
        sa.text("SELECT COUNT(*) FROM notifiche WHERE tipo = 'menzione'")
    ).scalar() or 0

    if quanti:
        legame.execute(
            sa.text("UPDATE notifiche SET tipo = 'commento' WHERE tipo = 'menzione'")
        )
        print(
            f"\nATTENZIONE: {quanti} avvisi di menzione sono diventati avvisi di "
            "commento.\n"
            "Nessuno e' stato cancellato: il testo, la data e il collegamento "
            "restano quelli.\nE' cambiato solo il tipo, perche' il codice a cui "
            "si sta tornando 'menzione' non lo sa leggere.\n"
        )
