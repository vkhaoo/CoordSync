"""versione delle sessioni per revocarle

Revision ID: a542713155ab
Revises: 03c36aca2c83
Create Date: 2026-09-06 12:13:09.525517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a542713155ab'
down_revision: Union[str, Sequence[str], None] = '03c36aca2c83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default='1': la colonna e' NOT NULL e la tabella e' piena di
    # utenti, quindi serve un valore per le righe che ci sono. Uno va bene
    # per tutti: sono tutte sessioni della "prima generazione", e i token
    # gia' in giro (che questo numero dentro non ce l'hanno) valgono uno per
    # convenzione — cosi' nessuno viene buttato fuori dalla pubblicazione.
    with op.batch_alter_table("utenti", schema=None) as batch_op:
        batch_op.add_column(sa.Column('token_versione', sa.Integer(), server_default='1', nullable=False))



def downgrade() -> None:
    # Si perde solo la possibilita' di revocare: le sessioni tornano a valere
    # fino a scadenza. Nessun dato di lavoro e' coinvolto.
    with op.batch_alter_table('utenti', schema=None) as batch_op:
        batch_op.drop_column('token_versione')

    # ### end Alembic commands ###
