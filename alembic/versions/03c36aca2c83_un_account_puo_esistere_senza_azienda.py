"""un account puo' esistere senza azienda

Iscriversi e creare un'azienda diventano due gesti separati: prima nasce
l'account, poi da dentro l'app si crea la prima azienda o si accetta un
invito. Quindi `utenti.organizzazione_id` puo' restare vuota.

La salita non tocca nessun dato: allarga soltanto quello che e' ammesso.

La DISCESA invece e' delicata, ed e' scritta a mano. Tornare a NOT NULL con
delle righe vuote farebbe fallire l'ALTER; quindi prima si tolgono di mezzo
gli account senza azienda. Si possono cancellare senza perdere niente proprio
perche' non appartengono a nessun posto: non hanno progetti, lavori, commenti
o voci di storico — quelle cose esistono solo dentro un'azienda. E' l'unico
esito possibile, ma va detto invece che scoperto.

Revision ID: 03c36aca2c83
Revises: f465708f9686
Create Date: 2026-09-05 22:31:09.847221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03c36aca2c83'
down_revision: Union[str, Sequence[str], None] = 'f465708f9686'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("utenti", schema=None) as batch_op:
        batch_op.alter_column("organizzazione_id",
                              existing_type=sa.INTEGER(),
                              nullable=True)


def downgrade() -> None:
    # Prima le tessere (la chiave esterna punta all'utente), poi gli account.
    op.execute("""
        DELETE FROM appartenenze
        WHERE utente_id IN (SELECT id FROM utenti WHERE organizzazione_id IS NULL)
    """)
    op.execute("DELETE FROM utenti WHERE organizzazione_id IS NULL")

    with op.batch_alter_table("utenti", schema=None) as batch_op:
        batch_op.alter_column("organizzazione_id",
                              existing_type=sa.INTEGER(),
                              nullable=False)
