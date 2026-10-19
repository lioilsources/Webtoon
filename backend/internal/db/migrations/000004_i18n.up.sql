-- Translated episode titles keyed by language; bubble and choice translations live inside their JSON (i18n).
ALTER TABLE episodes ADD COLUMN title_i18n JSONB NOT NULL DEFAULT '{}';
