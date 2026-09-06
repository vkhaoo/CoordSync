"""un commento si puo' correggere

Una colonna sola, nullable: 'modificato_il' resta vuota finche' il commento
non viene riscritto. Vuota vuol dire "e' ancora come l'ho scritto", ed e'
esattamente cosa devono dire tutti i commenti gia' esistenti — quindi niente
travaso: il valore giusto per loro e' proprio NULL.

Nessun server_default: non serve, perche' la colonna nasce gia' permissiva.
(La regola del server_default vale quando si aggiunge una colonna NOT NULL a
una tabella che ha gia' delle righe.)

Revision ID: 610a925a90e0
Revises: 76fcb48d73ff
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '610a925a90e0'
down_revision: Union[str, Sequence[str], None] = '76fcb48d73ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("commenti", schema=None) as batch_op:
        batch_op.add_column(sa.Column("modificato_il", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Si perde solo l'informazione "questo era stato riscritto": i commenti
    # restano tutti, con il loro testo attuale.
    with op.batch_alter_table("commenti", schema=None) as batch_op:
        batch_op.drop_column("modificato_il")
