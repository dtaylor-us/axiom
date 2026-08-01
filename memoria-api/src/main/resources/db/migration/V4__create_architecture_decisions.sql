CREATE TABLE architecture_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    adr_number INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PROPOSED',
    context TEXT NOT NULL,
    decision TEXT NOT NULL,
    consequences TEXT,
    alternatives_considered TEXT,
    source_pillar VARCHAR(50),
    source_session_id UUID,
    superseded_by_adr_number INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, adr_number)
);
CREATE INDEX idx_adrs_project ON architecture_decisions(project_id);
