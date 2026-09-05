"""impegni con piu partecipanti

Revision ID: 085f69855d88
Revises: dcbc9794f0d1
Create Date: 2026-09-05 08:31:55.799545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '085f69855d88'
down_revision: Union[str, Sequence[str], None] = 'dcbc9794f0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Da un impegno per persona a un impegno con piu' partecipanti."""
    op.create_table('partecipanti_impegno',
    sa.Column('impegno_id', sa.Integer(), nullable=False),
    sa.Column('utente_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['impegno_id'], ['impegni.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['utente_id'], ['utenti.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('impegno_id', 'utente_id')
    )

    # PASSO A MANO: ogni impegno che esiste gia' diventa un impegno con un solo
    # partecipante, la persona di cui era l'agenda. Va fatto PRIMA della
    # rinomina, perche' legge ancora la vecchia colonna.
    op.execute("""
        INSERT INTO partecipanti_impegno (impegno_id, utente_id)
        SELECT id, utente_id FROM impegni
    """)

    # RINOMINO invece di eliminare e ricreare: l'autogenerate proponeva una
    # drop + add, che avrebbe buttato via il proprietario di ogni impegno (e
    # creato una colonna obbligatoria senza valore su righe esistenti).
    with op.batch_alter_table('impegni', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_impegni_utente_id'))
        batch_op.alter_column('utente_id', new_column_name='organizzatore_id',
                              existing_type=sa.Integer(), existing_nullable=False)

    # L'indice si crea FUORI dal blocco: dentro, la rinomina non e' ancora
    # applicata e il nome nuovo non esiste ancora (KeyError).
    op.create_index('ix_impegni_organizzatore_id', 'impegni',
                    ['organizzatore_id'], unique=False)


def downgrade() -> None:
    """Torna a un impegno per persona.

    ATTENZIONE: una riunione con piu' partecipanti resta in agenda al solo
    organizzatore. Inevitabile tornando a una colonna singola, ma va saputo.
    """
    with op.batch_alter_table('impegni', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_impegni_organizzatore_id'))
        batch_op.alter_column('organizzatore_id', new_column_name='utente_id',
                              existing_type=sa.Integer(), existing_nullable=False)

    op.create_index('ix_impegni_utente_id', 'impegni', ['utente_id'], unique=False)

    op.drop_table('partecipanti_impegno')
