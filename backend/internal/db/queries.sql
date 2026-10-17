-- name: UpsertSetting :exec
INSERT INTO settings (key, value) VALUES ($1, $2)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now();

-- name: GetSetting :one
SELECT value FROM settings WHERE key = $1;

-- name: UpsertStylePreset :exec
INSERT INTO style_presets (id, data) VALUES ($1, $2)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = now();

-- name: ListStylePresets :many
SELECT id, data FROM style_presets ORDER BY id;

-- name: CreateWorld :one
INSERT INTO worlds (id, owner_id, title, synopsis, tone, audience, language, style_id, bible, canon, permissions, visibility)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
RETURNING *;

-- name: UpsertWorld :exec
INSERT INTO worlds (id, owner_id, title, synopsis, tone, audience, language, style_id, bible, canon, permissions, visibility)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
ON CONFLICT (id) DO UPDATE SET
    owner_id = EXCLUDED.owner_id, title = EXCLUDED.title, synopsis = EXCLUDED.synopsis, tone = EXCLUDED.tone,
    audience = EXCLUDED.audience, language = EXCLUDED.language, style_id = EXCLUDED.style_id,
    bible = EXCLUDED.bible, canon = EXCLUDED.canon, permissions = EXCLUDED.permissions,
    visibility = EXCLUDED.visibility, updated_at = now();

-- name: GetWorld :one
SELECT * FROM worlds WHERE id = $1;

-- name: ListWorlds :many
SELECT * FROM worlds
WHERE (visibility = 'public' OR owner_id = @viewer::text)
  AND (sqlc.narg(visibility)::text IS NULL OR visibility = sqlc.narg(visibility)::text)
ORDER BY created_at DESC
LIMIT 200;

-- name: UpdateWorld :one
UPDATE worlds SET
    title       = COALESCE(sqlc.narg(title), title),
    synopsis    = COALESCE(sqlc.narg(synopsis), synopsis),
    tone        = COALESCE(sqlc.narg(tone), tone),
    audience    = COALESCE(sqlc.narg(audience), audience),
    language    = COALESCE(sqlc.narg(language), language),
    style_id    = COALESCE(sqlc.narg(style_id), style_id),
    visibility  = COALESCE(sqlc.narg(visibility), visibility),
    bible       = COALESCE(sqlc.narg(bible), bible),
    canon       = COALESCE(sqlc.narg(canon), canon),
    permissions = COALESCE(sqlc.narg(permissions), permissions),
    updated_at  = now()
WHERE id = @id
RETURNING *;

-- name: CreateCharacter :one
INSERT INTO characters (world_id, id, owner_id, name, role, count_tag, description, personality, speech_style,
                        tag_prompt, reference_images, identity_level, identity_asset, position)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
        (SELECT count(*) FROM characters c WHERE c.world_id = $1))
RETURNING *;

-- name: UpsertCharacter :exec
INSERT INTO characters (world_id, id, owner_id, name, role, count_tag, description, personality, speech_style,
                        tag_prompt, reference_images, identity_level, identity_asset, position)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
ON CONFLICT (world_id, id) DO UPDATE SET
    owner_id = EXCLUDED.owner_id, name = EXCLUDED.name, role = EXCLUDED.role, count_tag = EXCLUDED.count_tag,
    description = EXCLUDED.description, personality = EXCLUDED.personality, speech_style = EXCLUDED.speech_style,
    tag_prompt = EXCLUDED.tag_prompt, reference_images = EXCLUDED.reference_images,
    identity_level = EXCLUDED.identity_level, identity_asset = EXCLUDED.identity_asset, position = EXCLUDED.position;

-- name: ListCharacters :many
SELECT * FROM characters WHERE world_id = $1 ORDER BY position, created_at;

-- name: CreateLocation :one
INSERT INTO locations (world_id, id, name, description, tag_prompt, reference_images, mood, position)
VALUES ($1, $2, $3, $4, $5, $6, $7, (SELECT count(*) FROM locations l WHERE l.world_id = $1))
RETURNING *;

