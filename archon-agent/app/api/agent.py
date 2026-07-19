import logging
import os
from typing import AsyncGenerator

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.models import ArchitectureContext, PipelineMode, HistoryMessage
from app.pipeline import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentStreamRequest(BaseModel):
    conversationId: str
    userMessage: str
    mode: str = "AUTO"
    history: list[dict] = []
    context: dict | None = None
    previousArchitecture: dict | None = None
    iterativeMode: bool = False


class AgentResponseChunk(BaseModel):
    type: str
    content: str | None = None
    stage: str | None = None
    toolName: str | None = None
    payload: dict | None = None
    conversationId: str | None = None
    metadata: dict | None = None


def chunk(event_type: str, **kwargs) -> str:
    data = AgentResponseChunk(type=event_type, **kwargs)
    return data.model_dump_json(exclude_none=True) + "\n"


def _stage_payload(stage: str, **extra: object) -> dict:
    """Build a standardised payload dict for STAGE_COMPLETE events."""
    return {"status": "complete", "stage": stage, **extra}


def _seed_context_from_previous(ctx: ArchitectureContext) -> None:
    """Seed supporting-stage artifacts without seeding regenerated design fields."""
    if not (ctx.previous_architecture and ctx.iterative_mode):
        return
    previous = ctx.previous_architecture
    for source, target in (
        ("characteristics", "characteristics"),
        ("trade_offs", "trade_offs"),
        ("fmea_risks", "fmea_risks"),
        ("weaknesses", "weaknesses"),
    ):
        if previous.get(source):
            setattr(ctx, target, previous[source])


@router.post("/agent/stream")
async def agent_stream(
    request: AgentStreamRequest,
    raw_request: Request,
    x_internal_secret: str = Header(
        default=None, alias="x-internal-secret"),
):
    expected = os.getenv("INTERNAL_SECRET", "dev-secret-change-in-prod")
    if x_internal_secret != expected:
        raise HTTPException(status_code=401,
                            detail="Invalid internal secret")

    logger.info("Agent stream request conversation=%s mode=%s",
                request.conversationId, request.mode)

    ctx = ArchitectureContext(
        conversation_id=request.conversationId,
        raw_requirements=request.userMessage,
        project_memory_context=(request.context or {}).get("project_memory_context"),
        mode=(PipelineMode(request.mode)
              if request.mode in PipelineMode.__members__
              else PipelineMode.AUTO),
        history=[
            HistoryMessage(
                id=str(i),
                role=h.get("role", "USER"),
                content=h.get("content", ""),
            )
            for i, h in enumerate(request.history)
        ],
        previous_architecture=request.previousArchitecture,
        iterative_mode=request.iterativeMode,
    )

    _seed_context_from_previous(ctx)

    memory_store = getattr(raw_request.app.state, "memory_store", None)

    return StreamingResponse(
        run_pipeline(ctx, memory_store=memory_store),
        media_type="application/x-ndjson",
        headers={"X-Conversation-Id": ctx.conversation_id},
    )
