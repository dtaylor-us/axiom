CREATE TABLE session_documents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID NOT NULL
                     REFERENCES sessions(id) ON DELETE CASCADE,
    document_type    VARCHAR(50)  NOT NULL,
    filename         VARCHAR(255),
    source_label     VARCHAR(255),
    storage_key      VARCHAR(500),
    extracted_text   TEXT,
    extraction_result JSONB,
    status           VARCHAR(50)  NOT NULL DEFAULT 'PENDING',
    error_message    TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    processed_at     TIMESTAMPTZ
);

CREATE INDEX idx_docs_session_id ON session_documents(session_id);
CREATE INDEX idx_docs_status     ON session_documents(status);
