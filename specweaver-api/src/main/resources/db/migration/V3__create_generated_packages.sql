CREATE TABLE generated_packages (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id            UUID NOT NULL
                          REFERENCES sessions(id) ON DELETE CASCADE,
    package_json          JSONB NOT NULL,
    total_requirements    INT   NOT NULL DEFAULT 0,
    high_confidence_count INT   NOT NULL DEFAULT 0,
    inferred_count        INT   NOT NULL DEFAULT 0,
    readiness_score       DECIMAL(3,2) NOT NULL DEFAULT 0.00,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    sent_to_archon_at     TIMESTAMPTZ,
    archon_conversation_id UUID
);

CREATE INDEX idx_packages_session_id
    ON generated_packages(session_id);
