import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LlmProposta } from "./api";
import PropostaCard from "./PropostaCard";
import { calls, mockApi, renderAt } from "./test-utils";

const proposta = (over: Partial<LlmProposta> = {}): LlmProposta => ({
  id: 7, execucao_id: 1, conjunto_id: "ds-1", conjunto_titulo: "Conjunto de teste", campo: "tags",
  valor_original: ["a"], valor_proposto: ["a", "b", "c"], valor_final: null, estado: "pendente", erro: null,
  provedor: "simulado", modelo: "regras", externo: false, tarefa_chave: "sugerir-tags", ...over,
});

describe("PropostaCard", () => {
  it("mostra o valor atual e a sugestão lado a lado, com a origem", () => {
    renderAt(<PropostaCard p={proposta()} onDone={() => {}} />);

    expect(screen.getByText("Valor atual").nextSibling).toHaveTextContent("a");
    expect(screen.getByText("Sugestão").nextSibling).toHaveTextContent("a, b, c");
    expect(screen.getByText(/simulado/)).toBeInTheDocument();
  });

  it("marca provedor externo de forma visível", () => {
    renderAt(<PropostaCard p={proposta({ provedor: "openai-compatible", externo: true })} onDone={() => {}} />);

    expect(screen.getByText(/EXTERNO/)).toBeInTheDocument();
  });

  it("aprovar envia a decisão e avisa quem chamou", async () => {
    const spy = mockApi({ "/llm/propostas": { estado: "aprovada" } });
    const onDone = vi.fn();
    renderAt(<PropostaCard p={proposta()} onDone={onDone} />);

    await userEvent.click(screen.getByRole("button", { name: "Aprovar" }));

    const c = calls(spy)[0];
    expect(c.url.pathname).toBe("/api/v1/llm/propostas/7/decidir");
    expect(JSON.parse(String(c.init?.body))).toEqual({ decisao: "aprovar" });
    expect(onDone).toHaveBeenCalled();
  });

  it("editar converte texto em lista para tags", async () => {
    const spy = mockApi({ "/llm/propostas": { estado: "editada" } });
    renderAt(<PropostaCard p={proposta()} onDone={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Editar" }));
    const box = screen.getByLabelText("Valor editado da proposta 7");
    await userEvent.clear(box);
    await userEvent.type(box, "x, y ,, z");
    await userEvent.click(screen.getByRole("button", { name: "Salvar edição e aplicar" }));

    expect(JSON.parse(String(calls(spy)[0].init?.body))).toEqual({ decisao: "editar", valor: ["x", "y", "z"] });
  });

  it("rejeitar não exige nada além da decisão", async () => {
    const spy = mockApi({ "/llm/propostas": { estado: "rejeitada" } });
    renderAt(<PropostaCard p={proposta()} onDone={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Rejeitar" }));

    expect(JSON.parse(String(calls(spy)[0].init?.body))).toEqual({ decisao: "rejeitar" });
  });

  it("mostra o motivo quando a proposta ficou desatualizada (409)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: "O conjunto mudou depois da proposta" }) }),
    );
    renderAt(<PropostaCard p={proposta()} onDone={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Aprovar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("O conjunto mudou depois da proposta");
  });

  it("proposta já decidida não oferece botões; com erro mostra o motivo", () => {
    const { unmount } = renderAt(<PropostaCard p={proposta({ estado: "aprovada", valor_final: ["a", "b"] })} onDone={() => {}} />);
    expect(screen.queryByRole("button", { name: "Aprovar" })).not.toBeInTheDocument();
    expect(screen.getByText("Aprovada")).toBeInTheDocument();
    unmount();

    renderAt(<PropostaCard p={proposta({ estado: "erro", erro: "Resposta inválida do modelo" })} onDone={() => {}} />);
    expect(screen.getByText("Resposta inválida do modelo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
  });
});
