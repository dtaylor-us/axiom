CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,
    tier VARCHAR(20) NOT NULL DEFAULT 'EPISODIC',
    content TEXT NOT NULL,
    rationale TEXT,
    source_pillar VARCHAR(50),
    source_session_id UUID,
    source_excerpt TEXT,
    confidence VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    superseded_by UUID REFERENCES memory_entries(id),
    expires_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 0,
    tags TEXT[],
    embedding vector(1536),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_memory_project ON memory_entries(project_id);
CREATE INDEX idx_memory_status ON memory_entries(status);
CREATE INDEX idx_memory_expires ON memory_entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_memory_embedding ON memory_entries
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
