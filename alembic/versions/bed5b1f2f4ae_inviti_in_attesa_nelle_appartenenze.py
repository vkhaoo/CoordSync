"""inviti in attesa nelle appartenenze

Aggiunge lo stato alla tessera: 'invitata' (un invito che aspetta una
risposta) o 'attiva' (ci lavora davvero).

Rivista a mano dopo l'autogenerate. Una cosa cambiata, ed e' quella che
avrebbe rotto la pubblicazione:

    server_default="attiva"

La colonna e' NOT NULL e la tabella ha gia' dei dati: senza un valore di
riempimento, il database rifiuta di aggiungerla perche' non saprebbe cosa
scrivere nelle righe che ci sono. Il valore giusto e' "attiva": le tessere
esistenti sono di gente che gia' lavora li', non inviti da accettare.

Il tipo enum 'statoappartenenza' invece e' nuovo, quindi qui va bene crearlo
(a differenza di 'ruoloutente' nella migrazione precedente, che esisteva gia').

Revision ID: bed5b1f2f4ae
Revises: 2bd91f251225
Create Date: 2026-09-05 21:41:03.552214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bed5b1f2f4ae'
down_revision: Union[str, Sequence[str], None] = '2bd91f251225'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Su PostgreSQL un enum e' un TIPO a se', e questa riga lo crea prima
    # della colonna che lo usa.
    #
    # NOTA ONESTA: l'avevo aggiunta convinto che senza sarebbe fallita in
    # produzione, e non era vero — la migrazione era gia' passata cosi' com'era.
    # Il ritardo che avevo scambiato per un errore era solo la coda delle
    # pubblicazioni su Render. La riga resta perche' e' comunque piu' sicura
    # (con checkfirst=True la migrazione si puo' ripetere anche se un
    # tentativo si e' fermato a meta'), non perche' servisse a rimediare.
    # Su SQLite non esiste niente da creare e non fa nulla.
    tipo = sa.Enum("invitata", "attiva", name="statoappartenenza")
    tipo.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("appartenenze", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("stato", tipo, nullable=False, server_default="attiva"))


def downgrade() -> None:
    with op.batch_alter_table("appartenenze", schema=None) as batch_op:
        batch_op.drop_column("stato")

    # Su PostgreSQL il tipo resta li' anche dopo aver tolto la colonna che lo
    # usava: va buttato a mano, se no una risalita futura trova il tipo gia'
    # esistente e fallisce. Su SQLite non esiste niente da togliere.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS statoappartenenza")
