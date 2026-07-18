from typing import Optional

from pydantic import BaseModel, Field


class DistillRequest(BaseModel):
    session_id: str
    project_id: str
    pillar: str  # ARCHON | SPECWEAVER | LENS
    session_summary: Optional[str] = None
    existing_entries: list[dict] = Field(default_factory=list)


class MemoryCandidate(BaseModel):
    memory_type: str
    content: str
    rationale: str
    confidence: str
    source_excerpt: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

class ConflictFlag(BaseModel):
    existing_entry_id: str
    new_candidate_index: int
    conflict_description: str


class DistillResponse(BaseModel):
    session_id: str
    candidates: list[MemoryCandidate] = Field(default_factory=list)
    conflicts: list[ConflictFlag] = Field(default_factory=list)
    message: str = ""
