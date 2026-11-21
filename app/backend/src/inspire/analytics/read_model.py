"""Modelo de leitura `analitico.conjunto_busca` (ADR-0008): uma linha por conjunto, já com os valores
EFETIVOS (original + alterações curadas), arrays e texto indexado em português sem acentos.

É um derivado: pode ser reconstruído a qualquer momento a partir de `catalogo` e `curadoria`.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

REFRESH_SQL = text(
    """
    WITH latest AS (
        SELECT DISTINCT ON (conjunto_id, campo) conjunto_id, campo, valor
        FROM curadoria.alteracao
        WHERE CAST(:ids AS text[]) IS NULL OR conjunto_id = ANY(CAST(:ids AS text[]))
        ORDER BY conjunto_id, campo, id DESC
    ),
    alt AS (
        SELECT conjunto_id,
               (array_agg(valor) FILTER (WHERE campo = 'titulo'))[1] AS titulo,
               (array_agg(valor) FILTER (WHERE campo = 'descricao'))[1] AS descricao,
               (array_agg(valor) FILTER (WHERE campo = 'licenca'))[1] AS licenca,
               (array_agg(valor) FILTER (WHERE campo = 'periodicidade'))[1] AS periodicidade,
               (array_agg(valor) FILTER (WHERE campo = 'tags'))[1] AS tags,
               (array_agg(valor) FILTER (WHERE campo = 'temas'))[1] AS temas
        FROM latest
        WHERE valor IS NOT NULL
        GROUP BY conjunto_id
    ),
    eff AS (
        SELECT c.id,
               COALESCE(a.titulo #>> '{}', c.titulo) AS titulo,
               COALESCE(a.descricao #>> '{}', c.descricao) AS descricao,
               c.organizacao_slug, o.titulo AS organizacao_titulo, o.esfera, o.uf,
               COALESCE(a.licenca #>> '{}', c.licenca) AS licenca,
               COALESCE(a.periodicidade #>> '{}', c.periodicidade) AS periodicidade,
               CASE WHEN a.temas IS NOT NULL
                    THEN ARRAY(SELECT jsonb_array_elements_text(a.temas))
                    ELSE ARRAY(SELECT ct.tema_slug FROM catalogo.conjunto_tema ct
                               WHERE ct.conjunto_id = c.id ORDER BY 1)
               END AS temas,
               CASE WHEN a.tags IS NOT NULL
                    THEN ARRAY(SELECT jsonb_array_elements_text(a.tags))
                    ELSE ARRAY(SELECT cg.tag_nome FROM catalogo.conjunto_tag cg
                               WHERE cg.conjunto_id = c.id ORDER BY 1)
               END AS tags,
               ARRAY(SELECT DISTINCT upper(r.formato) FROM catalogo.recurso r
                     WHERE r.conjunto_id = c.id AND r.formato IS NOT NULL AND r.formato <> ''
                     ORDER BY 1) AS formatos,
               c.selo_portal, c.atualizado_portal, c.dados_abertos, c.descontinuado, c.sem_detalhe,
               (c.removido_em IS NOT NULL) AS removido, c.qtd_recursos,
               c.metadados_atualizados_em,
               COALESCE(s.estado, 'pendente') AS estado_curadoria,
               (a.conjunto_id IS NOT NULL) AS curado,
               q.nota AS nota_qualidade,
               COALESCE((SELECT sum(r.downloads) FROM catalogo.recurso r WHERE r.conjunto_id = c.id), 0) AS downloads_total
        FROM catalogo.conjunto c
        LEFT JOIN catalogo.organizacao o ON o.slug = c.organizacao_slug
        LEFT JOIN alt a ON a.conjunto_id = c.id
        LEFT JOIN curadoria.status_conjunto s ON s.conjunto_id = c.id
        LEFT JOIN analitico.qualidade_conjunto q ON q.conjunto_id = c.id
        WHERE CAST(:ids AS text[]) IS NULL OR c.id = ANY(CAST(:ids AS text[]))
    )
    INSERT INTO analitico.conjunto_busca (
        id, titulo, descricao, organizacao_slug, organizacao_titulo, esfera, uf, licenca, periodicidade,
        temas, tags, formatos, selo_portal, atualizado_portal, dados_abertos, descontinuado, sem_detalhe,
        removido, qtd_recursos, metadados_atualizados_em, estado_curadoria, curado, nota_qualidade, downloads_total,
        prioridade, tsv, atualizado_em)
    SELECT id, titulo, descricao, organizacao_slug, organizacao_titulo, esfera, uf, licenca, periodicidade,
           temas, tags, formatos, selo_portal, atualizado_portal, dados_abertos, descontinuado, sem_detalhe,
           removido, qtd_recursos, metadados_atualizados_em, estado_curadoria, curado, nota_qualidade, downloads_total,
           CASE WHEN nota_qualidade IS NULL THEN NULL
                ELSE round(((100 - nota_qualidade) * (1 + ln(1 + downloads_total)))::numeric, 2) END,
           setweight(to_tsvector('portuguese', public.f_busca(COALESCE(titulo, ''))), 'A')
           || setweight(to_tsvector('portuguese', public.f_busca(
                  array_to_string(tags, ' ') || ' ' || array_to_string(temas, ' ') || ' '
                  || COALESCE(organizacao_titulo, ''))), 'B')
           || setweight(to_tsvector('portuguese', public.f_busca(COALESCE(descricao, ''))), 'C'),
           now()
    FROM eff
    ON CONFLICT (id) DO UPDATE SET
        titulo = EXCLUDED.titulo, descricao = EXCLUDED.descricao,
        organizacao_slug = EXCLUDED.organizacao_slug, organizacao_titulo = EXCLUDED.organizacao_titulo,
        esfera = EXCLUDED.esfera, uf = EXCLUDED.uf, licenca = EXCLUDED.licenca,
        periodicidade = EXCLUDED.periodicidade, temas = EXCLUDED.temas, tags = EXCLUDED.tags,
        formatos = EXCLUDED.formatos, selo_portal = EXCLUDED.selo_portal,
        atualizado_portal = EXCLUDED.atualizado_portal, dados_abertos = EXCLUDED.dados_abertos,
        descontinuado = EXCLUDED.descontinuado, sem_detalhe = EXCLUDED.sem_detalhe,
        removido = EXCLUDED.removido, qtd_recursos = EXCLUDED.qtd_recursos,
        metadados_atualizados_em = EXCLUDED.metadados_atualizados_em,
        estado_curadoria = EXCLUDED.estado_curadoria, curado = EXCLUDED.curado,
        nota_qualidade = EXCLUDED.nota_qualidade, downloads_total = EXCLUDED.downloads_total,
        prioridade = EXCLUDED.prioridade, tsv = EXCLUDED.tsv, atualizado_em = now()
    """
)


def refresh_read_model(engine: Engine, ids: list[str] | None = None) -> int:
    """Recalcula o modelo de leitura de alguns conjuntos (ids) ou de todos (None)."""
    with engine.begin() as conn:
        return conn.execute(REFRESH_SQL, {"ids": ids}).rowcount
