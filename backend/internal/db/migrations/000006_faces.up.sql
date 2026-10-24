-- Face boxes of a panel's image (m0/faces.py, storyboard panels[].faces): [[x0, y0, x1, y1], ...] normalized 0..1,
-- origin top-left. The reader keeps speech bubbles off them; [] = unknown (old placement).
ALTER TABLE panels ADD COLUMN faces JSONB NOT NULL DEFAULT '[]';
