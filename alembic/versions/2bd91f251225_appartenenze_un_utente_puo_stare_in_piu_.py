"""appartenenze: un utente puo' stare in piu' aziende

Crea la tabella delle tessere di appartenenza e **ci travasa dentro la
situazione di adesso**: ogni utente esistente diventa membro della sua azienda,
con il ruolo che ha gia'.

Il travaso lo scrivo a mano perche' l'autogenerate non lo fa: lui vede solo la
tabella nuova e vuota. Senza queste due righe, al primo avvio nessuno
risulterebbe piu' membro di niente e l'app si svuoterebbe per tutti.

Dopo questa migrazione il comportamento e' IDENTICO a prima: le tessere ci
sono ma non le usa ancora nessuno. E' voluto — una migrazione che sposta dati
e una che cambia logica non devono viaggiare insieme, se no quando qualcosa va
storto non si sa quale delle due incolpare.

Revision ID: 2bd91f251225
Revises: cad8fe0afe14
Create Date: 2026-09-05 19:14:22.108431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2bd91f251225'
down_revision: Union[str, Sequence[str], None] = 'cad8fe0afe14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tipo_ruolo():
    """Il tipo della colonna 'ruolo', diverso a seconda del database.

    QUI C'ERA UNA TRAPPOLA che in locale non si vedeva. Su PostgreSQL un enum
    e' un TIPO vero, creato una volta sola: 'ruoloutente' esiste gia' dallo
    schema iniziale, dove lo usa la tabella utenti. Un sa.Enum dentro
    create_table proverebbe a CREARLO DI NUOVO, e la migrazione morirebbe in
    produzione con "type ruoloutente already exists" — mentre in locale, su
    SQLite (dove gli enum sono semplici stringhe), sarebbe passata liscia.

    Con create_type=False si dice a PostgreSQL: il tipo c'e' gia', usalo e
    basta. E' anche il motivo per cui tutte le migrazioni precedenti non
    avevano il problema: creavano tipi nuovi, non ne riusavano uno.
    """
    valori = ("admin", "caposquadra", "operatore")
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.ENUM(*valori, name="ruoloutente", create_type=False)
    return sa.Enum(*valori, name="ruoloutente")


def upgrade() -> None:
    op.create_table(
        "appartenenze",
        sa.Column("utente_id", sa.Integer(), nullable=False),
        sa.Column("organizzazione_id", sa.Integer(), nullable=False),
        sa.Column("ruolo", _tipo_ruolo(), nullable=False),
        sa.Column("creato_il", sa.DateTime(), nullable=True),
        # I vincoli hanno un nome: Alembic li genererebbe anonimi, e il giorno
        # che servisse toccarli il downgrade non saprebbe cosa togliere.
        sa.ForeignKeyConstraint(["organizzazione_id"], ["organizzazioni.id"],
                                name="fk_appartenenze_organizzazione_id",
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["utente_id"], ["utenti.id"],
                                name="fk_appartenenze_utente_id",
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("utente_id", "organizzazione_id"),
    )

    # --- il travaso: la situazione di adesso diventa la prima tessera ---
    op.execute("""
        INSERT INTO appartenenze (utente_id, organizzazione_id, ruolo, creato_il)
        SELECT id, organizzazione_id, ruolo, CURRENT_TIMESTAMP
        FROM utenti
        WHERE organizzazione_id IS NOT NULL
    """)


def downgrade() -> None:
    # Si torna indietro senza perdere niente di quello che c'era prima: la
    # riga dell'utente non e' mai stata toccata, tiene ancora la sua azienda e
    # il suo ruolo. Si perdono solo le appartenenze IN PIU' aggiunte nel
    # frattempo, che prima di questa migrazione non potevano esistere.
    op.drop_table("appartenenze")
