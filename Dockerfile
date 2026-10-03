FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY source/ ./source/
COPY templates/ ./source/templates/
COPY static/ ./source/static/

ENV DB_PATH=/data/status.db \
    PORT=5004 \
    ADMIN_TOKEN=change-me \
    SECRET_KEY=dev-secret-change-me

EXPOSE 5004

VOLUME ["/data"]

CMD ["gunicorn", "--bind", "0.0.0.0:5004", "--workers", "2", "--threads", "4", "source.app:app"]