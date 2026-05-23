import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.api.agent import router as agent_router
from app.llm.client import LLMClient
from app.memory.store import MemoryStore
from app.observability import setup_tracing, setup_metrics
from app.pipeline import compile_pipeline, init_registry, init_review_agent
from app.review.agent import ArchitectReviewAgent
from app.tools.registry import build_registry

# Configure structlog for JSON output with trace context injection
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
    logger.info("Archon Agent starting up")

    # Observability must initialise first — before any other component
    setup_tracing()
    setup_metrics()

    # Instrument FastAPI and httpx automatically
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    # Initialise shared LLM client
    llm_client = LLMClient()
    app.state.llm_client = llm_client
    logger.info("LLMClient attached to app.state")

    # Initialise Qdrant-backed memory store
    memory_store = MemoryStore()
    await memory_store._ensure_collection()
    app.state.memory_store = memory_store
    logger.info("MemoryStore attached to app.state")

    # Build tool registry and wire it into pipeline nodes
    registry = build_registry(llm_client, memory_store)
    app.state.tool_registry = registry
    init_registry(registry)
    logger.info("Tool registry initialised with %d tools", len(registry))

    # Build and wire the architect review agent
    review_agent = ArchitectReviewAgent(llm_client)
    app.state.review_agent = review_agent
    init_review_agent(review_agent)
    logger.info("ArchitectReviewAgent initialised")

    # Compile the LangGraph pipeline graph
    compile_pipeline()

    yield
    logger.info("Archon Agent shutting down")


app = FastAPI(
    title="Archon Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(agent_router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "UP",
                         "service": "archon-agent"})


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Expose OTel metrics in Prometheus text format.

    Prometheus scrapes this endpoint at its configured interval.
    The PrometheusMetricReader registered in setup_metrics() populates
    the prometheus_client default registry that generate_latest() reads.
    """
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