-- name: UpsertLocation :exec
INSERT INTO locations (world_id, id, name, description, tag_prompt, reference_images, mood, position)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT (world_id, id) DO UPDATE SET
    name = EXCLUDED.name, description = EXCLUDED.description, tag_prompt = EXCLUDED.tag_prompt,
    reference_images = EXCLUDED.reference_images, mood = EXCLUDED.mood, position = EXCLUDED.position;

-- name: ListLocations :many
SELECT * FROM locations WHERE world_id = $1 ORDER BY position, created_at;

-- name: CreateCampaign :one
INSERT INTO campaigns (id, world_id, player_id, title, player_character_id, state, canon_progress)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING *;

-- name: GetCampaign :one
SELECT * FROM campaigns WHERE id = $1;

-- name: GetCampaignForUpdate :one
SELECT * FROM campaigns WHERE id = $1 FOR UPDATE;

-- name: UpdateCampaignState :exec
UPDATE campaigns SET state = $2, canon_progress = $3, updated_at = now() WHERE id = $1;

-- name: CreateEpisode :one
INSERT INTO episodes (id, campaign_id, idx, premise, chosen)
VALUES ($1, $2, $3, $4, $5)
RETURNING *;

-- name: GetEpisode :one
SELECT * FROM episodes WHERE id = $1;

-- name: GetEpisodeForUpdate :one
SELECT * FROM episodes WHERE id = $1 FOR UPDATE;

-- name: ListEpisodes :many
SELECT * FROM episodes WHERE campaign_id = $1 ORDER BY idx;

-- name: GetLatestEpisode :one
SELECT * FROM episodes WHERE campaign_id = $1 ORDER BY idx DESC LIMIT 1;

-- name: SetEpisodeStatus :exec
UPDATE episodes SET status = $2, error = $3, updated_at = now() WHERE id = $1;

-- name: SetEpisodeModeration :exec
UPDATE episodes SET moderation = $2, updated_at = now() WHERE id = $1;

-- name: SaveStoryboard :exec
UPDATE episodes SET
    title = $2, storyboard = $3, choices = $4, state_diff = $5, warnings = $6,
    panels_total = $7, credits_cost = $8, panels_ready = 0, status = 'generating', error = '', updated_at = now()
WHERE id = $1;

-- name: FinishEpisode :exec
UPDATE episodes SET status = $2, state_snapshot = $3, error = $4, updated_at = now() WHERE id = $1;

-- name: RefreshPanelsReady :one
UPDATE episodes e SET
    panels_ready = (SELECT count(*) FROM panels p WHERE p.episode_id = e.id AND p.status = 'ready'),
    updated_at = now()
WHERE e.id = $1
RETURNING panels_ready, panels_total, status;

-- name: PanelProgress :one
SELECT
    count(*) FILTER (WHERE status = 'ready')::int  AS ready,
    count(*) FILTER (WHERE status = 'failed')::int AS failed,
    count(*)::int AS total
FROM panels WHERE episode_id = $1;

-- name: InsertPanel :exec
INSERT INTO panels (episode_id, idx, shot, location_id, gap_after, bubbles, sfx, characters, visual_tags)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);

-- name: GetPanel :one
SELECT * FROM panels WHERE episode_id = $1 AND idx = $2;

-- name: ListPanels :many
SELECT * FROM panels WHERE episode_id = $1 ORDER BY idx;

-- name: SetPanelStatus :exec
UPDATE panels SET status = $3, error = $4, updated_at = now() WHERE episode_id = $1 AND idx = $2;

-- name: SavePanelResult :exec
UPDATE panels SET
    status = $3, image_path = $4, prompt = $5, negative = $6, seed = $7, width = $8, height = $9,
    rating = $10, identity = $11, identity_score = $12, attempts = $13, error = $14, updated_at = now()
WHERE episode_id = $1 AND idx = $2;

-- name: UpdatePanelBubbles :exec
UPDATE panels SET bubbles = $3, updated_at = now() WHERE episode_id = $1 AND idx = $2;

