CREATE TABLE IF NOT EXISTS denov_sessions (
    token TEXT PRIMARY KEY,
    uid UUID NOT NULL REFERENCES denov_users(uid),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
