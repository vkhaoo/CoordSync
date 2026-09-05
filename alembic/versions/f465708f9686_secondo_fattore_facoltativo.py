"""secondo fattore facoltativo

Revision ID: f465708f9686
Revises: bed5b1f2f4ae
Create Date: 2026-09-05 21:49:33.229138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f465708f9686'
down_revision: Union[str, Sequence[str], None] = 'bed5b1f2f4ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("utenti", schema=None) as batch_op:
        batch_op.add_column(sa.Column("totp_segreto", sa.String(), nullable=True))
        # server_default: la colonna e' NOT NULL e la tabella e' piena di
        # utenti. Senza un valore di riempimento il database non saprebbe cosa
        # scrivere nelle righe che ci sono, e la migrazione morirebbe. Il
        # valore giusto e' "spento": nessuno ha ancora acceso niente.
        batch_op.add_column(sa.Column("totp_attivo", sa.Boolean(), nullable=False,
                                      server_default=sa.false()))
        batch_op.add_column(sa.Column("totp_recupero", sa.Text(), nullable=True))


def downgrade() -> None:
    # Tornando indietro si perdono le configurazioni del secondo fattore: chi
    # l'aveva acceso torna al solo accesso con password. E' l'unico esito
    # possibile, e non fa perdere dati di lavoro.
    with op.batch_alter_table("utenti", schema=None) as batch_op:
        batch_op.drop_column("totp_recupero")
        batch_op.drop_column("totp_attivo")
        batch_op.drop_column("totp_segreto")
