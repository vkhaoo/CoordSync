"""impegni che si ripetono

Una colonna sola: 'serie_id', il numero che lega fra loro le occorrenze di una
ripetizione (ed e' l'id della prima). NULL = impegno singolo, che e' la
stragrande maggioranza — quindi niente travaso: il valore giusto per tutti gli
impegni gia' presi e' proprio NULL.

Non e' una chiave esterna verso 'impegni', ed e' voluto: se si cancella la
prima occorrenza le altre devono restare in piedi come serie, e un vincolo con
CASCADE le porterebbe via tutte mentre uno con SET NULL scioglierebbe il
gruppo. Qui il legame vale fra pari, non dal figlio al padre.

L'indice invece serve: cancellare tutta la serie e' una ricerca per questo
campo.

Revision ID: f9560906898c
Revises: 69533c3919d2
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f9560906898c'
down_revision: Union[str, Sequence[str], None] = '69533c3919d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("impegni", schema=None) as batch_op:
        batch_op.add_column(sa.Column("serie_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_impegni_serie_id"), ["serie_id"], unique=False)


def downgrade() -> None:
    # Gli impegni restano TUTTI, uno per data: si perde solo il fatto che
    # fossero una serie, quindi vanno cancellati uno alla volta. Nessun
    # appuntamento sparisce dall'agenda di nessuno.
    with op.batch_alter_table("impegni", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_impegni_serie_id"))
        batch_op.drop_column("serie_id")
