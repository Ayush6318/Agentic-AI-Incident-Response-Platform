CREATE TABLE users (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'viewer'
                  CHECK (role IN ('viewer', 'sre', 'admin')),
    created       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE incidents (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    status      VARCHAR(30) NOT NULL DEFAULT 'running'
                CHECK (status IN ('running','awaiting_approval','done','rejected','failed')),
    root_cause  TEXT NOT NULL DEFAULT '',
    plan        TEXT NOT NULL DEFAULT '',
    tokens_used INTEGER NOT NULL DEFAULT 0,
    created     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_incidents_user_id ON incidents (user_id);

CREATE TABLE audit_logs (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    action  VARCHAR(50)  NOT NULL,
    target  VARCHAR(100) NOT NULL,
    time    TIMESTAMPTZ NOT NULL DEFAULT now()
);