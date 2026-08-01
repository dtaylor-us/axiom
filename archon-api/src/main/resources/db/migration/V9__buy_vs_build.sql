-- Buy-vs-build decisions persisted from stage 6b buy_vs_build_analysis.
-- Stores per-component sourcing recommendations (build | buy | adopt)
-- plus user preference conflict metadata.

CREATE TABLE buy_vs_build_decisions (
    id                          UUID PRIMARY KEY
                                    DEFAULT gen_random_uuid(),
    conversation_id             UUID NOT NULL
                                    REFERENCES conversations(id)
                                    ON DELETE CASCADE,
    component_name              TEXT NOT NULL,
    recommendation              TEXT NOT NULL,
    rationale                   TEXT NOT NULL,
    alternatives_considered     JSONB,
    recommended_solution        TEXT,
    estimated_build_cost        TEXT,
    vendor_lock_in_risk         TEXT NOT NULL,
    integration_effort          TEXT NOT NULL,
    conflicts_with_user_preference BOOLEAN NOT NULL DEFAULT FALSE,
    conflict_explanation        TEXT,
    is_core_differentiator      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bvb_conversation
    ON buy_vs_build_decisions(conversation_id);
CREATE INDEX idx_bvb_recommendation
    ON buy_vs_build_decisions(recommendation);
CREATE INDEX idx_bvb_conflict
    ON buy_vs_build_decisions(conflicts_with_user_preference);

ALTER TABLE architecture_outputs
    ADD COLUMN IF NOT EXISTS override_applied  BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS override_warning  TEXT;

