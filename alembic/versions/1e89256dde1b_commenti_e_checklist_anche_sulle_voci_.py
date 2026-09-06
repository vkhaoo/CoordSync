"""commenti e checklist anche sulle voci di macchina

Una voce del taccuino di una macchina non era discutibile ne' spuntabile: si
poteva solo scrivere e rileggere. Ma intorno a un guasto si discute ("ho
provato a...", "ricontrolla la taratura") e si tiene il conto dei passi da
fare, esattamente come sui lavori di progetto. Invece di duplicare due tabelle
identiche si riusano quelle che ci sono gia', come si fa da sempre con gli
allegati: una colonna per ogni possibile genitore, valorizzata una sola.

Rivista a mano dopo l'autogenerate. Tre cose cambiate:

- i vincoli di chiave esterna sono NOMINATI. Alembic li genera con None e poi
  il downgrade non sa cosa togliere: fallisce sul posto;
- l'ordine dentro il batch: la colonna nuova si aggiunge PRIMA di renderla
  raggiungibile, e su SQLite l'intero blocco ricostruisce la tabella una volta
  sola;
- il DOWNGRADE non butta via niente. L'autogenerate rimetteva lavoro_id a NOT
  NULL: appena qualcuno avesse commentato una macchina, tornare indietro
  sarebbe fallito, oppure — peggio — avrebbe preteso di cancellare quei
  commenti per riuscirci. Qui il vincolo si rimette solo se si puo' farlo
  senza toccare una riga; se ci sono commenti di macchina la colonna resta
  permissiva e lo si dice a voce alta. Il testo, l'autore e la data restano
  scritti nel database: invisibili all'app, ma recuperabili a mano.

Revision ID: 1e89256dde1b
Revises: 17fd0080a243
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1e89256dde1b'
down_revision: Union[str, Sequence[str], None] = '17fd0080a243'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_COMMENTI = "fk_commenti_voce_id"
FK_SOTTO = "fk_sotto_attivita_voce_id"


def upgrade() -> None:
    with op.batch_alter_table("commenti", schema=None) as batch_op:
        batch_op.add_column(sa.Column("voce_id", sa.Integer(), nullable=True))
        # Da qui in poi un commento puo' stare su un lavoro OPPURE su una voce:
        # non si puo' piu' pretendere il lavoro.
        batch_op.alter_column("lavoro_id", existing_type=sa.INTEGER(), nullable=True)
        batch_op.create_index(batch_op.f("ix_commenti_lavoro_id"), ["lavoro_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commenti_voce_id"), ["voce_id"], unique=False)
        batch_op.create_foreign_key(FK_COMMENTI, "voci_macchina", ["voce_id"], ["id"],
                                    ondelete="CASCADE")

    with op.batch_alter_table("sotto_attivita", schema=None) as batch_op:
        batch_op.add_column(sa.Column("voce_id", sa.Integer(), nullable=True))
        batch_op.alter_column("lavoro_id", existing_type=sa.INTEGER(), nullable=True)
        batch_op.create_index(batch_op.f("ix_sotto_attivita_lavoro_id"), ["lavoro_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sotto_attivita_voce_id"), ["voce_id"], unique=False)
        batch_op.create_foreign_key(FK_SOTTO, "voci_macchina", ["voce_id"], ["id"],
                                    ondelete="CASCADE")


def _quante_orfane(tabella: str) -> int:
    """Quante righe resterebbero senza genitore tornando indietro."""
    return op.get_bind().execute(
        sa.text(f"SELECT COUNT(*) FROM {tabella} WHERE lavoro_id IS NULL")
    ).scalar() or 0


def downgrade() -> None:
    # Si conta PRIMA di toccare le tabelle: dopo, la colonna che dice dove
    # stavano quelle righe non c'e' piu'.
    orfani_commenti = _quante_orfane("commenti")
    orfane_spunte = _quante_orfane("sotto_attivita")

    with op.batch_alter_table("sotto_attivita", schema=None) as batch_op:
        batch_op.drop_constraint(FK_SOTTO, type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_sotto_attivita_voce_id"))
        batch_op.drop_index(batch_op.f("ix_sotto_attivita_lavoro_id"))
        batch_op.drop_column("voce_id")
        if orfane_spunte == 0:
            batch_op.alter_column("lavoro_id", existing_type=sa.INTEGER(), nullable=False)

    with op.batch_alter_table("commenti", schema=None) as batch_op:
        batch_op.drop_constraint(FK_COMMENTI, type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_commenti_voce_id"))
        batch_op.drop_index(batch_op.f("ix_commenti_lavoro_id"))
        batch_op.drop_column("voce_id")
        if orfani_commenti == 0:
            batch_op.alter_column("lavoro_id", existing_type=sa.INTEGER(), nullable=False)

    if orfani_commenti or orfane_spunte:
        print(
            f"\nATTENZIONE: {orfani_commenti} commenti e {orfane_spunte} spunte "
            "erano appesi a voci di macchina.\n"
            "NON sono stati cancellati: restano nel database con il loro testo, "
            "il loro autore e la loro data,\nma l'app non li vede piu' perche' la "
            "colonna che diceva dove stavano non c'e' piu'.\n"
            "Per questo lavoro_id resta permissiva invece di tornare NOT NULL: "
            "rimetterla avrebbe voluto dire buttarli via.\n"
        )
