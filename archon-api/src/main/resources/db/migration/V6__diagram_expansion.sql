-- Add diagrams_json JSONB column to store the intelligent diagram selector output.
-- This column holds an array of diagram objects, each with:
--   diagram_id, type, title, description, mermaid_source, characteristic_addressed
-- Existing component_diagram and sequence_diagram TEXT columns are kept for
-- backward compatibility.
ALTER TABLE architecture_outputs
  ADD COLUMN IF NOT EXISTS diagrams_json JSONB;

COMMENT ON COLUMN architecture_outputs.diagrams_json IS
  'JSON array of diagram objects from the intelligent diagram selector';
