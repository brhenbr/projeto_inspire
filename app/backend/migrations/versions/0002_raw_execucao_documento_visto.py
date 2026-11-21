"""Camada raw: execuções, documentos brutos e o que cada execução viu (ADR-0005, ADR-0006).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE raw.execucao (
            id             bigserial PRIMARY KEY,
            tipo           text NOT NULL CHECK (tipo IN ('incremental', 'completa')),
            forcada        boolean NOT NULL DEFAULT false,
            solicitada_por text,
            estado         text NOT NULL CHECK (estado IN (
                'enfileirada', 'em_andamento', 'pausada', 'concluida',
                'concluida_com_divergencias', 'falhou', 'cancelada')),
            criada_em      timestamptz NOT NULL DEFAULT now(),
            iniciada_em    timestamptz,
            finalizada_em  timestamptz,
            parametros     jsonb NOT NULL DEFAULT '{}'::jsonb,
            totais         jsonb NOT NULL DEFAULT '{}'::jsonb,
            erro           text
        )
        """
    )
    # Uma execução ativa por vez, garantida pelo banco e não só pelo código (ADR-0006).
    op.execute(
        """
        CREATE UNIQUE INDEX execucao_uma_ativa ON raw.execucao ((true))
        WHERE estado IN ('enfileirada', 'em_andamento', 'pausada')
        """
    )
    op.execute(
        """
        CREATE TABLE raw.documento (
            id            bigserial PRIMARY KEY,
            tipo          text NOT NULL,
            chave_externa text NOT NULL,
            hash          text NOT NULL,
            payload       jsonb NOT NULL,
            execucao_id   bigint NOT NULL REFERENCES raw.execucao (id),
            coletado_em   timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX documento_chave ON raw.documento (tipo, chave_externa, id DESC)")
    op.execute(
        """
        CREATE TABLE raw.visto (
            execucao_id   bigint NOT NULL REFERENCES raw.execucao (id),
            tipo          text NOT NULL,
            chave_externa text NOT NULL,
            documento_id  bigint NOT NULL REFERENCES raw.documento (id),
            PRIMARY KEY (execucao_id, tipo, chave_externa)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS raw.visto")
    op.execute("DROP TABLE IF EXISTS raw.documento")
    op.execute("DROP TABLE IF EXISTS raw.execucao")
