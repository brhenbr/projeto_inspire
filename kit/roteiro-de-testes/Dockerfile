FROM python:3.12-slim
# Sem dependências de terceiros: só a biblioteca padrão do Python.
RUN useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin roteiro \
 && mkdir -p /data && chown roteiro /data
WORKDIR /srv
COPY app/ /srv/app/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DB_PATH=/data/roteiro.db CASOS_DIR=/casos
USER roteiro
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=4s --retries=3 CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/roteiros', timeout=3)"
CMD ["python", "/srv/app/server.py"]
