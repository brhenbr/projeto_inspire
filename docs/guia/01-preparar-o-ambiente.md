# 1. Preparar o ambiente

**Em palavras simples:** o sistema roda dentro do **Docker**, um programa que cria "caixas" isoladas com tudo o que o
sistema precisa. Assim você não instala banco de dados, Python nem nada parecido: instala só o Docker e o Git, baixa o
projeto e pronto. Funciona igual em Windows, macOS e Linux.

## O que o seu computador precisa ter
| Item | Mínimo | Observação |
|---|---|---|
| Memória (RAM) | 8 GB no computador, **4 GB livres para o Docker** | Medido com 8 GB liberados ao Docker; abaixo de 4 GB pode travar |
| Espaço em disco | **6 GB livres** | Imagens ~1,6 GB, base de dados ~0,5 GB e cache de construção ~3 GB. Só se for rodar os testes automáticos do código: +4 GB |
| Internet | Sim, na primeira vez | Para baixar o projeto e as imagens do Docker (~1,5 GB) |
| Sistema | Windows 10/11, macOS ou Linux | No Windows, Docker Desktop com WSL 2 (o instalador sugere) |

## Passo 1: instalar o Docker
1. Baixe o **Docker Desktop** em <https://www.docker.com/products/docker-desktop/> e instale (aceite as opções padrão).
   No Linux, instale o Docker Engine e o plugin Compose.
2. **Abra o Docker Desktop** e espere o ícone ficar verde ("Engine running"). O Docker precisa estar aberto sempre que
   você for usar o sistema.
3. Confirme no terminal: `docker --version` e `docker compose version` devem mostrar versões, sem erro.

> **Windows:** em *Settings → Resources* do Docker Desktop, confira que há pelo menos 4 GB de memória liberados.

## Passo 2: instalar o Git (e um terminal com `bash`)
- **Windows:** instale o **Git for Windows** (<https://git-scm.com/download/win>). Ele traz o **Git Bash**, um terminal
  que os scripts do projeto usam. Abra o "Git Bash" pelo menu Iniciar para todos os comandos deste guia.
- **macOS:** `xcode-select --install` (ou instale o Git pelo Homebrew). O Terminal já serve.
- **Linux:** `sudo apt install git` (ou o gerenciador da sua distribuição).

## Passo 3: baixar o projeto
No terminal (Git Bash no Windows), escolha uma pasta e rode:
```
git clone https://github.com/brhenbr/projeto_inspire.git
cd projeto_inspire
```
Se o repositório for privado, o Git pedirá o seu login do GitHub (use o mesmo usuário que recebeu o convite). Se pedir
senha, use um *token* de acesso pessoal: GitHub → Settings → Developer settings → Personal access tokens.

## Passo 4: conferir
```
docker compose config --quiet && echo "tudo certo"
```
Se aparecer "tudo certo", o ambiente está pronto. Siga para [Rodar o sistema](02-rodar-o-sistema.md).

## Duas contas opcionais (você só precisa se quiser ir além)
| Para quê | O que criar | Preciso? |
|---|---|---|
| **Atualizar o catálogo** com dados novos do portal | Chave de API em <https://dados.gov.br> → *Minha Conta* | **Não**, se você usar o pacote de teste |
| **IA real** nas sugestões e no "Perguntar" | Chave gratuita em um provedor de LLM (Groq, Gemini, OpenRouter, Cerebras...) | **Não**: o modo simulado funciona sem chave |

Para usá-las, copie `.env.example` para `.env` e preencha só o que for usar. O `.env` **nunca** vai para o git.
