CREATE TABLE IF NOT EXISTS denov_users (
    uid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    login VARCHAR(64) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);
