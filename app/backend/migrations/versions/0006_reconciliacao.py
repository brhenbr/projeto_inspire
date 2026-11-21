"""Reconciliação idempotente: bancos migrados com uma versão intermediária da 0004 ganham o que faltava.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-21

Tudo aqui usa IF NOT EXISTS / OR REPLACE: em um banco novo (que já recebeu a 0004 completa) não faz nada.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.f_busca(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT regexp_replace(public.f_unaccent(lower($1)), 'oes\\y', 'ao', 'g') $$
        """
    )
    op.execute(
        "ALTER TABLE curadoria.colecao ADD COLUMN IF NOT EXISTS ultimos_membros text[] NOT NULL DEFAULT '{}'"
    )
    op.execute("ALTER TABLE curadoria.colecao ADD COLUMN IF NOT EXISTS ultimo_diff jsonb")
    op.execute(
        "ALTER TABLE analitico.conjunto_busca ADD COLUMN IF NOT EXISTS downloads_total bigint NOT NULL DEFAULT 0"
    )
    op.execute("ALTER TABLE analitico.conjunto_busca ADD COLUMN IF NOT EXISTS prioridade numeric")
    op.execute(
        "CREATE INDEX IF NOT EXISTS busca_prioridade ON analitico.conjunto_busca (prioridade DESC NULLS LAST)"
    )


def downgrade() -> None:
    pass  # reconciliação: nada a desfazer (as colunas e a função pertencem à 0004)
