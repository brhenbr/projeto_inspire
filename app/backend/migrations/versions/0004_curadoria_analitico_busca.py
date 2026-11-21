"""Curadoria, qualidade e modelo de leitura (ADR-0005, ADR-0008, ADR-0009, ADR-0010).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # unaccent imutável, para poder indexar (a função nativa é apenas "stable")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.f_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        """
    )

    # Normalização de busca: sem acento e com plural "-ões" igual a "-ão" (o stemmer depende do acento).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.f_busca(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT regexp_replace(public.f_unaccent(lower($1)), 'oes\y', 'ao', 'g') $$
        """
    )

    # ---------------- curadoria
    op.execute(
        """
        CREATE TABLE curadoria.alteracao (
            id           bigserial PRIMARY KEY,
            conjunto_id  text NOT NULL,
            campo        text NOT NULL CHECK (campo IN
                         ('titulo', 'descricao', 'tags', 'temas', 'periodicidade', 'licenca')),
            valor        jsonb,
            origem       text NOT NULL CHECK (origem IN ('humano', 'llm')),
            proposta_id  bigint,
            autor        text NOT NULL,
            comentario   text,
            em           timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX alteracao_campo ON curadoria.alteracao (conjunto_id, campo, id DESC)")
    op.execute(
        """
        CREATE TABLE curadoria.status_conjunto (
            conjunto_id    text PRIMARY KEY,
            estado         text NOT NULL CHECK (estado IN
                           ('pendente', 'em_revisao', 'aprovado', 'rejeitado', 'duplicado')),
            duplicado_de   text,
            atualizado_em  timestamptz NOT NULL DEFAULT now(),
            atualizado_por text NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE curadoria.colecao (
            id           bigserial PRIMARY KEY,
            nome         text NOT NULL UNIQUE,
            descricao    text,
            responsavel  text,
            tipo         text NOT NULL CHECK (tipo IN ('manual', 'dinamica')),
            regra_filtro jsonb NOT NULL DEFAULT '{}'::jsonb,
            criada_em    timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE curadoria.colecao_item (
            colecao_id  bigint NOT NULL REFERENCES curadoria.colecao (id) ON DELETE CASCADE,
            conjunto_id text NOT NULL,
            modo        text NOT NULL DEFAULT 'incluir' CHECK (modo IN ('incluir', 'excluir')),
            PRIMARY KEY (colecao_id, conjunto_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE curadoria.llm_tarefa (
            chave           text PRIMARY KEY,
            nome            text NOT NULL,
            descricao       text NOT NULL,
            campo_alvo      text NOT NULL,
            prompt_sistema  text NOT NULL,
            prompt_usuario  text NOT NULL,
            versao          integer NOT NULL DEFAULT 1
        )
        """
    )
    op.execute(
        """
        CREATE TABLE curadoria.llm_execucao (
            id            bigserial PRIMARY KEY,
            tarefa_chave  text NOT NULL REFERENCES curadoria.llm_tarefa (chave),
            tarefa_versao integer NOT NULL,
            estado        text NOT NULL CHECK (estado IN
                          ('enfileirada', 'em_andamento', 'concluida', 'falhou', 'cancelada')),
            conjuntos     jsonb NOT NULL,
            parametros    jsonb NOT NULL DEFAULT '{}'::jsonb,
            provedor      text,
            modelo        text,
            externo       boolean,
            solicitada_por text,
            criada_em     timestamptz NOT NULL DEFAULT now(),
            iniciada_em   timestamptz,
            finalizada_em timestamptz,
            totais        jsonb NOT NULL DEFAULT '{}'::jsonb,
            erro          text
        )
        """
    )
    op.execute(
        """
        CREATE TABLE curadoria.llm_proposta (
            id              bigserial PRIMARY KEY,
            execucao_id     bigint NOT NULL REFERENCES curadoria.llm_execucao (id) ON DELETE CASCADE,
            conjunto_id     text NOT NULL,
            campo           text NOT NULL,
            valor_original  jsonb,
            valor_proposto  jsonb,
            valor_final     jsonb,
            estado          text NOT NULL DEFAULT 'pendente' CHECK (estado IN
                            ('pendente', 'aprovada', 'editada', 'rejeitada', 'desatualizada', 'erro')),
            hash_base       text,
            prompt          text,
            resposta_bruta  text,
            erro            text,
            criada_em       timestamptz NOT NULL DEFAULT now(),
            decidida_em     timestamptz,
            decidida_por    text
        )
        """
    )
    op.execute("CREATE INDEX llm_proposta_estado ON curadoria.llm_proposta (estado, conjunto_id)")

    # ---------------- analitico
    op.execute(
        """
        CREATE TABLE analitico.regra_qualidade (
            chave      text PRIMARY KEY,
            dimensao   text NOT NULL,
            framework  text NOT NULL,
            nome       text NOT NULL,
            descricao  text NOT NULL,
            peso       numeric NOT NULL DEFAULT 1 CHECK (peso >= 0),
            fonte      text NOT NULL,
            ativa      boolean NOT NULL DEFAULT true
        )
        """
    )
    op.execute(
        """
        CREATE TABLE analitico.qualidade_conjunto (
            conjunto_id  text PRIMARY KEY,
            nota         numeric NOT NULL,
            detalhes     jsonb NOT NULL,
            dimensoes    jsonb NOT NULL,
            calculada_em timestamptz NOT NULL DEFAULT now(),
            versao_regras integer NOT NULL DEFAULT 1
        )
        """
    )
    op.execute(
        """
        CREATE TABLE analitico.qualidade_historico (
            id           bigserial PRIMARY KEY,
            conjunto_id  text NOT NULL,
            nota         numeric NOT NULL,
            calculada_em timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX qualidade_historico_conjunto ON analitico.qualidade_historico (conjunto_id, id DESC)"
    )
    op.execute(
        """
        CREATE TABLE analitico.conjunto_busca (
            id                       text PRIMARY KEY,
            titulo                   text NOT NULL,
            descricao                text,
            organizacao_slug         text,
            organizacao_titulo       text,
            esfera                   text,
            uf                       text,
            licenca                  text,
            periodicidade            text,
            temas                    text[] NOT NULL DEFAULT '{}',
            tags                     text[] NOT NULL DEFAULT '{}',
            formatos                 text[] NOT NULL DEFAULT '{}',
            selo_portal              text,
            atualizado_portal        text,
            dados_abertos            boolean,
            descontinuado            boolean NOT NULL DEFAULT false,
            sem_detalhe              boolean NOT NULL DEFAULT false,
            removido                 boolean NOT NULL DEFAULT false,
            qtd_recursos             integer NOT NULL DEFAULT 0,
            metadados_atualizados_em timestamptz,
            estado_curadoria         text NOT NULL DEFAULT 'pendente',
            curado                   boolean NOT NULL DEFAULT false,
            nota_qualidade           numeric,
            downloads_total          bigint NOT NULL DEFAULT 0,
            prioridade               numeric,
            tsv                      tsvector NOT NULL,
            atualizado_em            timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX busca_tsv ON analitico.conjunto_busca USING gin (tsv)")
    op.execute("CREATE INDEX busca_tags ON analitico.conjunto_busca USING gin (tags)")
    op.execute("CREATE INDEX busca_temas ON analitico.conjunto_busca USING gin (temas)")
    op.execute("CREATE INDEX busca_formatos ON analitico.conjunto_busca USING gin (formatos)")
    op.execute("CREATE INDEX busca_org ON analitico.conjunto_busca (organizacao_slug)")
    op.execute(
        "CREATE INDEX busca_prioridade ON analitico.conjunto_busca (prioridade DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX busca_titulo_trgm ON analitico.conjunto_busca "
        "USING gin (public.f_unaccent(lower(titulo)) gin_trgm_ops)"
    )


def downgrade() -> None:
    for table in (
        "analitico.conjunto_busca",
        "analitico.qualidade_historico",
        "analitico.qualidade_conjunto",
        "analitico.regra_qualidade",
        "curadoria.llm_proposta",
        "curadoria.llm_execucao",
        "curadoria.llm_tarefa",
        "curadoria.colecao_item",
        "curadoria.colecao",
        "curadoria.status_conjunto",
        "curadoria.alteracao",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
    op.execute("DROP FUNCTION IF EXISTS public.f_busca(text)")
    op.execute("DROP FUNCTION IF EXISTS public.f_unaccent(text)")
