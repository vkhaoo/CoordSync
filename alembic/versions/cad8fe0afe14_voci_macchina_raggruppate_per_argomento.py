"""voci macchina raggruppate per argomento

Aggiunge alle voci del taccuino un "genitore" facoltativo: una voce puo' stare
sotto un'altra, come i lavori stanno sotto un progetto.

Rivista a mano dopo l'autogenerate, come sempre. Due cose cambiate:

- il vincolo di chiave esterna e' NOMINATO ('fk_voci_macchina_genitore_id').
  Alembic lo genera anonimo, e poi il downgrade fallisce perche' non sa cosa
  togliere;
- ondelete='SET NULL' confermato a mano: cancellando l'argomento le voci che
  stavano sotto NON devono sparire, tornano sciolte.

Nessun dato da spostare: la colonna nasce vuota e tutte le voci che esistono
restano esattamente dove sono, come argomenti a se' stanti.

Revision ID: cad8fe0afe14
Revises: c9dcce1d867a
Create Date: 2026-09-05 18:21:56.490172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cad8fe0afe14'
down_revision: Union[str, Sequence[str], None] = 'c9dcce1d867a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOME_VINCOLO = "fk_voci_macchina_genitore_id"


def upgrade() -> None:
    with op.batch_alter_table("voci_macchina", schema=None) as batch_op:
        batch_op.add_column(sa.Column("genitore_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_voci_macchina_genitore_id"), ["genitore_id"], unique=False)
        batch_op.create_foreign_key(
            NOME_VINCOLO, "voci_macchina", ["genitore_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("voci_macchina", schema=None) as batch_op:
        batch_op.drop_constraint(NOME_VINCOLO, type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_voci_macchina_genitore_id"))
        batch_op.drop_column("genitore_id")
