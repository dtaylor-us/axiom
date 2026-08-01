CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE review_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    system_description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'EVIDENCE_COLLECTION',
    gap_round INTEGER NOT NULL DEFAULT 0,
    gaps_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
