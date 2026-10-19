-- Motion panels: a 1–3 s seamless loop rendered from the finished still (PLAN-motion-panels.md).
-- video_status '' = static panel; pending/rendering/ready/failed mirror the still's lifecycle.
ALTER TABLE panels ADD COLUMN animate      BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE panels ADD COLUMN motion       TEXT    NOT NULL DEFAULT '';
ALTER TABLE panels ADD COLUMN loop_seconds INT     NOT NULL DEFAULT 2 CHECK (loop_seconds BETWEEN 1 AND 3);
ALTER TABLE panels ADD COLUMN video_status TEXT    NOT NULL DEFAULT '' CHECK (video_status IN ('', 'pending', 'rendering', 'ready', 'failed'));
ALTER TABLE panels ADD COLUMN video_path   TEXT    NOT NULL DEFAULT '';
ALTER TABLE panels ADD COLUMN video_seed   BIGINT  NOT NULL DEFAULT 0;
ALTER TABLE panels ADD COLUMN video_error  TEXT    NOT NULL DEFAULT '';
