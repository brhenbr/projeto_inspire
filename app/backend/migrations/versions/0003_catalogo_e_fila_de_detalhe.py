"""Camada catalogo (espelho tabular) e fila de detalhe da extração (ADR-0005, ADR-0007).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- raw: controle de execução e fila de detalhe (retomável)
    op.execute(
        "ALTER TABLE raw.execucao ADD COLUMN cancelar_solicitado boolean NOT NULL DEFAULT false"
    )
    op.execute("ALTER TABLE raw.execucao ADD COLUMN batimento_em timestamptz")
    op.execute(
        """
        CREATE TABLE raw.fila_detalhe (
            execucao_id  bigint NOT NULL REFERENCES raw.execucao (id) ON DELETE CASCADE,
            conjunto_id  text NOT NULL,
            resumo       jsonb NOT NULL,
            estado       text NOT NULL DEFAULT 'pendente'
                         CHECK (estado IN ('pendente', 'concluido', 'sem_detalhe', 'erro')),
            motivo       text,
            PRIMARY KEY (execucao_id, conjunto_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX fila_detalhe_pendente ON raw.fila_detalhe (execucao_id) WHERE estado = 'pendente'"
    )

    # --- catalogo: espelho tabular, reconstruível a partir do raw
    op.execute(
        """
        CREATE TABLE catalogo.organizacao (
            slug            text PRIMARY KEY,
            id              text,
            titulo          text NOT NULL,
            descricao       text,
            esfera          text CHECK (esfera IN ('federal', 'estadual', 'municipal')),
            uf              text,
            municipio       text,
            qtd_declarada   integer NOT NULL DEFAULT 0,
            atualizado_em   timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE catalogo.tema (
            slug       text PRIMARY KEY,
            id         text,
            titulo     text NOT NULL,
            descricao  text
        )
        """
    )
    op.execute("CREATE TABLE catalogo.formato (nome text PRIMARY KEY)")
    op.execute(
        "CREATE TABLE catalogo.observancia_legal (id integer PRIMARY KEY, descricao text NOT NULL)"
    )
    op.execute("CREATE TABLE catalogo.tag (nome text PRIMARY KEY)")
    op.execute(
        """
        CREATE TABLE catalogo.conjunto (
            id                          text PRIMARY KEY,
            slug                        text,
            titulo                      text NOT NULL,
            descricao                   text,
            organizacao_slug            text,
            licenca                     text,
            periodicidade               text,
            cobertura_temporal_inicio   text,
            cobertura_temporal_fim      text,
            cobertura_espacial          text,
            granularidade_espacial      text,
            versao                      text,
            descontinuado               boolean NOT NULL DEFAULT false,
            dados_abertos               boolean,
            selo_portal                 text,
            atualizado_portal           text,
            origem_cadastro             text,
            visibilidade                text,
            observancia_legal           text,
            tem_responsavel             boolean NOT NULL DEFAULT false,
            tem_email_responsavel       boolean NOT NULL DEFAULT false,
            catalogado_em               timestamptz,
            metadados_atualizados_em    timestamptz,
            dados_atualizados_em        timestamptz,
            alteracao_listagem          text,
            qtd_recursos                integer NOT NULL DEFAULT 0,
            sem_detalhe                 boolean NOT NULL DEFAULT false,
            hash_atual                  text,
            primeira_vez_em             timestamptz NOT NULL DEFAULT now(),
            ultima_vez_em               timestamptz NOT NULL DEFAULT now(),
            removido_em                 timestamptz
        )
        """
    )
    op.execute("CREATE INDEX conjunto_organizacao ON catalogo.conjunto (organizacao_slug)")
    op.execute(
        """
        CREATE TABLE catalogo.recurso (
            id                text PRIMARY KEY,
            conjunto_id       text NOT NULL REFERENCES catalogo.conjunto (id) ON DELETE CASCADE,
            titulo            text,
            descricao         text,
            formato           text,
            tipo              text,
            link              text,
            nome_arquivo      text,
            tamanho           bigint,
            downloads         integer,
            ordem             integer,
            catalogado_em     timestamptz,
            atualizado_em     timestamptz
        )
        """
    )
    op.execute("CREATE INDEX recurso_conjunto ON catalogo.recurso (conjunto_id)")
    op.execute(
        """
        CREATE TABLE catalogo.conjunto_tema (
            conjunto_id text NOT NULL REFERENCES catalogo.conjunto (id) ON DELETE CASCADE,
            tema_slug   text NOT NULL,
            PRIMARY KEY (conjunto_id, tema_slug)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE catalogo.conjunto_tag (
            conjunto_id text NOT NULL REFERENCES catalogo.conjunto (id) ON DELETE CASCADE,
            tag_nome    text NOT NULL,
            PRIMARY KEY (conjunto_id, tag_nome)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE catalogo.conjunto_associado (
            conjunto_id  text NOT NULL REFERENCES catalogo.conjunto (id) ON DELETE CASCADE,
            associado_id text NOT NULL,
            PRIMARY KEY (conjunto_id, associado_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE catalogo.conjunto_historico (
            id           bigserial PRIMARY KEY,
            conjunto_id  text NOT NULL,
            execucao_id  bigint NOT NULL,
            evento       text NOT NULL CHECK (evento IN ('novo', 'alterado', 'removido', 'reaparecido')),
            em           timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX conjunto_historico_conjunto ON catalogo.conjunto_historico (conjunto_id, id DESC)"
    )
    op.execute(
        "CREATE INDEX conjunto_historico_execucao ON catalogo.conjunto_historico (execucao_id)"
    )


def downgrade() -> None:
    for table in (
        "conjunto_historico",
        "conjunto_associado",
        "conjunto_tag",
        "conjunto_tema",
        "recurso",
        "conjunto",
        "tag",
        "observancia_legal",
        "formato",
        "tema",
        "organizacao",
    ):
        op.execute(f"DROP TABLE IF EXISTS catalogo.{table}")
    op.execute("DROP TABLE IF EXISTS raw.fila_detalhe")
    op.execute("ALTER TABLE raw.execucao DROP COLUMN IF EXISTS batimento_em")
    op.execute("ALTER TABLE raw.execucao DROP COLUMN IF EXISTS cancelar_solicitado")
