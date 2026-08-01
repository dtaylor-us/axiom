-- Traceability and resolution progress for workshop quality attributes
ALTER TABLE workshop_attributes
    ADD COLUMN IF NOT EXISTS resolved_answers jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE workshop_attributes
    ADD COLUMN IF NOT EXISTS questions_resolved_count integer NOT NULL DEFAULT 0;
ALTER TABLE workshop_attributes
    ADD COLUMN IF NOT EXISTS last_update_summary text;
ALTER TABLE workshop_attributes
    ADD COLUMN IF NOT EXISTS last_updated_turn integer;
