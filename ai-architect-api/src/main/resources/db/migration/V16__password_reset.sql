CREATE TABLE password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_ip  TEXT,
    user_agent  TEXT
);

CREATE INDEX idx_password_reset_user
    ON password_reset_tokens(user_id);

CREATE INDEX idx_password_reset_expires
    ON password_reset_tokens(expires_at)
    WHERE used_at IS NULL;

COMMENT ON TABLE password_reset_tokens IS
    'One record per password reset request. token_hash stores a bcrypt hash of the raw token. The raw token exists only in the reset email link. used_at is set when the token is consumed to enforce single use.';
