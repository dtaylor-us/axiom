FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
RUN uv pip install --system --no-cache -e .
COPY app ./app
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", \
     "--port", "8001", "--workers", "2", "--log-level", "info"]
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s \
  CMD python -c \
  "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"
