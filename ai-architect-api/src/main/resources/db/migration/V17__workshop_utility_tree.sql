-- V17: Add utility tree and architectural implications to workshop sessions.
--
-- utility_tree holds the complete SEI QAW utility tree generated after
-- sufficient scenarios have been elicited (at least 5 partial-or-better
-- scenarios across at least 3 attributes).
--
-- architecture_implications holds the list of architectural constraints
-- derived from driver scenarios in the utility tree. Each implication
-- traces to a specific scenario and uses component types, not technology names.

ALTER TABLE workshop_sessions
    ADD COLUMN IF NOT EXISTS utility_tree JSONB,
    ADD COLUMN IF NOT EXISTS architecture_implications JSONB;

COMMENT ON COLUMN workshop_sessions.utility_tree IS
    'SEI QAW utility tree: scenarios organised by attribute and refinement, '
    'scored by business importance and technical risk. Null until generated.';

COMMENT ON COLUMN workshop_sessions.architecture_implications IS
    'Architectural implications derived from driver scenarios. '
    'Each entry traces to a specific scenario. Null until generated.';
