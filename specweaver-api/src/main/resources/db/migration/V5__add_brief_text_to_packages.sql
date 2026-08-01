ALTER TABLE generated_packages
  ADD COLUMN IF NOT EXISTS brief_text TEXT;
-- Stores the formatted requirements brief that will be
-- pre-populated in the Archon chat input.
-- Populated when the package is generated.
-- Persists so the user can always retrieve it.
