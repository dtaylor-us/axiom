-- Review health tracking fields for governance reports.
-- Makes silent review degradation visible to users and operators.

ALTER TABLE governance_reports
    ADD COLUMN IF NOT EXISTS review_completed_fully
        BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS governance_score_confidence
        TEXT DEFAULT 'unavailable',
    ADD COLUMN IF NOT EXISTS failed_review_nodes
        JSONB DEFAULT '[]';

-- A governance score may be unavailable when scoring fails; record the report
-- with a null score instead of dropping the row.
ALTER TABLE governance_reports
    ALTER COLUMN governance_score DROP NOT NULL;

COMMENT ON COLUMN governance_reports.governance_score_confidence IS
    'high = all sub-reviews passed, partial = some failed, low = only scoring passed, unavailable = scoring itself failed';

