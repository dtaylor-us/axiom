ALTER TABLE governance_reports
    ADD COLUMN characteristic_alignment INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN trade_off_quality INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN adl_enforceability INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN risk_awareness INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN consistency_bonus INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN score_evidence JSONB;

COMMENT ON COLUMN governance_reports.score_evidence IS
    'Artifact-count evidence strings used to explain each governance score dimension.';
