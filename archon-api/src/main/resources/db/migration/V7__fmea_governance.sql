-- FMEA risks and governance reports for Phase 5 governance pipeline

CREATE TABLE fmea_risks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL
                        REFERENCES conversations(id) ON DELETE CASCADE,
    risk_id         TEXT NOT NULL,
    failure_mode    TEXT NOT NULL,
    component       TEXT NOT NULL,
    cause           TEXT,
    effect          TEXT,
    severity        INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 10),
    occurrence      INTEGER NOT NULL CHECK (occurrence BETWEEN 1 AND 10),
    detection       INTEGER NOT NULL CHECK (detection BETWEEN 1 AND 10),
    rpn             INTEGER NOT NULL,
    current_controls    TEXT,
    recommended_action  TEXT,
    linked_weakness     TEXT,
    linked_characteristic TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fmea_risks_conversation_id ON fmea_risks(conversation_id);
CREATE INDEX idx_fmea_risks_rpn             ON fmea_risks(rpn DESC);

CREATE TABLE governance_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL
                        REFERENCES conversations(id) ON DELETE CASCADE,
    iteration       INTEGER NOT NULL DEFAULT 0,
    governance_score INTEGER NOT NULL,
    requirement_coverage    INTEGER NOT NULL DEFAULT 0,
    architectural_soundness INTEGER NOT NULL DEFAULT 0,
    risk_mitigation         INTEGER NOT NULL DEFAULT 0,
    governance_completeness INTEGER NOT NULL DEFAULT 0,
    justification           TEXT,
    should_reiterate        BOOLEAN NOT NULL DEFAULT FALSE,
    review_findings         JSONB,
    improvement_recommendations JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_governance_reports_conversation_id ON governance_reports(conversation_id);
CREATE INDEX idx_governance_reports_created_at      ON governance_reports(created_at DESC);
