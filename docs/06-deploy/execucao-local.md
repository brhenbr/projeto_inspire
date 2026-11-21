# Execução local

1. Abra o Docker Desktop.
2. Na raiz do repositório, copie `.env.example` para `.env` e preencha `DADOS_GOV_API_KEY`.
3. `docker compose up --build` e abra http://127.0.0.1:8080.
4. Documentação da API: http://127.0.0.1:8080/api/docs
5. Parar: `docker compose down`. Apagar também os dados do banco: `docker compose down -v`.

Para publicar em nuvem no futuro, as mesmas imagens servem; será preciso definir segredos, volume do banco
e a entrada web em ADR próprio.
