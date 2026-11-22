# Avaliação dos LLMs gratuitos em português (US-044)

**Em palavras simples:** testei os quatro provedores gratuitos que o roteador usa, pedindo as três tarefas de curadoria
(melhorar descrição, sugerir palavras-chave, sugerir tema) para três conjuntos reais. Medi se a resposta veio no formato
certo e quanto demorou. **É uma amostra pequena** (36 chamadas); serve para escolher a ordem de preferência, não para
declarar qual modelo é "o melhor".

Data: 2026-11-22. Conjuntos: "Convênios", "Censo Escolar 2015" e "Educação".

| Provedor | Modelo | Descrição | Palavras-chave | Tema | Tempo médio por chamada |
|---|---|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | 3/3 | 3/3 | 3/3 | 0,6 a 1,0 s |
| Cerebras | `gpt-oss-120b` | 3/3 | 2/3 | **1/3** | 0,3 a 0,5 s |
| Gemini | `gemini-3.5-flash` | 3/3 | 3/3 | 3/3 | 3 a 12 s |
| OpenRouter | `nvidia/nemotron-3-ultra-550b-a55b:free` | 3/3 | 3/3 | 3/3 | 4 a 10 s |

*"3/3" = a resposta veio num formato aceito pela validação do sistema.*

## O que dá para concluir
1. **Todos escrevem bom português** nas descrições; a diferença está na confiabilidade do formato e na velocidade.
2. **Groq** foi o mais rápido e acertou o formato sempre. É um bom primeiro da lista (já é).
3. **Cerebras** falhou o formato em parte das tarefas curtas (palavras-chave e tema). Fica como reserva: a validação do
   sistema descarta a resposta inválida e o roteador não depende dele.
4. **Gemini e OpenRouter** são mais lentos, mas confiáveis; bons como reserva quando a cota do primeiro acaba.
5. **Risco comum: "inventar" detalhes.** Em descrições de conjuntos com pouca informação, alguns modelos acrescentaram
   coisas plausíveis que não estavam nos metadados (por exemplo, "escolas públicas e privadas", "matrículas e
   professores"). Por isso **toda sugestão passa pela aprovação humana** e o prompt manda não inventar fatos.

## Limites desta avaliação
Poucos conjuntos, uma única rodada, sem nota de qualidade do texto por especialistas. Os modelos gratuitos mudam sem
aviso (já vimos nomes deixarem de existir). Reavaliar quando o catálogo ou os provedores mudarem.
