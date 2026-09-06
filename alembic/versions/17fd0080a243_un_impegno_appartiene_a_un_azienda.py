"""un impegno appartiene a un'azienda

Chiude una fuga fra aziende trovata attaccando l'app: un consulente che lavora
per due clienti organizzava una riunione per il primo e, essendo membro anche
del secondo, i colleghi del secondo se la vedevano comparire in agenda. La
causa era di modello — un impegno apparteneva solo a delle PERSONE, quindi per
capire chi potesse vederlo si guardava l'azienda dell'organizzatore, che di
aziende ne ha due.

Rivista a mano dopo l'autogenerate. Due cose cambiate:

- il vincolo di chiave esterna e' NOMINATO (Alembic lo genera anonimo e poi il
  downgrade non sa cosa togliere);
- soprattutto, c'e' il TRAVASO dei dati, che l'autogenerate non fa mai: gli
  impegni gia' esistenti prendono l'azienda "di casa" del loro organizzatore.
  E' il valore giusto perche' prima del multi-azienda ognuno ne aveva
  esattamente una. Senza queste righe gli impegni gia' presi sparirebbero
  dalla vista "tutta l'azienda".

Revision ID: 17fd0080a243
Revises: a542713155ab
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '17fd0080a243'
down_revision: Union[str, Sequence[str], None] = 'a542713155ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOME_VINCOLO = "fk_impegni_organizzazione_id"


def upgrade() -> None:
    with op.batch_alter_table("impegni", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organizzazione_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_impegni_organizzazione_id"),
                              ["organizzazione_id"], unique=False)
        batch_op.create_foreign_key(NOME_VINCOLO, "organizzazioni",
                                    ["organizzazione_id"], ["id"], ondelete="CASCADE")

    # --- il travaso: ogni impegno prende l'azienda di chi l'ha organizzato ---
    op.execute("""
        UPDATE impegni
        SET organizzazione_id = (
            SELECT organizzazione_id FROM utenti WHERE utenti.id = impegni.organizzatore_id
        )
        WHERE organizzazione_id IS NULL
    """)


def downgrade() -> None:
    # Si perde solo il legame con l'azienda: gli impegni restano tutti, e si
    # torna a decidere chi li vede guardando l'organizzatore (con la fuga che
    # ne consegue, ma e' lo stato di prima).
    with op.batch_alter_table("impegni", schema=None) as batch_op:
        batch_op.drop_constraint(NOME_VINCOLO, type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_impegni_organizzazione_id"))
        batch_op.drop_column("organizzazione_id")
