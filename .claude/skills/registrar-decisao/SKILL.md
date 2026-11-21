---
name: registrar-decisao
description: Registra uma decisão de arquitetura ou produto como ADR numerado em docs/03-decisoes a partir do template do kit. Use quando uma decisão relevante for tomada ou alterada.
---

1. Liste `docs/03-decisoes/` e descubra o próximo número (NNNN, 4 dígitos).
2. Copie `kit/templates/adr.md` para `docs/03-decisoes/NNNN-slug-curto.md`.
3. Preencha contexto, opções com prós e contras, decisão e consequências, em português.
4. Se a decisão substitui outra, marque a antiga como "substituída por ADR-NNNN".
5. Cite o ADR na entrada do diário da sessão em `docs/diario/`.
