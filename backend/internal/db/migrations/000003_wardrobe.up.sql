-- Romance worlds: a character is base tags + a named outfit per panel (m0 stories_romance.char),
-- and photoreal presets prompt with a sentence description instead of booru tags.
ALTER TABLE characters ADD COLUMN base    TEXT  NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN photo   TEXT  NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN outfits JSONB NOT NULL DEFAULT '{}';
