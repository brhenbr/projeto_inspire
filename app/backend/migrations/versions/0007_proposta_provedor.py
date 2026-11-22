"""Registra qual provedor respondeu cada proposta de LLM (roteador, ADR-0014).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE curadoria.llm_proposta ADD COLUMN IF NOT EXISTS provedor text")


def downgrade() -> None:
    op.execute("ALTER TABLE curadoria.llm_proposta DROP COLUMN IF EXISTS provedor")
