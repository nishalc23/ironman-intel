FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/api/requirements.txt /tmp/api-requirements.txt
COPY services/ingestion/requirements.txt /tmp/ingestion-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/api-requirements.txt \
    -r /tmp/ingestion-requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
