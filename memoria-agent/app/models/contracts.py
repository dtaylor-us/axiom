from pydantic import BaseModel
from typing import Optional


class DistillRequest(BaseModel):
    session_id: str
    project_id: str
    pillar: str  # ARCHON | SPECWEAVER | LENS
    session_summary: Optional[str] = None
    existing_entries: list[dict] = []


class MemoryCandidate(BaseModel):
    memory_type: str
    content: str
    rationale: str
    confidence: str
    source_excerpt: Optional[str] = None
    tags: list[str] = []


class ConflictFlag(BaseModel):
    existing_entry_id: str
    new_candidate_index: int
    conflict_description: str


class DistillResponse(BaseModel):
    session_id: str
    candidates: list[MemoryCandidate] = []
    conflicts: list[ConflictFlag] = []
    message: str = ""
