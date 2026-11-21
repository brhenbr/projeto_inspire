"""Portal dados.gov.br falso, fiel ao que foi medido no portal real (ver CLAUDE.md).

Usado nos testes de integração (via httpx.MockTransport) e nos testes E2E (via servidor HTTP).
Reproduz: chave obrigatória (401), listagem de 15 itens por página com `pagina` a partir de 1, datas em
`dd/mm/aaaa hh:mm:ss`, nome e e-mail do responsável no detalhe, respostas vazias intermitentes e detalhes
que devolvem sempre 400.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

PAGE_SIZE = 15
API_KEY = "chave-de-teste"
THEMES = [
    {"name": "saude", "title": "Saúde", "id": "t1", "description": "Dados de saúde"},
    {"name": "educacao", "title": "Educação", "id": "t2", "description": "Dados de educação"},
    {"name": "trabalho", "title": "Trabalho", "id": "t3", "description": "Dados de trabalho"},
]


class FakePortal:
    def __init__(
        self,
        n_datasets: int = 40,
        n_orgs: int = 3,
        *,
        flaky_every: int = 0,
        bad_ids: Iterable[str] = (),
    ) -> None:
        self.flaky_every = flaky_every
        self.bad_ids = set(bad_ids)
        self.hidden_from_listing: set[str] = set()
        self.calls: Counter[str] = Counter()
        self._requests = 0
        self.orgs = [f"orgao-{i + 1}" for i in range(n_orgs)]
        self.datasets: dict[str, dict[str, Any]] = {}
        for i in range(n_datasets):
            self.add(f"ds-{i + 1:04d}", self.orgs[i % n_orgs], i)

    # ------------------------------------------------------------------ mutações
    def add(self, dataset_id: str, org: str, i: int = 0) -> None:
        theme = THEMES[i % len(THEMES)]
        self.datasets[dataset_id] = {
            "id": dataset_id,
            "titulo": f"Conjunto {dataset_id}",
            "nome": f"conjunto-{dataset_id}",
            "organizacao": org,
            "descricao": f"Descrição do conjunto {dataset_id}"
            + (" completa e detalhada" * (i % 3)),
            "licenca": "cc-by" if i % 2 == 0 else None,
            "responsavel": f"Responsável {i}",
            "emailResponsavel": f"resp{i}@{org}.gov.br",
            "periodicidade": ["MENSAL", "ANUAL", None][i % 3],
            "temas": [{"name": theme["name"], "title": theme["title"]}],
            "tags": [
                {"id": f"tag-{i % 5}", "name": f"Tag {i % 5}", "display_name": None},
                {"id": "tag-x", "name": "Comum", "display_name": None},
            ],
            "coberturaTemporalInicio": "01/01/2020" if i % 4 == 0 else None,
            "coberturaTemporalFim": None,
            "coberturaEspacial": None,
            "granularidadeEspacial": None,
            "versao": "1",
            "atualizacaoVersao": False,
            "visibilidade": "PUBLICA",
            "descontinuado": False,
            "dataDescontinuacao": None,
            "reuso": False,
            "recursos": [
                {
                    "id": f"{dataset_id}-r{j}",
                    "idConjuntoDados": dataset_id,
                    "titulo": f"Recurso {j}",
                    "descricao": None,
                    "formato": ["CSV", "PDF", "JSON"][(i + j) % 3],
                    "tipo": None,
                    "link": f"https://{org}.gov.br/{dataset_id}/{j}",
                    "nomeArquivo": f"arquivo{j}",
                    "tamanho": 100 * (j + 1),
                    "quantidadeDownloads": j,
                    "numOrdem": j,
                    "dataCatalogacao": "01/02/2024 10:00:00",
                    "dataUltimaAtualizacaoArquivo": "01/03/2024 10:00:00",
                }
                for j in range(2)
            ],
            "conjuntoDadosAssociados": [],
            "dataUltimaAtualizacaoMetadados": "10/05/2024 08:00:00",
            "dataUltimaAtualizacaoArquivo": "01/03/2024 10:00:00",
            "dataCatalogacao": "01/02/2024 09:00:00",
            "atualizado": "Atualizado" if i % 2 == 0 else "Desatualizado",
            "dadosRacaEtnia": None,
            "dadosGenero": None,
            "observanciaLegal": None,
            "dadosAbertos": "Sim",
            "selo": "Nenhum",
            "origemCadastro": "Portal",
        }

    def update_title(self, dataset_id: str, title: str, when: str = "20/06/2025 12:00:00") -> None:
        self.datasets[dataset_id]["titulo"] = title
        self.datasets[dataset_id]["dataUltimaAtualizacaoMetadados"] = when

    def remove(self, dataset_id: str) -> None:
        del self.datasets[dataset_id]

    # ------------------------------------------------------------------ respostas
    def _summary(self, d: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": d["id"],
            "title": d["titulo"],
            "nome": d["nome"],
            "catalogacao": d["dataCatalogacao"],
            "nomeOrganizacao": d["organizacao"],
            "ultimaAlteracaoMetadados": d["dataUltimaAtualizacaoMetadados"],
            "ultimaAtualizacaoDados": d["dataUltimaAtualizacaoArquivo"],
            "isAtualizado": d["atualizado"] == "Atualizado",
        }

    def _org_doc(self, slug: str) -> dict[str, Any]:
        declared = sum(1 for d in self.datasets.values() if d["organizacao"] == slug)
        return {
            "id": f"id-{slug}",
            "titulo": f"Órgão {slug}",
            "nome": slug,
            "descricao": "Órgão de teste",
            "qtdConjuntoDeDados": str(declared),
            "organizationEsfera": "1",
            "organizationUf": "DF",
            "organizationMunicipio": "Brasília",
        }

    def handle(self, path: str, params: dict[str, str], api_key: str | None) -> tuple[int, Any]:
        if api_key != API_KEY:
            return 401, None
        self._requests += 1
        flaky_empty = bool(self.flaky_every) and self._requests % self.flaky_every == 0

        def page(items: list[Any]) -> tuple[int, Any]:
            n = int(params.get("pagina", "0"))
            if n < 1:
                return 400, {"Erro na API": "Erro ao executar a consulta"}
            return 200, [] if flaky_empty else items[(n - 1) * PAGE_SIZE : n * PAGE_SIZE]

        if path == "/dados/api/temas":
            self.calls["dim"] += 1
            return 200, THEMES
        if path == "/dados/api/publico/conjuntos-dados/formatos":
            self.calls["dim"] += 1
            return 200, ["", "CSV", "JSON", "PDF"]
        if path == "/dados/api/publico/conjuntos-dados/observancia-legal":
            self.calls["dim"] += 1
            return 200, [{"id": 1, "descricao": "Público"}]
        if path == "/dados/api/publico/organizacao":
            self.calls["org"] += 1
            return page([self._org_doc(o) for o in self.orgs])
        if path == "/dados/api/publico/conjuntos-dados":
            self.calls["list"] += 1
            visible = [
                self._summary(d)
                for d in self.datasets.values()
                if d["id"] not in self.hidden_from_listing
            ]
            return page(visible)
        prefix = "/dados/api/publico/conjuntos-dados/"
        if path.startswith(prefix):
            self.calls["detail"] += 1
            dataset_id = path.removeprefix(prefix)
            if dataset_id in self.bad_ids:
                return 400, {"Erro na API": "Erro ao executar a consulta"}
            if dataset_id not in self.datasets:
                return 404, None
            return 200, {} if flaky_empty else self.datasets[dataset_id]
        return 404, None
