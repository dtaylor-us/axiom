"""FastAPI application entrypoint for specweaver-agent."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.agent import router as agent_router
from app.api.health import router as health_router
from app.llm.client import LLMClient
from app.observability import configure_telemetry

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise telemetry and the shared LLM client."""
    logger.info("SpecWeaver Agent starting up")
    configure_telemetry()

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    llm_client = LLMClient()
    await llm_client.check_connectivity()
    app.state.llm_client = llm_client
    logger.info("LLMClient attached to app.state")

    yield
    logger.info("SpecWeaver Agent shutting down")


app = FastAPI(
    title="SpecWeaver Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(agent_router)
app.include_router(health_router)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Expose metrics in Prometheus text format."""
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
