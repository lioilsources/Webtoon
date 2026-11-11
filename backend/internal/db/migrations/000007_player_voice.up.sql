-- Player's own voice for the Toonfork app (docs/voice-backend.md, internal/voice).
-- The samples themselves are never in the database: they are encrypted files in VOICE_DATA_DIR.

-- Anonymous devices. Only the sha256 of the bearer token is stored.
CREATE TABLE player_devices (
    id           TEXT PRIMARY KEY,
    token_hash   TEXT NOT NULL UNIQUE,
    platform     TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A voice stays as 'deleting' (detached from its device, sample already removed) until the
-- worker has deleted it in AiStack; then the row goes.
CREATE TABLE player_voices (
    id                     TEXT PRIMARY KEY,
    device_id              TEXT REFERENCES player_devices (id) ON DELETE SET NULL,
    status                 TEXT NOT NULL CHECK (status IN ('queued', 'ready', 'failed', 'deleting')),
    error                  TEXT NOT NULL DEFAULT '',
    sample_file            TEXT NOT NULL DEFAULT '',
    sample_ext             TEXT NOT NULL DEFAULT '',
    sample_bytes           INT NOT NULL DEFAULT 0,
    sample_duration_s      REAL NOT NULL DEFAULT 0,
    receipt_platform       TEXT NOT NULL,
    receipt_original_id    TEXT NOT NULL,
    receipt_transaction_id TEXT NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL,
    last_used_at           TIMESTAMPTZ NOT NULL
);
-- One voice per device.
CREATE UNIQUE INDEX player_voices_one_per_device ON player_voices (device_id) WHERE status <> 'deleting';
CREATE INDEX player_voices_receipt ON player_voices (receipt_platform, receipt_original_id) WHERE status <> 'deleting';
CREATE INDEX player_voices_last_used ON player_voices (last_used_at) WHERE status <> 'deleting';

-- Consent audit record; no foreign key, it outlives the voice by VOICE_CONSENT_RETENTION_DAYS.
CREATE TABLE player_voice_consents (
    voice_id        TEXT PRIMARY KEY,
    device_id       TEXT NOT NULL,
    consent_text    TEXT NOT NULL,
    consent_sha256  TEXT NOT NULL,
    consent_version TEXT NOT NULL,
    consented_at    TIMESTAMPTZ NOT NULL,
    deleted_at      TIMESTAMPTZ,
    delete_reason   TEXT NOT NULL DEFAULT ''
);

-- Rendered lines, keyed by sha256(voice_id, lang, text); the audio is an encrypted file.
CREATE TABLE player_lines (
    voice_id   TEXT NOT NULL REFERENCES player_voices (id) ON DELETE CASCADE,
    hash       TEXT NOT NULL CHECK (length(hash) = 64),
    lang       TEXT NOT NULL,
    file       TEXT NOT NULL,
    bytes      INT NOT NULL,
    duration_s REAL NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (voice_id, hash)
);

-- Newly voiced lines per device and UTC day.
CREATE TABLE player_quota (
    device_id TEXT NOT NULL REFERENCES player_devices (id) ON DELETE CASCADE,
    day       DATE NOT NULL,
    lines     INT NOT NULL DEFAULT 0,
    PRIMARY KEY (device_id, day)
);

-- Queue of the Spark voice worker (separate from jobs, which the Mac pipeline workers claim).
CREATE TABLE voice_tasks (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('voice_create', 'voice_delete', 'lines')),
    voice_id    TEXT NOT NULL,
    device_id   TEXT NOT NULL DEFAULT '',
    lang        TEXT NOT NULL DEFAULT '',
    lines       JSONB NOT NULL DEFAULT '[]',
    idem_key    TEXT NOT NULL DEFAULT '',
    priority    INT NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'failed', 'cancelled')),
    error       TEXT NOT NULL DEFAULT '',
    attempts    INT NOT NULL DEFAULT 0,
    worker      TEXT NOT NULL DEFAULT '',
    run_after   TIMESTAMPTZ NOT NULL,
    lease_until TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ
);
CREATE INDEX voice_tasks_open ON voice_tasks (priority DESC, created_at) WHERE status IN ('queued', 'running');
CREATE INDEX voice_tasks_voice ON voice_tasks (voice_id);
