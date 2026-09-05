"""progetti e macchine su piu reparti

Revision ID: dcbc9794f0d1
Revises: 4b6bb227dddd
Create Date: 2026-09-05 08:15:46.826765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcbc9794f0d1'
down_revision: Union[str, Sequence[str], None] = '4b6bb227dddd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Da un reparto solo a piu' reparti per progetti e macchine."""
    op.create_table('macchine_reparto',
    sa.Column('macchina_id', sa.Integer(), nullable=False),
    sa.Column('reparto_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['macchina_id'], ['macchine.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reparto_id'], ['reparti.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('macchina_id', 'reparto_id')
    )
    op.create_table('progetti_reparto',
    sa.Column('progetto_id', sa.Integer(), nullable=False),
    sa.Column('reparto_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['progetto_id'], ['progetti.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reparto_id'], ['reparti.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('progetto_id', 'reparto_id')
    )

    # PASSO AGGIUNTO A MANO, il piu' importante: prima di buttare la vecchia
    # colonna, porto i dati esistenti nelle tabelle nuove. Senza questo, in
    # produzione si perderebbe a quale reparto appartiene ogni progetto e ogni
    # macchina. L'autogenerate le colonne le elimina e basta.
    op.execute("""
        INSERT INTO progetti_reparto (progetto_id, reparto_id)
        SELECT id, reparto_id FROM progetti WHERE reparto_id IS NOT NULL
    """)
    op.execute("""
        INSERT INTO macchine_reparto (macchina_id, reparto_id)
        SELECT id, reparto_id FROM macchine WHERE reparto_id IS NOT NULL
    """)

    # Ora le colonne si possono togliere. Non elimino i vincoli di chiave
    # esterna a parte: spariscono da soli insieme alla colonna, sia su SQLite
    # (batch mode ricrea la tabella) sia su PostgreSQL.
    with op.batch_alter_table('macchine', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_macchine_reparto_id'))
        batch_op.drop_column('reparto_id')

    with op.batch_alter_table('progetti', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_progetti_reparto_id'))
        batch_op.drop_column('reparto_id')


def downgrade() -> None:
    """Torna al reparto singolo.

    ATTENZIONE: chi stava in piu' reparti ne conserva UNO SOLO. E' inevitabile
    tornando a una colonna che ne regge uno, ma va saputo prima di eseguirlo.
    """
    with op.batch_alter_table('progetti', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reparto_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_progetti_reparto_id', 'reparti',
                                    ['reparto_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index(batch_op.f('ix_progetti_reparto_id'), ['reparto_id'], unique=False)

    with op.batch_alter_table('macchine', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reparto_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_macchine_reparto_id', 'reparti',
                                    ['reparto_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index(batch_op.f('ix_macchine_reparto_id'), ['reparto_id'], unique=False)

    # Anche all'indietro i dati vanno riportati, altrimenti il downgrade
    # svuoterebbe tutto. Tengo il reparto con l'id piu' basso.
    op.execute("""
        UPDATE progetti SET reparto_id =
            (SELECT MIN(reparto_id) FROM progetti_reparto WHERE progetto_id = progetti.id)
    """)
    op.execute("""
        UPDATE macchine SET reparto_id =
            (SELECT MIN(reparto_id) FROM macchine_reparto WHERE macchina_id = macchine.id)
    """)

    op.drop_table('progetti_reparto')
    op.drop_table('macchine_reparto')
