-- V18: Track send-to-pipeline submissions to suppress rapid duplicates.

ALTER TABLE workshop_sessions
    ADD COLUMN IF NOT EXISTS pipeline_conversation_id UUID,
    ADD COLUMN IF NOT EXISTS pipeline_sent_at TIMESTAMPTZ;

COMMENT ON COLUMN workshop_sessions.pipeline_conversation_id IS
    'The conversation ID created when this session was sent to the architecture pipeline. Used to prevent duplicate submissions.';

COMMENT ON COLUMN workshop_sessions.pipeline_sent_at IS
    'Timestamp when pipeline_conversation_id was created. Used to suppress rapid retries within the duplicate-submission window.';
