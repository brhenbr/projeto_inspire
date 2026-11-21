# Backlog

- `backlog.json` — **fonte da verdade**. Edite aqui.
- `backlog.md` e `backlog-jira.csv` — gerados. Para regenerar, na raiz do repositório:

```
python -I kit/scripts/backlog_to_jira.py docs/01-produto/backlog/backlog.json docs/01-produto/backlog
```

## Importar no Jira (Cloud)
1. Projeto → **Configurações do espaço → Importar** (ou *Jira settings → System → External system import → CSV*).
2. Selecione `backlog-jira.csv`, delimitador vírgula, UTF-8.
3. Mapeie os campos: `Issue Id` → Issue Id, `Issue Type`, `Summary`, `Description`, `Priority`, `Labels`
   (as três colunas), `Epic Name` → Epic Name e **`Parent` → Parent** (liga cada história ao épico).
4. Importe primeiro uma cópia pequena em um projeto de teste para conferir o mapeamento.

**Aviso:** a importação não foi testada em um Jira real. Os nomes de campos mudam entre projetos
"company-managed" e "team-managed"; se `Parent` não ligar aos épicos, use `Epic Link` no lugar.
