CREATE TABLE architecture_outputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL
                        REFERENCES conversations(id) ON DELETE CASCADE,
    style           TEXT,
    domain          TEXT,
    system_type     TEXT,
    component_count INTEGER NOT NULL DEFAULT 0,
    components      JSONB,
    interactions    JSONB,
    characteristics JSONB,
    conflicts       JSONB,
    component_diagram TEXT,
    sequence_diagram  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_arch_outputs_conversation_id ON architecture_outputs(conversation_id);
CREATE INDEX idx_arch_outputs_created_at      ON architecture_outputs(created_at DESC);
