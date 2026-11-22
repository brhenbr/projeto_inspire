# Limites conhecidos e pontos a conversar

**Em palavras simples:** lista do que o sistema ainda **não** faz ou faz com ressalvas, para conversarmos com calma.
Cada item diz o que é, por que ficou assim e o que seria preciso para resolver. Atualizada em 2026-11-21.

## Entregas da sessão 04 (LLM, DCAT-BR, chat, coleção por texto)
1. **Pausa por cota só na memória.** O roteador de LLM guarda "este provedor está sem cota até X" na memória de cada
   processo (API e worker são separados). Efeito: após reiniciar, ou entre execuções, ele pode tentar de novo um provedor
   que ainda está sem cota (custa uma chamada). Solução: guardar a pausa no banco.
2. **O chat entende filtros, não perguntas analíticas.** "Dados de saúde em CSV" funciona; "qual órgão publica mais?" ou
   "resuma o que existe sobre educação" não. Foi escolha de segurança (o LLM não vê os dados; ADR-0016). Para ir além é
   preciso decidir quanto do catálogo pode ir ao provedor externo, ou usar um modelo local/soberano.
3. **Sem busca semântica (US-080).** A busca é por palavras (com acento, plural e erro de digitação). Achar por significado
   ("evasão escolar" ≈ "abandono") exige embeddings: API externa (envia textos do catálogo), modelo local em CPU
   (lento nesta máquina) ou GPU futura. Sugestão: avaliar primeiro se o chat basta para a demonstração.
4. **DCAT-BR incompleto de propósito.** Sem contato do responsável (dado pessoal, LGPD), sem os selos Bronze/Prata/Ouro do
   vocabulário (usamos a nossa nota) e sem validação formal (SHACL). Dá para calcular os selos e validar quando a fase 2
   (A5) começar. Catálogo inteiro: ~150 MB e ~45 s; o ideal é exportar por coleção ou filtro.

## Pendências já registradas antes
5. **Termos de uso dos provedores gratuitos** ainda não foram lidos por nós (US-067 parcial). Gratuito costuma significar
   que o provedor pode reter ou usar os textos enviados; hoje só vão textos públicos e o texto digitado no chat.
6. **Modelos de camada gratuita mudam** sem aviso (vimos nomes que deixaram de existir). Ficam configuráveis, mas alguém
   precisa conferir de vez em quando.
7. **Cobertura da extração: 97,8%** (560 conjuntos sem detalhe por erro 400 do portal). Por segurança o sistema só apaga
   conjuntos sumidos do portal acima de 99% de cobertura.
8. **Texto do portal com caracteres corrompidos** (�) já na origem; saem como estão. Poderíamos sinalizar na qualidade.
9. **Extração só manual**, sem agendamento automático; sem devolução de alterações ao portal (somente leitura).
10. **Verificação de links dos recursos** (fase 2) e detecção de duplicados: não feitas.
11. **Sem licença e sem publicação:** o repositório ainda não tem licença, push nem CI (decisão do cliente: depois dos testes).
12. **Estimativa de pesos da nota de qualidade** foi julgamento nosso, aprovada sem revisão detalhada; vale validar com os
    professores.
