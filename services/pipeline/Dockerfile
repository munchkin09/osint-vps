FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cto_pipeline ./cto_pipeline

RUN useradd --create-home --shell /usr/sbin/nologin cto
USER cto

CMD ["python", "-m", "cto_pipeline.workers.enrichment"]
