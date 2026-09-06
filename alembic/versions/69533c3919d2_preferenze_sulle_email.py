"""preferenze sulle email

Due interruttori sull'utente: ricevere o no l'email quando ti assegnano un
lavoro, e quella che ricorda un impegno in agenda.

IL server_default E' OBBLIGATORIO, e non e' un dettaglio. Le colonne sono NOT
NULL e la tabella ha gia' delle righe: senza un valore predefinito deciso dal
DATABASE, l'aggiunta fallisce su PostgreSQL (le righe esistenti resterebbero a
NULL su una colonna che non lo ammette). Il default= del modello non basta:
quello lo applica Python quando crea un utente nuovo, e qui gli utenti ci sono
gia'.

E il valore predefinito e' ACCESO, non spento: chi non ha mai toccato niente
deve continuare a ricevere quello che riceveva ieri. Una migrazione che
spegne le notifiche di tutti in silenzio si scopre solo quando qualcuno ha
gia' perso un lavoro assegnato.

Revision ID: 69533c3919d2
Revises: 2a018f20b4cd
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '69533c3919d2'
down_revision: Union[str, Sequence[str], None] = '2a018f20b4cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("utenti", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email_assegnazioni", sa.Boolean(),
                                      nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("email_promemoria", sa.Boolean(),
                                      nullable=False, server_default="1"))


def downgrade() -> None:
    # Si perdono solo le preferenze: tornando indietro le email ripartono per
    # tutti, che e' il comportamento di prima. Nessun dato di lavoro e' toccato.
    with op.batch_alter_table("utenti", schema=None) as batch_op:
        batch_op.drop_column("email_promemoria")
        batch_op.drop_column("email_assegnazioni")
