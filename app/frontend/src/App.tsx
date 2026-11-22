import { useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";

import { api, getCurator, setCurator, type LlmEstado } from "./api";
import { useApi } from "./hooks";
import BuscaPage from "./pages/Busca";
import { ColecaoPage, ColecoesPage } from "./pages/Colecoes";
import ConfiguracoesPage from "./pages/Configuracoes";
import ConjuntoPage from "./pages/Conjunto";
import ExtracaoPage from "./pages/Extracao";
import FilaPage from "./pages/Fila";
import LlmPage from "./pages/Llm";
import { OrganizacaoPage, OrganizacoesPage } from "./pages/Organizacoes";
import PainelPage from "./pages/Painel";
import PerguntarPage from "./pages/Perguntar";

const MENU: [string, string][] = [
  ["/", "Painel"],
  ["/conjuntos", "Buscar"],
  ["/perguntar", "Perguntar"],
  ["/curadoria", "Fila de curadoria"],
  ["/colecoes", "Coleções"],
  ["/organizacoes", "Organizações"],
  ["/llm", "Sugestões de LLM"],
  ["/extracao", "Extração"],
  ["/configuracoes", "Configurações"],
];

export default function App() {
  const llm = useApi(() => api.get<LlmEstado>("/llm/estado"), []);
  const [curador, setNome] = useState(getCurator());
  const e = llm.data;

  return (
    <>
      <header className="topo">
        <div className="topo-interno">
          <Link className="marca" to="/">Inspire Catálogo</Link>
          <nav className="menu" aria-label="Principal">
            {MENU.map(([to, rotulo]) => (
              <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "ativo" : "")}>{rotulo}</NavLink>
            ))}
          </nav>
          <label className="curador">
            Curador(a)
            <input type="text" value={curador} placeholder="seu nome" aria-label="Seu nome (registrado nas alterações)" onChange={(ev) => { setNome(ev.target.value); setCurator(ev.target.value); }} />
          </label>
        </div>
      </header>
      {e?.habilitado && e.externo && (
        <div className="aviso aviso-externo" role="alert">
          <div className="aviso-interno"><strong>Provedor de LLM externo ativo</strong> ({e.host}): campos públicos dos conjuntos são enviados a ele ao pedir sugestões.</div>
        </div>
      )}
      {e?.habilitado && e.simulado && (
        <div className="aviso aviso-simulado" role="note">
          <div className="aviso-interno"><strong>Modo simulado:</strong> as sugestões de LLM são geradas por regras simples, sem IA e sem enviar dados a ninguém.</div>
        </div>
      )}
      <Routes>
        <Route path="/" element={<PainelPage />} />
        <Route path="/conjuntos" element={<BuscaPage />} />
        <Route path="/perguntar" element={<PerguntarPage />} />
        <Route path="/conjuntos/:id" element={<ConjuntoPage />} />
        <Route path="/curadoria" element={<FilaPage />} />
        <Route path="/colecoes" element={<ColecoesPage />} />
        <Route path="/colecoes/:id" element={<ColecaoPage />} />
        <Route path="/organizacoes" element={<OrganizacoesPage />} />
        <Route path="/organizacoes/:slug" element={<OrganizacaoPage />} />
        <Route path="/llm" element={<LlmPage />} />
        <Route path="/extracao" element={<ExtracaoPage />} />
        <Route path="/configuracoes" element={<ConfiguracoesPage />} />
        <Route path="*" element={<main className="pagina"><h1>Página não encontrada</h1><Link to="/">Ir para o painel</Link></main>} />
      </Routes>
    </>
  );
}
