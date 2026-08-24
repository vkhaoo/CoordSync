"""aggiunge completamento a lavoro

Revision ID: c06e2e6511ac
Revises: f4b05eb6d462
Create Date: 2026-08-23 07:29:14.519811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c06e2e6511ac'
down_revision: Union[str, Sequence[str], None] = 'f4b05eb6d462'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('lavori', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completato_il', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('completato_da_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_lavori_completato_da', 'utenti',
                                    ['completato_da_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('lavori', schema=None) as batch_op:
        batch_op.drop_constraint('fk_lavori_completato_da', type_='foreignkey')
        batch_op.drop_column('completato_da_id')
        batch_op.drop_column('completato_il')
