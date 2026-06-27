FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app/
COPY app /app/app

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir uvicorn fastapi pydantic httpx python-dotenv langgraph jinja2 structlog opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc opentelemetry-exporter-prometheus opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx prometheus-client

EXPOSE 8086

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8086"]
