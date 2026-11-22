"""Procura segredos no histórico inteiro do git e arquivos que nunca deveriam ser versionados.

Uso: python scripts/varrer_segredos.py       (sai com código 1 se achar algo)
Sem dependências além da biblioteca padrão e do `git`. Não imprime o valor do segredo: só onde está e o tipo.
"""

import re
import subprocess
import sys

PADROES = {
    "chave Groq": r"gsk_[A-Za-z0-9]{20,}",
    "chave Google/Gemini": r"AIza[0-9A-Za-z_\-]{30,}",
    "chave estilo OpenAI/OpenRouter": r"sk-[A-Za-z0-9_\-]{20,}",
    "token GitHub": r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}",
    "chave AWS": r"AKIA[0-9A-Z]{16}",
    "JWT": r"eyJ[A-Za-z0-9_\-]{15,}\.eyJ[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{10,}",
    "chave privada": r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "atribuição de segredo": r"""(?i)\b[A-Z_]*(API_KEY|SECRET|PASSWORD|TOKEN)\b\s*[:=]\s*["']?[A-Za-z0-9+/_\-]{28,}["']?""",
}
ARQUIVOS_PROIBIDOS = re.compile(r"(^|/)\.env$|/restrito/|\.pem$|\.p12$|id_rsa|\.dump$|\.sqlite3?$")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout


def main() -> int:
    problemas: list[str] = []
    for caminho in git("ls-files").splitlines():
        if ARQUIVOS_PROIBIDOS.search(caminho):
            problemas.append(f"arquivo que não deveria ser versionado: {caminho}")
    historico = git("log", "--all", "-p", "--no-color", "--format=commit %h")
    commit, arquivo = "?", "?"
    regexes = {nome: re.compile(p) for nome, p in PADROES.items()}
    for linha in historico.splitlines():
        if linha.startswith("commit "):
            commit = linha.split()[1]
        elif linha.startswith("+++ b/"):
            arquivo = linha[6:]
        elif linha.startswith("+") and not linha.startswith("+++"):
            for nome, rx in regexes.items():
                if rx.search(linha):
                    problemas.append(f"{nome} no commit {commit}, arquivo {arquivo}")
    problemas = sorted(set(problemas))
    if problemas:
        print("POSSÍVEIS SEGREDOS ENCONTRADOS:")
        for p in problemas:
            print(" -", p)
        print("Revogue a chave no provedor (remover do git não basta) e limpe o histórico.")
        return 1
    print("Nenhum segredo encontrado no histórico nem arquivos proibidos versionados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
