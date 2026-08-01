-- Architecture tactics recommendations for stage 4b tactics advisor pipeline stage.
-- Persists tactic recommendations sourced from the Bass, Clements, Kazman catalog
-- (Software Architecture in Practice, 4th ed., SEI/Addison-Wesley 2021).

CREATE TABLE architecture_tactics (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id         UUID        NOT NULL
                                            REFERENCES conversations(id) ON DELETE CASCADE,
    tactic_id               TEXT        NOT NULL,
    tactic_name             TEXT        NOT NULL,
    characteristic_name     TEXT        NOT NULL,
    category                TEXT        NOT NULL,
    description             TEXT        NOT NULL,
    concrete_application    TEXT        NOT NULL,
    implementation_examples JSONB       NOT NULL DEFAULT '[]',
    already_addressed       BOOLEAN     NOT NULL DEFAULT FALSE,
    address_evidence        TEXT        NOT NULL DEFAULT '',
    effort                  TEXT        NOT NULL CHECK (effort IN ('low', 'medium', 'high')),
    priority                TEXT        NOT NULL CHECK (priority IN ('critical', 'recommended', 'optional')),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_architecture_tactics_conversation_id
    ON architecture_tactics(conversation_id);

CREATE INDEX idx_architecture_tactics_characteristic_name
    ON architecture_tactics(conversation_id, characteristic_name);

CREATE INDEX idx_architecture_tactics_priority
    ON architecture_tactics(conversation_id, priority);

