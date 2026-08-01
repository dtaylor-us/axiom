CREATE TABLE architecture_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES review_sessions(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    source_label VARCHAR(255),
    submitted_at TIMESTAMP NOT NULL DEFAULT NOW()
);
