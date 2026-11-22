"use strict";
/* Roteiro de Testes: SPA simples, sem dependências. Todo texto entra como nó de texto (nada de HTML injetado). */

const RESULTADOS = { passou: "Passou", falhou: "Falhou", nao_executou: "Não consegui executar" };
const MARCAS = { passou: "✓", falhou: "✗", nao_executou: "!" };
const app = document.getElementById("app");
const quem = document.getElementById("quem");
const guarda = { get: (k) => localStorage.getItem("rt." + k), set: (k, v) => localStorage.setItem("rt." + k, v) };

function h(tag, attrs, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, "");
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const f of filhos.flat()) if (f != null && f !== false) el.append(f.nodeType ? f : document.createTextNode(String(f)));
  return el;
}

async function api(metodo, caminho, corpo, cabecalhos) {
  const resp = await fetch("/api" + caminho, {
    method: metodo,
    headers: { "Content-Type": "application/json", ...(cabecalhos || {}) },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const dados = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(dados.detail || "Erro " + resp.status);
  return dados;
}

async function baixarArquivo(caminho, nome) {
  const r = await fetch(caminho);
  if (!r.ok) return;
  const a = h("a", { href: URL.createObjectURL(await r.blob()), download: nome });
  document.body.append(a);
  a.click();
  a.remove();
}

function montar(...nos) {
  app.replaceChildren(...nos.flat().filter(Boolean));
  window.scrollTo(0, 0);
}

/* ------------------------------------------------------------------ início */
async function telaInicio() {
  quem.textContent = "";
  let roteiros;
  try {
    roteiros = await api("GET", "/roteiros");
  } catch (e) {
    return montar(h("p", { class: "erro" }, e.message));
  }
  const nome = h("input", { type: "text", id: "nome", maxlength: 80, value: guarda.get("nome") || "", autocomplete: "name" });
  const sel = h("select", { id: "roteiro" }, roteiros.map((r) => h("option", { value: r.roteiro }, `${r.titulo} (${r.total} casos)`)));
  const msg = h("p", { class: "erro" });
  const ir = h("button", {
    type: "button",
    onclick: async () => {
      msg.textContent = "";
      try {
        const s = await api("POST", "/sessoes", { roteiro: sel.value, testador: nome.value });
        guarda.set("nome", nome.value.trim());
        location.hash = `#/sessao/${s.sessao.id}`;
      } catch (e) {
        msg.textContent = e.message;
      }
    },
  }, "Começar ou continuar");
  montar(
    h("h1", {}, "Roteiro de Testes"),
    h("p", { class: "sub" }, "Você vai executar cada caso no sistema e marcar o resultado aqui, um de cada vez. Se já começou antes com o mesmo nome, continua de onde parou."),
    roteiros.length === 0
      ? h("div", { class: "aviso" }, "Nenhum roteiro encontrado na pasta de casos.")
      : h("div", { class: "card" },
          h("label", { for: "nome" }, "Seu nome"), nome,
          h("label", { for: "roteiro" }, "Roteiro"), sel,
          h("div", { class: "linha" }, ir), msg),
  );
}

/* ------------------------------------------------------------------ sessão */
async function telaSessao(id, casoId) {
  let d;
  try {
    d = await api("GET", `/sessoes/${id}`);
  } catch (e) {
    return montar(h("p", { class: "erro" }, e.message), h("a", { href: "#/" }, "Voltar ao início"));
  }
  const casos = d.roteiro.casos;
  quem.textContent = `${d.sessao.testador} · ${d.roteiro.titulo}`;
  const respondidos = Object.keys(d.respostas).length;
  const atual = casos.find((c) => c.id === casoId) || casos.find((c) => !d.respostas[c.id]) || casos[0];
  const idx = casos.indexOf(atual);

  const lateral = h("ul", { class: "lista" }, casos.map((c) => {
    const r = d.respostas[c.id]?.resultado;
    return h("li", {}, h("a", { href: `#/sessao/${id}/${c.id}`, class: casoId !== "resumo" && c.id === atual.id ? "atual" : "" },
      h("span", { class: `marca-resultado ${r ? "r-" + r : "r-vazio"}` }, r ? MARCAS[r] : "·"), `${c.id} · ${c.titulo}`));
  }));
  const barra = h("div", { class: "barra" }, h("div", {}));
  barra.firstChild.style.width = `${Math.round((respondidos / casos.length) * 100)}%`;

  montar(
    d.roteiro_atualizado ? h("div", { class: "aviso" }, "Este roteiro foi atualizado depois que você começou. Suas respostas foram mantidas; confira os casos alterados.") : null,
    h("div", { class: "layout" },
      h("aside", {}, h("div", { class: "card" },
        h("strong", {}, `${respondidos} de ${casos.length} respondidos`), barra, lateral,
        h("div", { class: "linha" }, h("button", { class: "sec", type: "button", onclick: () => { location.hash = `#/sessao/${id}/resumo`; } }, "Ver resumo")))),
      casoId === "resumo" ? resumo(d) : formularioCaso(d, atual, idx)),
  );
}

function formularioCaso(d, caso, idx) {
  const casos = d.roteiro.casos;
  const anterior = d.respostas[caso.id];
  let escolha = anterior?.resultado || null;
  const botoes = Object.entries(RESULTADOS).map(([k, rotulo]) => h("button", {
    type: "button", class: "escolha " + k, "data-r": k,
    onclick: () => { escolha = k; pintar(); },
  }, rotulo));
  const erro = h("textarea", { id: "erro", maxlength: 2000, placeholder: "Cole aqui a mensagem de erro ou descreva o que aconteceu" }, anterior?.mensagem_erro || "");
  const blocoErro = h("div", {}, h("label", { for: "erro" }, "Mensagem de erro (obrigatória quando falhou)"), erro);
  const comentario = h("textarea", { id: "comentario", maxlength: 2000, placeholder: "Opcional: o que achou, o que confundiu, sugestões" }, anterior?.comentario || "");
  const msg = h("p", { class: "erro" });
  const ultimo = idx >= casos.length - 1;
  const salvar = h("button", { type: "button" }, ultimo ? "Salvar e ver o resumo" : "Salvar e ir para o próximo");

  function pintar() {
    botoes.forEach((b) => b.classList.toggle("on", b.dataset.r === escolha));
    blocoErro.hidden = escolha !== "falhou";
  }
  salvar.addEventListener("click", async () => {
    msg.textContent = "";
    if (!escolha) { msg.textContent = "Escolha o resultado: Passou, Falhou ou Não consegui executar."; return; }
    if (escolha === "falhou" && !erro.value.trim()) { msg.textContent = "Descreva a mensagem de erro ou o que aconteceu."; erro.focus(); return; }
    salvar.disabled = true;
    try {
      await api("PUT", `/sessoes/${d.sessao.id}/respostas/${caso.id}`, { resultado: escolha, comentario: comentario.value, mensagem_erro: erro.value });
      location.hash = ultimo ? `#/sessao/${d.sessao.id}/resumo` : `#/sessao/${d.sessao.id}/${casos[idx + 1].id}`;
    } catch (e) {
      msg.textContent = e.message;
      salvar.disabled = false;
    }
  });
  const lista = (itens, tag, cls) => (itens && itens.length ? h(tag, { class: cls }, itens.map((i) => h("li", {}, i))) : null);
  const nav = h("div", { class: "linha" },
    idx > 0 ? h("a", { class: "botao sec", href: `#/sessao/${d.sessao.id}/${casos[idx - 1].id}` }, "← Voltar") : null, salvar);
  const bloco = h("div", { class: "card" },
    h("p", { class: "sub" }, `Caso ${idx + 1} de ${casos.length} · ${caso.id}`),
    h("h1", {}, caso.titulo),
    caso.objetivo ? h("p", {}, h("strong", {}, "Objetivo: "), caso.objetivo) : null,
    caso.preparacao ? h("p", {}, h("strong", {}, "Antes de começar: "), caso.preparacao) : null,
    h("h2", {}, "Passo a passo"), lista(caso.passos, "ol", "passos"),
    caso.esperado && caso.esperado.length ? [h("h2", {}, "O que deve acontecer"), lista(caso.esperado, "ul", "esperado")] : null,
    caso.anotar ? h("p", { class: "sub" }, h("strong", {}, "Anote: "), caso.anotar) : null,
    h("h2", {}, "Resultado"), h("div", { class: "escolhas" }, botoes), blocoErro,
    h("label", { for: "comentario" }, "Comentário"), comentario, msg, nav);
  pintar();
  return bloco;
}

function resumo(d) {
  const casos = d.roteiro.casos;
  const cont = { passou: 0, falhou: 0, nao_executou: 0 };
  Object.values(d.respostas).forEach((r) => { cont[r.resultado] += 1; });
  const faltam = casos.filter((c) => !d.respostas[c.id]);
  const problemas = casos.filter((c) => ["falhou", "nao_executou"].includes(d.respostas[c.id]?.resultado));
  const fim = d.sessao.finalizada_em;
  const link = (c) => h("a", { href: `#/sessao/${d.sessao.id}/${c.id}` }, `${c.id} · ${c.titulo}`);
  return h("div", { class: "card" },
    h("h1", {}, "Resumo"),
    h("div", { class: "numeros" },
      ...Object.entries(RESULTADOS).map(([k, r]) => h("div", { class: "numero" }, h("b", { class: "r-" + k }, cont[k]), r)),
      h("div", { class: "numero" }, h("b", {}, faltam.length), "Sem resposta")),
    fim ? h("div", { class: "ok" }, "Teste finalizado. Obrigado!") : null,
    h("p", { class: "sub" }, "Quando terminar, clique em \"Baixar meus resultados\" e envie o arquivo para quem conduz o teste (e-mail ou pasta combinada)."),
    problemas.length ? [h("h2", {}, "Para olhar com atenção"), h("table", {}, h("tbody", {}, problemas.map((c) => {
      const r = d.respostas[c.id];
      return h("tr", {}, h("td", {}, link(c)), h("td", {}, h("span", { class: "pill " + r.resultado }, RESULTADOS[r.resultado])), h("td", {}, r.mensagem_erro || r.comentario || ""));
    })))] : null,
    faltam.length ? [h("h2", {}, "Ainda sem resposta"), h("ul", {}, faltam.map((c) => h("li", {}, link(c))))] : null,
    h("div", { class: "linha" },
      fim ? null : h("button", { type: "button", onclick: async () => { await api("POST", `/sessoes/${d.sessao.id}/finalizar`); telaRota(); } }, "Finalizar teste"),
      h("button", { class: "sec", type: "button", onclick: () => baixarArquivo(`/api/sessoes/${d.sessao.id}/resultados.csv`, "meus-resultados.csv") }, "Baixar meus resultados"),
      h("a", { class: "botao sec", href: "#/" }, "Início")));
}

/* -------------------------------------------------------------- resultados */
async function telaResultados() {
  quem.textContent = "";
  const msg = h("p", { class: "erro" });
  const saida = h("div", {});
  async function carregar() {
    msg.textContent = "";
    try {
      saida.replaceChildren(tabelaResultados(await api("GET", "/resultados")));
    } catch (e) {
      msg.textContent = e.message;
      saida.replaceChildren();
    }
  }
  async function baixar() {
    const r = await fetch("/api/resultados.csv");
    if (!r.ok) { msg.textContent = (await r.json().catch(() => ({}))).detail || "Erro"; return; }
    const a = h("a", { href: URL.createObjectURL(await r.blob()), download: "resultados.csv" });
    document.body.append(a);
    a.click();
    a.remove();
  }
  montar(
    h("h1", {}, "Resultados"),
    h("p", { class: "sub" }, "Todas as respostas dadas até agora, de todos os testadores."),
    h("div", { class: "linha" }, h("button", { class: "sec", type: "button", onclick: carregar }, "Atualizar"), h("button", { type: "button", onclick: baixar }, "Baixar CSV")),
    msg,
    saida,
  );
  carregar();
}

function tabelaResultados(d) {
  if (!d.respostas.length) return h("div", { class: "card" }, "Ainda não há respostas.");
  const por = new Map(d.sessoes.map((s) => [s.id, s]));
  return h("div", { class: "card" }, h("table", {},
    h("thead", {}, h("tr", {}, ["Testador", "Roteiro", "Caso", "Resultado", "Erro", "Comentário"].map((t) => h("th", {}, t)))),
    h("tbody", {}, d.respostas.map((a) => {
      const s = por.get(a.sessao_id);
      return h("tr", {}, h("td", {}, s.testador), h("td", {}, `${s.roteiro} (${s.versao_roteiro})`), h("td", {}, `${a.caso_id} · ${a.caso_titulo}`),
        h("td", {}, h("span", { class: "pill " + a.resultado }, RESULTADOS[a.resultado])), h("td", {}, a.mensagem_erro || ""), h("td", {}, a.comentario || ""));
    }))));
}

/* ------------------------------------------------------------------ rotas */
function telaRota() {
  const p = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (p[0] === "sessao" && /^\d+$/.test(p[1] || "")) return telaSessao(Number(p[1]), p[2]);
  if (p[0] === "resultados") return telaResultados();
  return telaInicio();
}
window.addEventListener("hashchange", telaRota);
telaRota();
