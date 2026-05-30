-- Add governance data columns to architecture_outputs
ALTER TABLE architecture_outputs
    ADD COLUMN IF NOT EXISTS trade_offs       JSONB,
    ADD COLUMN IF NOT EXISTS adl_rules        JSONB,
    ADD COLUMN IF NOT EXISTS adl_document     TEXT,
    ADD COLUMN IF NOT EXISTS weaknesses       JSONB,
    ADD COLUMN IF NOT EXISTS weakness_summary TEXT,
    ADD COLUMN IF NOT EXISTS fmea_risks       JSONB;
