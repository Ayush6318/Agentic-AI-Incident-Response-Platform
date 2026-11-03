CREATE TABLE services (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name             VARCHAR(60)  NOT NULL,
    github_repo      VARCHAR(200) NOT NULL,
    github_token_enc TEXT NOT NULL,
    can_write        BOOLEAN NOT NULL DEFAULT false,
    auto_merge       BOOLEAN NOT NULL DEFAULT false,
    default_branch   VARCHAR(100) NOT NULL DEFAULT 'main',
    loki_labels      JSONB NOT NULL DEFAULT '{}',
    prom_job         VARCHAR(100) NOT NULL DEFAULT '',
    created          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

ALTER TABLE incidents ADD COLUMN service_name VARCHAR(60) NOT NULL DEFAULT '';

CREATE TABLE remediations (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents (id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users (id),
    action      VARCHAR(30) NOT NULL,
    target_sha  VARCHAR(40) NOT NULL,
    status      VARCHAR(20) NOT NULL CHECK (status IN ('pr_opened','merged','failed','blocked')),
    pr_url      TEXT NOT NULL DEFAULT '',
    detail      TEXT NOT NULL DEFAULT '',
    created     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_remediations_incident ON remediations (incident_id);
CREATE INDEX idx_services_user ON services (user_id);