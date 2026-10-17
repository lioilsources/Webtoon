-- M3 author tools: per-character IP-Adapter settings and character reference sheets.

-- {preset, weight, end_at}; only used when identity_level = 'ip_adapter'. NULL = defaults.
ALTER TABLE characters ADD COLUMN ip_adapter JSONB;

-- One render of a character sheet (m0/render.py --sheet): N seeds, best by WD14 identity recall.
CREATE TABLE character_sheets (
    id           TEXT PRIMARY KEY,
    world_id     TEXT NOT NULL,
    character_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'rendering', 'ready', 'failed')),
    seeds        INT NOT NULL DEFAULT 4,
    prompt       TEXT NOT NULL DEFAULT '',
    negative     TEXT NOT NULL DEFAULT '',
    images       JSONB NOT NULL DEFAULT '[]',   -- [{seed, path, recall, missing, unsafe, status, attempts}]
    best         INT,                           -- index into images
    error        TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (world_id, character_id) REFERENCES characters (world_id, id) ON DELETE CASCADE
);
CREATE INDEX character_sheets_character_idx ON character_sheets (world_id, character_id, created_at DESC);
