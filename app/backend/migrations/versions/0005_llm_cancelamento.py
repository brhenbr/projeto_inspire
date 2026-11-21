"""Cancelamento de execuções de LLM (ADR-0011).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE curadoria.llm_execucao ADD COLUMN cancelar_solicitado boolean NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE curadoria.llm_execucao DROP COLUMN IF EXISTS cancelar_solicitado")