-- run_after uses the database clock (ClaimJob compares against now(); app and DB clocks may differ).
-- name: EnqueueJob :one
INSERT INTO jobs (kind, payload, max_attempts, run_after)
VALUES (@kind, @payload, @max_attempts, now() + make_interval(secs => @delay_seconds::float8))
RETURNING id;

-- name: ClaimJob :one
UPDATE jobs SET status = 'running', attempts = attempts + 1, locked_by = $1, locked_at = now(), updated_at = now()
WHERE id = (
    SELECT j.id FROM jobs j
    WHERE j.status = 'queued' AND j.run_after <= now()
    ORDER BY j.run_after, j.id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING *;

-- name: CompleteJob :exec
UPDATE jobs SET status = 'done', locked_by = '', updated_at = now() WHERE id = $1;

-- name: RetryJob :exec
UPDATE jobs SET status = 'queued', run_after = $2, last_error = $3, locked_by = '', updated_at = now() WHERE id = $1;

-- Upstream (LLM / ComfyUI / WD14) is off-schedule: requeue without burning an attempt.
-- name: DeferJob :exec
UPDATE jobs SET status = 'queued', attempts = GREATEST(attempts - 1, 0), run_after = $2, last_error = $3,
    locked_by = '', updated_at = now()
WHERE id = $1;

-- name: FailJob :exec
UPDATE jobs SET status = 'failed', last_error = $2, locked_by = '', updated_at = now() WHERE id = $1;

-- name: RequeueStaleJobs :execrows
UPDATE jobs SET status = 'queued', attempts = GREATEST(attempts - 1, 0), locked_by = '', updated_at = now()
WHERE status = 'running' AND locked_at < $1;

-- name: GetJob :one
SELECT * FROM jobs WHERE id = $1;

-- name: ListJobs :many
SELECT * FROM jobs ORDER BY id;

-- name: WorldCounts :one
SELECT
    (SELECT count(*) FROM campaigns c WHERE c.world_id = $1)::int AS campaigns,
    (SELECT count(DISTINCT c.player_id) FROM campaigns c WHERE c.world_id = $1)::int AS players,
    (SELECT count(*) FROM episodes e JOIN campaigns c ON c.id = e.campaign_id WHERE c.world_id = $1)::int AS episodes,
    (SELECT count(*) FROM episodes e JOIN campaigns c ON c.id = e.campaign_id
        WHERE c.world_id = $1 AND e.status = 'ready')::int AS episodes_ready,
    (SELECT count(*) FROM episodes e JOIN campaigns c ON c.id = e.campaign_id
        WHERE c.world_id = $1 AND e.status = 'failed')::int AS episodes_failed,
    (SELECT count(*) FROM panels p JOIN episodes e ON e.id = p.episode_id JOIN campaigns c ON c.id = e.campaign_id
        WHERE c.world_id = $1 AND p.status = 'ready')::int AS panels_ready,
    (SELECT count(*) FROM characters ch WHERE ch.world_id = $1 AND ch.role = 'player_created')::int AS player_created_characters;

-- name: ChoiceDistribution :many
SELECT
    COALESCE(e.chosen->>'kind', '')::text      AS kind,
    COALESCE(e.chosen->>'choice_id', '')::text AS choice_id,
    count(*)::int AS n
FROM episodes e JOIN campaigns c ON c.id = e.campaign_id
WHERE c.world_id = $1 AND e.chosen IS NOT NULL
GROUP BY 1, 2
ORDER BY n DESC, 1, 2;

-- name: CampaignDepths :many
SELECT d.depth::int AS depth, count(*)::int AS campaigns FROM (
    SELECT max(e.idx) AS depth FROM episodes e JOIN campaigns c ON c.id = e.campaign_id
    WHERE c.world_id = $1 GROUP BY e.campaign_id
) d GROUP BY d.depth ORDER BY d.depth;

-- name: CanonReached :many
SELECT node::text AS node_id, count(*)::int AS campaigns
FROM campaigns c, jsonb_array_elements_text(c.canon_progress) AS node
WHERE c.world_id = $1
GROUP BY node ORDER BY node;
