-- V13__workshop.sql
--
-- Quality Attribute Workshop persistence.
-- Creates two tables:
--   workshop_sessions   — one record per conversation session
--   workshop_attributes — denormalised attribute records for query access
--
-- The authoritative session state lives in workshop_sessions.context_json
-- (a JSONB column holding the full WorkshopContext). The workshop_attributes
-- table mirrors the attribute list from context_json so attributes can be
-- queried and filtered without parsing JSON in application code.

CREATE TABLE workshop_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT NOT NULL,
    system_name     TEXT,
    workshop_phase  TEXT NOT NULL DEFAULT 'input_analysis',
    context_json    JSONB NOT NULL DEFAULT '{}',
    is_complete     BOOLEAN NOT NULL DEFAULT FALSE,
    turn_count      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workshop_attributes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL
                        REFERENCES workshop_sessions(id)
                        ON DELETE CASCADE,
    attribute_id    TEXT NOT NULL,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    importance      TEXT NOT NULL,
    confidence      TEXT NOT NULL,
    description     TEXT,
    scenario_json   JSONB,
    evidence_quotes JSONB,
    open_questions  JSONB,
    derived_in_turn INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workshop_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL
                        REFERENCES workshop_sessions(id)
                        ON DELETE CASCADE,
    turn_number     INTEGER NOT NULL,
    user_input      TEXT NOT NULL,
    agent_response  TEXT NOT NULL,
    workshop_phase  TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workshop_sessions_user
    ON workshop_sessions(user_id);

CREATE INDEX idx_workshop_attributes_session
    ON workshop_attributes(session_id);

CREATE INDEX idx_workshop_attributes_confidence
    ON workshop_attributes(confidence);

COMMENT ON TABLE workshop_sessions IS
    'One record per Quality Attribute Workshop conversation.
     context_json holds the full WorkshopContext state and is
     updated after every turn.';

COMMENT ON TABLE workshop_attributes IS
    'Denormalised attribute records for queryable access.
     The authoritative state is in workshop_sessions.context_json.
     These records are updated in sync with context_json.';
