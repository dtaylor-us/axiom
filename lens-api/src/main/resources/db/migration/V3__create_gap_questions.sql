CREATE TABLE gap_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES review_sessions(id) ON DELETE CASCADE,
    round INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    rationale TEXT,
    answered BOOLEAN NOT NULL DEFAULT FALSE,
    skipped BOOLEAN NOT NULL DEFAULT FALSE,
    answer TEXT,
    asked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    answered_at TIMESTAMP
);
