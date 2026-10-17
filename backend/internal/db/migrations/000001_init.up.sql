-- M1 data model (WEBTOON_PLAN §2): World → Campaign → Episode → Panel, plus a job table for the worker.
-- IDs are short prefixed text ids (w_…, cp_…, ep_…). Character/location ids are the ones the storyboard
-- LLM sees and must reference, so they are unique per world, not globally.

CREATE TABLE settings (
    key        TEXT PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per style preset (styles.json "presets"); shared prompt pieces live in settings('styles').
CREATE TABLE style_presets (
    id         TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE worlds (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    title       TEXT NOT NULL,
    synopsis    TEXT NOT NULL DEFAULT '',
    tone        TEXT NOT NULL DEFAULT '',
    audience    TEXT NOT NULL DEFAULT 'teen' CHECK (audience IN ('kids', 'teen', 'adult')),
    language    TEXT NOT NULL DEFAULT 'cs',
    style_id    TEXT NOT NULL,
    bible       JSONB NOT NULL DEFAULT '{}',
    canon       JSONB NOT NULL DEFAULT '{}',
    permissions JSONB NOT NULL DEFAULT '{}',
    visibility  TEXT NOT NULL DEFAULT 'private' CHECK (visibility IN ('private', 'unlisted', 'public')),
    intro_episode_ids JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX worlds_owner_idx ON worlds (owner_id);
CREATE INDEX worlds_visibility_idx ON worlds (visibility);

CREATE TABLE characters (
    world_id         TEXT NOT NULL REFERENCES worlds (id) ON DELETE CASCADE,
    id               TEXT NOT NULL,
    owner_id         TEXT NOT NULL,
    name             TEXT NOT NULL,
    role             TEXT NOT NULL DEFAULT 'npc' CHECK (role IN ('npc', 'playable', 'player_created')),
    count_tag        TEXT NOT NULL DEFAULT '',
    description      TEXT NOT NULL DEFAULT '',
    personality      TEXT NOT NULL DEFAULT '',
    speech_style     TEXT NOT NULL DEFAULT '',
    tag_prompt       TEXT NOT NULL DEFAULT '',
    reference_images JSONB NOT NULL DEFAULT '[]',
    identity_level   TEXT NOT NULL DEFAULT 'prompt' CHECK (identity_level IN ('prompt', 'ip_adapter', 'lora')),
    identity_asset   TEXT,
    position         INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (world_id, id)
);

CREATE TABLE locations (
    world_id         TEXT NOT NULL REFERENCES worlds (id) ON DELETE CASCADE,
    id               TEXT NOT NULL,
    name             TEXT NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    tag_prompt       TEXT NOT NULL DEFAULT '',
    reference_images JSONB NOT NULL DEFAULT '[]',
    mood             TEXT NOT NULL DEFAULT '',
    position         INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (world_id, id)
);

CREATE TABLE campaigns (
    id                      TEXT PRIMARY KEY,
    world_id                TEXT NOT NULL REFERENCES worlds (id) ON DELETE CASCADE,
    player_id               TEXT NOT NULL,
    title                   TEXT NOT NULL DEFAULT '',
    status                  TEXT NOT NULL DEFAULT 'active',
    player_character_id     TEXT,
    state                   JSONB NOT NULL DEFAULT '{}',
    canon_progress          JSONB NOT NULL DEFAULT '[]',
    branch_parent_episode_id TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX campaigns_world_idx ON campaigns (world_id);
CREATE INDEX campaigns_player_idx ON campaigns (player_id);

CREATE TABLE episodes (
    id             TEXT PRIMARY KEY,
    campaign_id    TEXT NOT NULL REFERENCES campaigns (id) ON DELETE CASCADE,
    idx            INT NOT NULL,
    title          TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'generating', 'ready', 'failed')),
    premise        TEXT NOT NULL DEFAULT '',
    chosen         JSONB,              -- {choice_id, kind, text} that led to this episode
    moderation     JSONB,              -- verdict on free-text input
    storyboard     JSONB,
    choices        JSONB NOT NULL DEFAULT '[]',
    state_diff     JSONB,
    state_snapshot JSONB,              -- campaign state after this episode was applied
    warnings       JSONB NOT NULL DEFAULT '[]',
    panels_ready   INT NOT NULL DEFAULT 0,
    panels_total   INT NOT NULL DEFAULT 0,
    credits_cost   INT NOT NULL DEFAULT 0,
    error          TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (campaign_id, idx)
);

CREATE TABLE panels (
    episode_id     TEXT NOT NULL REFERENCES episodes (id) ON DELETE CASCADE,
    idx            INT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'rendering', 'ready', 'failed')),
    shot           TEXT NOT NULL DEFAULT '',
    location_id    TEXT NOT NULL DEFAULT '',
    image_path     TEXT NOT NULL DEFAULT '',
    prompt         TEXT NOT NULL DEFAULT '',
    negative       TEXT NOT NULL DEFAULT '',
    seed           BIGINT NOT NULL DEFAULT 0,
    width          INT NOT NULL DEFAULT 0,
    height         INT NOT NULL DEFAULT 0,
    gap_after      TEXT NOT NULL DEFAULT 'medium',
    bubbles        JSONB NOT NULL DEFAULT '[]',
    sfx            JSONB NOT NULL DEFAULT '[]',
    characters     JSONB NOT NULL DEFAULT '[]',
    visual_tags    JSONB NOT NULL DEFAULT '[]',
    rating         JSONB,
    identity       JSONB,              -- {character_id: {recall, missing}}
    identity_score REAL,
    attempts       JSONB NOT NULL DEFAULT '[]',
    error          TEXT NOT NULL DEFAULT '',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (episode_id, idx)
);

CREATE TABLE jobs (
    id           BIGSERIAL PRIMARY KEY,
    kind         TEXT NOT NULL,
    payload      JSONB NOT NULL,
    status       TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'failed')),
    attempts     INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    run_after    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error   TEXT NOT NULL DEFAULT '',
    locked_by    TEXT NOT NULL DEFAULT '',
    locked_at    TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX jobs_ready_idx ON jobs (run_after, id) WHERE status = 'queued';
