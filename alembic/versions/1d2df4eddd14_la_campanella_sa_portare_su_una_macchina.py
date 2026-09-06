"""la campanella sa portare su una macchina

Da quando si commenta sotto le voci del taccuino, l'autore di una voce va
avvisato quando qualcuno gli risponde. Ma la tabella degli avvisi sapeva
portare solo su un lavoro o su un impegno: un avviso che non porta da nessuna
parte e' peggio di nessun avviso.

Rivista a mano: il vincolo di chiave esterna e' NOMINATO, se no il downgrade
non sa cosa togliere.

SET NULL e non CASCADE, come per lavoro_id e impegno_id: cancellata la voce,
l'avviso resta leggibile — racconta ancora cosa e' successo quel giorno —
semplicemente non porta piu' da nessuna parte.

Niente travaso: gli avvisi vecchi sono tutti di lavori e impegni, e per loro
la colonna nuova resta giustamente vuota.

Revision ID: 1d2df4eddd14
Revises: 1e89256dde1b
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1d2df4eddd14'
down_revision: Union[str, Sequence[str], None] = '1e89256dde1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOME_VINCOLO = "fk_notifiche_voce_id"


def upgrade() -> None:
    with op.batch_alter_table("notifiche", schema=None) as batch_op:
        batch_op.add_column(sa.Column("voce_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(NOME_VINCOLO, "voci_macchina",
                                    ["voce_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    # Si perde solo il collegamento: gli avvisi restano tutti, con il loro
    # testo e la loro data.
    with op.batch_alter_table("notifiche", schema=None) as batch_op:
        batch_op.drop_constraint(NOME_VINCOLO, type_="foreignkey")
        batch_op.drop_column("voce_id")
