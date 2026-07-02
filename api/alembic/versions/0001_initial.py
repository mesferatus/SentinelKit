"""Create the initial SentinelKit schema."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.database import UTCDateTime

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

scan_type = sa.Enum(
    "recon", "webaudit", name="scan_type", native_enum=False, create_constraint=True
)
scan_status = sa.Enum(
    "pending",
    "running",
    "completed",
    "failed",
    name="scan_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "authorized_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target", sa.String(255), nullable=False),
        sa.Column("evidence", sa.String(1000), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("expires_at", UTCDateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint("confirmed = true", name="ck_authorized_target_confirmed"),
        sa.CheckConstraint("length(target) > 0", name="ck_authorized_target_not_empty"),
        sa.UniqueConstraint(
            "id", "user_id", name="uq_authorized_target_id_user_id"
        ),
        sa.UniqueConstraint(
            "user_id", "target", name="uq_authorized_target_user_target"
        ),
    )
    op.create_index(
        "ix_authorized_targets_user_id", "authorized_targets", ["user_id"]
    )
    op.create_index("ix_authorized_targets_target", "authorized_targets", ["target"])
    op.create_index(
        "ix_authorized_targets_expires_at", "authorized_targets", ["expires_at"]
    )
    op.create_index("ix_authorized_targets_active", "authorized_targets", ["active"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("expires_at", UTCDateTime(), nullable=False),
        sa.Column("revoked_at", UTCDateTime(), nullable=True),
        sa.Column(
            "replaced_by_id",
            sa.Integer(),
            sa.ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.UniqueConstraint("token_hash"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", scan_type, nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("status", scan_status, nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id", "user_id"],
            ["authorized_targets.id", "authorized_targets.user_id"],
            name="fk_scan_result_target_owner",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("task_id"),
    )
    for name in ("user_id", "type", "target_id", "task_id", "status"):
        op.create_index(f"ix_scan_results_{name}", "scan_results", [name])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("source_ip", sa.String(45), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("timestamp", UTCDateTime(), nullable=False),
    )
    for name in ("user_id", "endpoint", "source_ip", "status_code", "timestamp"):
        op.create_index(f"ix_audit_logs_{name}", "audit_logs", [name])

    op.create_table(
        "siem_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("timestamp", UTCDateTime(), nullable=False),
    )
    for name in ("user_id", "source", "timestamp"):
        op.create_index(f"ix_siem_analyses_{name}", "siem_analyses", [name])


def downgrade() -> None:
    op.drop_table("siem_analyses")
    op.drop_table("audit_logs")
    op.drop_table("scan_results")
    op.drop_table("refresh_tokens")
    op.drop_table("authorized_targets")
    op.drop_table("users")
