"""
FastAPI workshop endpoints.

These endpoints are called by Spring Boot, not by the UI directly.
The pattern mirrors app/api/agent.py but returns JSON responses
rather than SSE streams, because the workshop is conversational
not a long-running pipeline.

Each turn is fast enough for a synchronous request-response.
No SSE is needed. Spring Boot calls this and returns the response
to the UI in a standard REST response.

Spring Boot owns all persistence. The Python agent is stateless —
it receives the full WorkshopContext on each request, processes one
turn, and returns the updated context for Spring Boot to persist.
"""

import logging
import os

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.workshop.agent import QualityAttributeWorkshopAgent
from app.workshop.context import WorkshopContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workshop", tags=["workshop"])

# The expected internal secret value — must match the header Spring Boot sends.
# Validated on every request; absent headers return HTTP 401.
_INTERNAL_SECRET_ENV = "INTERNAL_SECRET"
_INTERNAL_SECRET_DEFAULT = "dev-secret-change-in-prod"


def _verify_internal_secret(provided: str | None) -> None:
    """
    Verify the X-Internal-Secret header against the configured secret.

    Args:
        provided: Value of the x-internal-secret header.

    Raises:
        HTTPException: HTTP 401 when the secret is absent or incorrect.
    """
    expected = os.getenv(_INTERNAL_SECRET_ENV, _INTERNAL_SECRET_DEFAULT)
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid internal secret")


def _get_workshop_agent(request: Request) -> QualityAttributeWorkshopAgent:
    """
    Resolve the workshop agent from app.state.

    The agent is initialised once during startup and attached to
    app.state.workshop_agent by the lifespan handler in main.py.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The QualityAttributeWorkshopAgent instance.

    Raises:
        RuntimeError: If the agent was not initialised at startup.
    """
    agent = getattr(request.app.state, "workshop_agent", None)
    if agent is None:
        raise RuntimeError(
            "workshop_agent not found in app.state. "
            "Ensure it is initialised in the lifespan handler."
        )
    return agent


class WorkshopTurnRequest(BaseModel):
    """
    Request body for /workshop/turn.

    Spring Boot serialises the current WorkshopContext to JSON and
    sends it alongside the user's latest input. The Python agent
    processes one turn and returns the updated context.
    """
    session_id: str
    user_input: str
    context_json: str
    # WorkshopContext serialised to JSON by Spring Boot.
    # Spring Boot owns persistence — agent receives state,
    # processes it, and returns the updated state.


class WorkshopTurnResponse(BaseModel):
    """
    Response body from /workshop/turn.

    Returns the updated context (for Spring Boot to persist) and the
    structured turn response (for the UI to render).
    """
    updated_context_json: str
    # Updated WorkshopContext serialised to JSON.
    # Spring Boot persists this after receiving it.
    turn_response: dict
    # Structured response for the UI.


class WorkshopSummaryRequest(BaseModel):
    """Request body for /workshop/summary."""
    session_id: str
    context_json: str
    # WorkshopContext serialised to JSON by Spring Boot.


class GenerateFromEvidenceRequest(BaseModel):
    """Request for readiness assessment and on-demand generation."""
    session_id: str
    context_json: str


class GenerationReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overall_readiness: str
    confidence_note: str
    attribute_preview: list[dict]
    high_value_gaps: list[dict]
    missing_domains: list[str]
    can_produce_useful_output: bool


class GenerateFromEvidenceResponse(BaseModel):
    """Response from /workshop/generate."""
    updated_context_json: str
    generation_response: dict


@router.post("/turn")
async def process_turn(
    request: WorkshopTurnRequest,
    raw_request: Request,
    x_internal_secret: str | None = Header(
        default=None, alias="x-internal-secret"
    ),
) -> WorkshopTurnResponse:
    """
    Process one workshop conversation turn.

    Spring Boot calls this with the current context and the user's
    latest input. Returns the updated context and the structured
    response for the UI.

    Spring Boot must persist the updated_context_json before
    responding to the user — the Python agent does not persist
    anything directly.

    Args:
        request:     WorkshopTurnRequest containing session_id,
                     user_input, and serialised context.
        raw_request: FastAPI Request for accessing app.state.
        x_internal_secret: Authentication header.

    Returns:
        WorkshopTurnResponse with updated_context_json and turn_response.

    Raises:
        HTTPException 401: Invalid or absent internal secret.
        HTTPException 400: Malformed context JSON.
        HTTPException 500: Unhandled agent exception.
    """
    _verify_internal_secret(x_internal_secret)

    try:
        context = WorkshopContext.model_validate_json(request.context_json)
    except Exception as exc:
        logger.error(
            "Invalid context JSON for session=%s: %s",
            request.session_id,
            exc,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid context JSON: {exc}",
        ) from exc

    agent = _get_workshop_agent(raw_request)

    try:
        updated_context, turn_response = await agent.process_turn(
            context=context,
            user_input=request.user_input,
        )
    except Exception as exc:
        logger.error(
            "Workshop agent error. session=%s turn=%d: %s",
            request.session_id,
            context.current_turn,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Workshop agent processing failed. See agent logs.",
        ) from exc

    return WorkshopTurnResponse(
        updated_context_json=updated_context.model_dump_json(),
        turn_response=turn_response,
    )


