"""add required user name

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("name", sa.String(length=120), nullable=True))
    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id, email FROM users")).all()
    for user_id, email in users:
        fallback = (email.split("@", 1)[0] or "Usuário")[:120]
        connection.execute(
            sa.text("UPDATE users SET name = :name WHERE id = :id"),
            {"name": fallback, "id": user_id},
        )
    with op.batch_alter_table("users") as batch:
        batch.alter_column("name", existing_type=sa.String(length=120), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("name")
