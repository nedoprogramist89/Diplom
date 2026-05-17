# CompetitionHub — образ для продакшена (Gunicorn + Django)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Зависимости ОС: PostgreSQL-клиент, Pillow (JPEG/PNG)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --create-home --shell /bin/bash appuser

COPY --chown=appuser:appgroup . .

RUN mkdir -p /app/media /app/staticfiles \
    && chown -R appuser:appgroup /app/media /app/staticfiles

COPY --chown=appuser:appgroup docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