@router.post("/summary")
async def produce_summary(
    request: WorkshopSummaryRequest,
    raw_request: Request,
    x_internal_secret: str | None = Header(
        default=None, alias="x-internal-secret"
    ),
) -> dict:
    """
    Produce the final QA summary for a completed workshop.

    The summary is structured for input into the main architecture
    pipeline. It lists all confirmed and inferred attributes with
    their scenarios, distinguishes confidence levels, and provides
    a pipeline-readiness assessment.

    Args:
        request:     WorkshopSummaryRequest with serialised context.
        raw_request: FastAPI Request for accessing app.state.
        x_internal_secret: Authentication header.

    Returns:
        Dict matching the produce_summary JSON schema.

    Raises:
        HTTPException 401: Invalid or absent internal secret.
        HTTPException 400: Malformed context JSON.
        HTTPException 500: Unhandled agent exception.
    """
    _verify_internal_secret(x_internal_secret)

    try:
        context = WorkshopContext.model_validate_json(request.context_json)
    except Exception as exc:
        logger.error(
            "Invalid context JSON for summary. session=%s: %s",
            request.session_id,
            exc,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid context JSON: {exc}",
        ) from exc

    agent = _get_workshop_agent(raw_request)

    try:
        summary = await agent.produce_summary(context)
    except Exception as exc:
        logger.error(
            "Workshop summary generation failed. session=%s: %s",
            request.session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Workshop summary generation failed. See agent logs.",
        ) from exc

    return summary


@router.post("/assess-readiness")
async def assess_readiness(
    request_body: GenerateFromEvidenceRequest,
    raw_request: Request,
    x_internal_secret: str | None = Header(
        default=None, alias="x-internal-secret"
    ),
) -> GenerationReadinessResponse:
    """
    Returns an honest assessment of what can be generated
    from current evidence. Called when the user is considering
    whether to generate now or continue with discovery.
    Does not modify context or session state.
    """
    _verify_internal_secret(x_internal_secret)

    try:
        context = WorkshopContext.model_validate_json(request_body.context_json)
    except Exception as exc:
        logger.error(
            "Invalid context JSON for assess-readiness session=%s: %s",
            request_body.session_id,
            exc,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid context JSON: {exc}",
        ) from exc

    agent = _get_workshop_agent(raw_request)

    try:
        assessment = await agent.assess_generation_readiness(context)
    except Exception as exc:
        logger.error(
            "Workshop assess-readiness failed. session=%s: %s",
            request_body.session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Workshop readiness assessment failed. See agent logs.",
        ) from exc

    return GenerationReadinessResponse.model_validate(assessment)


@router.post("/generate")
async def generate_attributes(
    request_body: GenerateFromEvidenceRequest,
    raw_request: Request,
    x_internal_secret: str | None = Header(
        default=None, alias="x-internal-secret"
    ),
) -> GenerateFromEvidenceResponse:
    """
    Generates quality attributes from current evidence.
    Always executes — never refuses based on gap state.
    The session remains open for continued refinement.
    """
    _verify_internal_secret(x_internal_secret)

    try:
        context = WorkshopContext.model_validate_json(request_body.context_json)
    except Exception as exc:
        logger.error(
            "Invalid context JSON for generate session=%s: %s",
            request_body.session_id,
            exc,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid context JSON: {exc}",
        ) from exc

    if not context.can_generate:
        raise HTTPException(
            status_code=400,
            detail="No input provided yet. Submit at least "
                   "one turn of context before generating.",
        )

    agent = _get_workshop_agent(raw_request)

    try:
        updated_context, generation_response = (
            await agent.generate_from_current_evidence(context)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "Workshop generate failed. session=%s: %s",
            request_body.session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Workshop generation failed. See agent logs.",
        ) from exc

    return GenerateFromEvidenceResponse(
        updated_context_json=updated_context.model_dump_json(),
        generation_response=generation_response,
    )
