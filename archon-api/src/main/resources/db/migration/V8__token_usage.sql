-- Token usage tracking for LLM cost observability (Phase 6)

CREATE TABLE token_usage (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL
                        REFERENCES conversations(id) ON DELETE CASCADE,
    stage           TEXT NOT NULL,
    model           TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    total_tokens    INTEGER NOT NULL DEFAULT 0,
    estimated_cost  NUMERIC(12, 6) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_token_usage_conversation_id ON token_usage(conversation_id);
CREATE INDEX idx_token_usage_created_at      ON token_usage(created_at);
