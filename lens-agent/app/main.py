"""FastAPI application entrypoint for lens-agent."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router as lens_router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_telemetry()
    yield


app = FastAPI(title="Lens Agent", version="0.1.0", lifespan=lifespan)
app.include_router(lens_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "lens-agent"}


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
