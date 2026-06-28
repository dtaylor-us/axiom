-- pgcrypto is required for gen_random_uuid().
-- On Azure PostgreSQL Flexible Server, pgcrypto must be allow-listed
-- before it can be created. The extension is enabled via the Azure portal
-- or CLI before running migrations:
--
--   az postgres flexible-server parameter set \
--     --resource-group rg-axiom-dev \
--     --server-name psql-axiom-dev-bpxn \
--     --name azure.extensions \
--     --value pgcrypto
--
-- Alternatively use gen_random_uuid() which is built into PostgreSQL 13+
-- without requiring pgcrypto. Since Azure PostgreSQL Flexible Server
-- runs PostgreSQL 14+, gen_random_uuid() is available natively.
-- This migration replaces the pgcrypto extension with the native function.

CREATE TABLE IF NOT EXISTS review_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    system_description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'EVIDENCE_COLLECTION',
    gap_round INTEGER NOT NULL DEFAULT 0,
    gaps_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_sessions_user_id ON review_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_review_sessions_status ON review_sessions(status);
