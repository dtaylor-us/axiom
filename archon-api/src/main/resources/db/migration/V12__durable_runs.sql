-- Durable pipeline run lifecycle: run records + append-only event log.

CREATE TYPE pipeline_run_status AS ENUM (
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'COMPLETED_WITH_GAPS'
);

CREATE TABLE pipeline_runs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id       UUID NOT NULL
                              REFERENCES conversations(id)
                              ON DELETE CASCADE,
    iteration             INTEGER NOT NULL DEFAULT 0,
    status                pipeline_run_status NOT NULL
                              DEFAULT 'RUNNING',
    started_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at          TIMESTAMPTZ,
    last_stage_completed  TEXT,
    governance_score      INTEGER,
    governance_confidence TEXT,
    has_gaps              BOOLEAN NOT NULL DEFAULT FALSE,
    gap_summary           TEXT,
    error_stage           TEXT,
    error_message         TEXT,
    total_tokens          INTEGER,
    estimated_cost_usd    NUMERIC(10, 4)
);

CREATE INDEX idx_runs_conversation ON pipeline_runs(conversation_id);
CREATE INDEX idx_runs_status       ON pipeline_runs(status);

CREATE TABLE pipeline_events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       UUID NOT NULL
                     REFERENCES pipeline_runs(id)
                     ON DELETE CASCADE,
    sequence_num INTEGER NOT NULL,
    event_type   TEXT NOT NULL,
    stage_name   TEXT,
    payload      JSONB,
    emitted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_run_id       ON pipeline_events(run_id);
CREATE INDEX idx_events_run_sequence ON pipeline_events(run_id, sequence_num);

COMMENT ON TABLE pipeline_runs IS
    'One record per pipeline execution. Status persists independently of the SSE stream — stream loss does not change run status.';

COMMENT ON TABLE pipeline_events IS
    'Append-only log of all SSE events for a run. Used to replay events to a reconnecting client.';

