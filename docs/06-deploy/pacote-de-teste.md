# Pacote de teste (base já carregada)

**Em palavras simples:** para os testadores não precisarem esperar a extração de ~90 minutos nem ter a chave do portal,
entregamos a base já extraída em um arquivo (~52 MB). Eles sobem o sistema em Docker, carregam o arquivo e já têm os
20 mil conjuntos para testar. Se quiserem dados novos, o botão de extração continua lá e só busca o que mudou.

## Para quem gera o pacote (nós)
```
bash scripts/pacote-de-teste.sh gerar
```
Cria `pacote/inspire-base-AAAAMMDD.dump` e o `.sha256` (a pasta `pacote/` não vai para o git). Envie os dois arquivos.

**O que vai:** catálogo espelhado, qualidade e pesos, histórico das extrações.
**O que não vai:** curadoria feita (edições, status, coleções, propostas de LLM), chaves de API e contatos de
responsáveis (já removidos na extração). Cada testador começa do zero na curadoria.
**Atenção:** as descrições dos conjuntos vêm como o portal publicou; algumas citam e-mails institucionais
(ouvidoria, diretoria). São textos públicos do portal, não o campo de contato do responsável.

## Para quem recebe (testador)
Pré-requisito: Docker Desktop aberto e o repositório baixado.
1. Copie os arquivos `.dump` e `.sha256` para a pasta `pacote/` do repositório.
2. Rode: `bash scripts/pacote-de-teste.sh carregar pacote/inspire-base-AAAAMMDD.dump`
3. Abra http://127.0.0.1:8080. O LLM vem em **modo simulado** (sem IA, sem rede). Para usar um LLM real, crie o seu
   próprio `.env` com as suas chaves (ver `.env.example`); as chaves de ninguém viajam no pacote.
4. Abra a ferramenta de testes (`kit/roteiro-de-testes`) e siga o roteiro.

O script confere a integridade (sha256), substitui a base da máquina e reinicia o sistema. Verificado em 2026-11-22: a
base restaurada tem os mesmos 20.218 conjuntos e 126.741 recursos, a curadoria vazia e a busca em português funcionando.
