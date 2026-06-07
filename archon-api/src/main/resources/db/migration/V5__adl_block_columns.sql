-- Add Richards-spec ADL fields to architecture_outputs.
-- These store the Mark Richards ADL block structure alongside
-- the existing adl_rules JSONB column (which is kept for
-- backward compatibility).
ALTER TABLE architecture_outputs
  ADD COLUMN IF NOT EXISTS requires_tooling TEXT,
  ADD COLUMN IF NOT EXISTS codegen_prompt   TEXT,
  ADD COLUMN IF NOT EXISTS adl_source       TEXT;

COMMENT ON COLUMN architecture_outputs.requires_tooling IS
  'The ADL REQUIRES field — names the test tooling needed';
COMMENT ON COLUMN architecture_outputs.codegen_prompt IS
  'The ADL PROMPT field — LLM instruction to generate test code';
COMMENT ON COLUMN architecture_outputs.adl_source IS
  'The complete ADL pseudo-code block, preserved verbatim';
