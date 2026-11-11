package voice

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

// PGStore is the Postgres Store (migration 000007_player_voice). Hand-written pgx: the queries
// are few and several need row locks that read better as plain SQL.
type PGStore struct{ Pool *pgxpool.Pool }

var _ Store = (*PGStore)(nil)

func NewPGStore(pool *pgxpool.Pool) *PGStore { return &PGStore{Pool: pool} }

func noRows(err error) error {
	if errors.Is(err, pgx.ErrNoRows) {
		return ErrNotFound
	}
	return err
}

func (s *PGStore) CreateDevice(ctx context.Context, d Device) error {
	_, err := s.Pool.Exec(ctx, `INSERT INTO player_devices (id, token_hash, platform, created_at, last_seen_at)
		VALUES ($1, $2, $3, $4, $4)`, d.ID, d.TokenHash, d.Platform, d.CreatedAt)
	return err
}

func (s *PGStore) DeviceByTokenHash(ctx context.Context, hash string, now time.Time) (Device, error) {
	var d Device
	err := s.Pool.QueryRow(ctx, `SELECT id, token_hash, platform, created_at, last_seen_at
		FROM player_devices WHERE token_hash = $1`, hash).
		Scan(&d.ID, &d.TokenHash, &d.Platform, &d.CreatedAt, &d.LastSeenAt)
	if err != nil {
		return d, noRows(err)
	}
	if now.Sub(d.LastSeenAt) >= time.Hour {
		if _, err := s.Pool.Exec(ctx, `UPDATE player_devices SET last_seen_at = $2 WHERE id = $1`, d.ID, now); err != nil {
			return d, err
		}
		d.LastSeenAt = now
	}
	return d, nil
}

func (s *PGStore) DeleteDevice(ctx context.Context, id string) error {
	_, err := s.Pool.Exec(ctx, `DELETE FROM player_devices WHERE id = $1`, id)
	return err
}

const voiceCols = `id, COALESCE(device_id, ''), status, error, sample_file, sample_ext, sample_bytes, sample_duration_s,
	receipt_platform, receipt_original_id, receipt_transaction_id, created_at, updated_at, last_used_at`

func scanVoice(row pgx.Row) (Voice, error) {
	var v Voice
	var dur float32
	err := row.Scan(&v.ID, &v.DeviceID, &v.Status, &v.Error, &v.SampleFile, &v.SampleExt, &v.SampleBytes, &dur,
		&v.ReceiptPlatform, &v.ReceiptOrigID, &v.ReceiptTxID, &v.CreatedAt, &v.UpdatedAt, &v.LastUsedAt)
	v.SampleDurationS = float64(dur)
	return v, err
}

func (s *PGStore) ActiveVoiceByDevice(ctx context.Context, deviceID string) (*Voice, error) {
	v, err := scanVoice(s.Pool.QueryRow(ctx, `SELECT `+voiceCols+` FROM player_voices
		WHERE device_id = $1 AND status <> 'deleting'`, deviceID))
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &v, nil
}

func (s *PGStore) ReceiptDevices(ctx context.Context, platform, origID, deviceID string) (int, error) {
	var n int
	err := s.Pool.QueryRow(ctx, `SELECT count(DISTINCT device_id) FROM player_voices
		WHERE receipt_platform = $1 AND receipt_original_id = $2 AND status <> 'deleting'
		  AND device_id IS NOT NULL AND device_id <> $3`, platform, origID, deviceID).Scan(&n)
	return n, err
}

func (s *PGStore) CreateVoice(ctx context.Context, v Voice, c Consent, t Task) error {
	err := pgx.BeginFunc(ctx, s.Pool, func(tx pgx.Tx) error {
		if _, err := tx.Exec(ctx, `INSERT INTO player_voices (id, device_id, status, error, sample_file, sample_ext,
			sample_bytes, sample_duration_s, receipt_platform, receipt_original_id, receipt_transaction_id,
			created_at, updated_at, last_used_at)
			VALUES ($1, $2, $3, '', $4, $5, $6, $7, $8, $9, $10, $11, $11, $11)`,
			v.ID, v.DeviceID, v.Status, v.SampleFile, v.SampleExt, v.SampleBytes, v.SampleDurationS,
			v.ReceiptPlatform, v.ReceiptOrigID, v.ReceiptTxID, v.CreatedAt); err != nil {
			return err
		}
		if _, err := tx.Exec(ctx, `INSERT INTO player_voice_consents (voice_id, device_id, consent_text, consent_sha256,
			consent_version, consented_at) VALUES ($1, $2, $3, $4, $5, $6)`,
			c.VoiceID, c.DeviceID, c.Text, c.SHA256, c.Version, c.ConsentedAt); err != nil {
			return err
		}
		return insertTask(ctx, tx, t)
	})
	var pe *pgconn.PgError
	if errors.As(err, &pe) && pe.Code == "23505" && pe.ConstraintName == "player_voices_one_per_device" {
		return ErrVoiceExists
	}
	return err
}

func (s *PGStore) GetVoice(ctx context.Context, id string) (Voice, error) {
	v, err := scanVoice(s.Pool.QueryRow(ctx, `SELECT `+voiceCols+` FROM player_voices WHERE id = $1`, id))
	return v, noRows(err)
}

func (s *PGStore) TouchVoice(ctx context.Context, id string, now time.Time) error {
	_, err := s.Pool.Exec(ctx, `UPDATE player_voices SET last_used_at = $2 WHERE id = $1 AND status <> 'deleting'`, id, now)
	return err
}

func (s *PGStore) SetVoiceStatus(ctx context.Context, id, status, msg string, now time.Time) error {
	tag, err := s.Pool.Exec(ctx, `UPDATE player_voices SET status = $2, error = $3, updated_at = $4
		WHERE id = $1 AND status <> 'deleting'`, id, status, msg, now)
	if err == nil && tag.RowsAffected() == 0 {
		return ErrNotFound
	}
	return err
}

func (s *PGStore) BeginDeleteVoice(ctx context.Context, id, reason string, now time.Time, t Task) error {
	return pgx.BeginFunc(ctx, s.Pool, func(tx pgx.Tx) error {
		tag, err := tx.Exec(ctx, `UPDATE player_voices SET status = 'deleting', device_id = NULL, sample_file = '',
			updated_at = $2 WHERE id = $1 AND status <> 'deleting'`, id, now)
		if err != nil {
			return err
		}
		if tag.RowsAffected() == 0 {
			return ErrNotFound
		}
		if _, err := tx.Exec(ctx, `DELETE FROM player_lines WHERE voice_id = $1`, id); err != nil {
			return err
		}
		if _, err := tx.Exec(ctx, `UPDATE voice_tasks SET status = 'cancelled', error = 'voice deleted', updated_at = $2,
			finished_at = $2, lease_until = NULL WHERE voice_id = $1 AND status IN ('queued', 'running')`, id, now); err != nil {
			return err
		}
		if _, err := tx.Exec(ctx, `UPDATE player_voice_consents SET deleted_at = $2, delete_reason = $3
			WHERE voice_id = $1 AND deleted_at IS NULL`, id, now, reason); err != nil {
			return err
		}
		return insertTask(ctx, tx, t)
	})
}

func (s *PGStore) FinishDeleteVoice(ctx context.Context, id string) error {
	_, err := s.Pool.Exec(ctx, `DELETE FROM player_voices WHERE id = $1 AND status = 'deleting'`, id)
	return err
}

func (s *PGStore) GetConsent(ctx context.Context, voiceID string) (Consent, error) {
	var c Consent
	err := s.Pool.QueryRow(ctx, `SELECT voice_id, device_id, consent_text, consent_sha256, consent_version,
		consented_at, deleted_at, delete_reason FROM player_voice_consents WHERE voice_id = $1`, voiceID).
		Scan(&c.VoiceID, &c.DeviceID, &c.Text, &c.SHA256, &c.Version, &c.ConsentedAt, &c.DeletedAt, &c.DeleteReason)
	return c, noRows(err)
}

func (s *PGStore) ids(ctx context.Context, q string, args ...any) ([]string, error) {
	rows, err := s.Pool.Query(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	return pgx.CollectRows(rows, pgx.RowTo[string])
}

func (s *PGStore) StaleVoices(ctx context.Context, before time.Time) ([]string, error) {
	return s.ids(ctx, `SELECT id FROM player_voices WHERE status <> 'deleting' AND last_used_at < $1 ORDER BY id`, before)
}

func (s *PGStore) StaleDevices(ctx context.Context, before time.Time) ([]string, error) {
	return s.ids(ctx, `SELECT d.id FROM player_devices d WHERE d.last_seen_at < $1
		AND NOT EXISTS (SELECT 1 FROM player_voices v WHERE v.device_id = d.id AND v.status <> 'deleting') ORDER BY d.id`, before)
}

func (s *PGStore) Cleanup(ctx context.Context, consentsBefore, tasksBefore time.Time, quotaDay string) error {
	if _, err := s.Pool.Exec(ctx, `DELETE FROM player_voice_consents WHERE deleted_at < $1`, consentsBefore); err != nil {
		return err
	}
	if _, err := s.Pool.Exec(ctx, `DELETE FROM voice_tasks WHERE finished_at < $1`, tasksBefore); err != nil {
		return err
	}
	_, err := s.Pool.Exec(ctx, `DELETE FROM player_quota WHERE day < $1::text::date`, quotaDay)
	return err
}

func (s *PGStore) Lines(ctx context.Context, voiceID string, hashes []string) (map[string]Line, error) {
	rows, err := s.Pool.Query(ctx, `SELECT voice_id, hash, lang, file, bytes, duration_s, created_at
		FROM player_lines WHERE voice_id = $1 AND hash = ANY($2)`, voiceID, hashes)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string]Line{}
	for rows.Next() {
		var l Line
		var dur float32
		if err := rows.Scan(&l.VoiceID, &l.Hash, &l.Lang, &l.File, &l.Bytes, &dur, &l.CreatedAt); err != nil {
			return nil, err
		}
		l.DurationS = float64(dur)
		out[l.Hash] = l
	}
	return out, rows.Err()
}

func (s *PGStore) PutLine(ctx context.Context, l Line) error {
	// Only for a voice that is not being deleted (the row lock orders it against BeginDeleteVoice).
	return pgx.BeginFunc(ctx, s.Pool, func(tx pgx.Tx) error {
		var st string
		if err := tx.QueryRow(ctx, `SELECT status FROM player_voices WHERE id = $1 FOR UPDATE`, l.VoiceID).Scan(&st); err != nil {
			return noRows(err)
		}
		if st == StatusDeleting {
			return ErrNotFound
		}
		_, err := tx.Exec(ctx, `INSERT INTO player_lines (voice_id, hash, lang, file, bytes, duration_s, created_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7)
			ON CONFLICT (voice_id, hash) DO UPDATE SET file = EXCLUDED.file, bytes = EXCLUDED.bytes,
				duration_s = EXCLUDED.duration_s, created_at = EXCLUDED.created_at`,
			l.VoiceID, l.Hash, l.Lang, l.File, l.Bytes, l.DurationS, l.CreatedAt)
		return err
	})
}

func (s *PGStore) AddQuota(ctx context.Context, deviceID, day string, n, limit int) (int, bool, error) {
	if n <= 0 {
		var used int
		err := s.Pool.QueryRow(ctx, `SELECT COALESCE((SELECT lines FROM player_quota WHERE device_id = $1 AND day = $2::text::date), 0)`,
			deviceID, day).Scan(&used)
		return used, true, err
	}
	if n > limit {
		return 0, false, nil
	}
	var used int
	err := s.Pool.QueryRow(ctx, `INSERT INTO player_quota (device_id, day, lines) VALUES ($1, $2::text::date, $3)
		ON CONFLICT (device_id, day) DO UPDATE SET lines = player_quota.lines + EXCLUDED.lines
		WHERE player_quota.lines + EXCLUDED.lines <= $4
		RETURNING lines`, deviceID, day, n, limit).Scan(&used)
	if errors.Is(err, pgx.ErrNoRows) {
		err = s.Pool.QueryRow(ctx, `SELECT lines FROM player_quota WHERE device_id = $1 AND day = $2::text::date`, deviceID, day).Scan(&used)
		return used, false, err
	}
	return used, err == nil, err
}

const taskCols = `id, kind, voice_id, device_id, lang, lines, idem_key, priority, status, error, attempts, worker,
	run_after, lease_until, created_at, updated_at, finished_at`

func scanTask(row pgx.Row) (Task, error) {
	var t Task
	var lines []byte
	err := row.Scan(&t.ID, &t.Kind, &t.VoiceID, &t.DeviceID, &t.Lang, &lines, &t.IdemKey, &t.Priority, &t.Status,
		&t.Error, &t.Attempts, &t.Worker, &t.RunAfter, &t.LeaseUntil, &t.CreatedAt, &t.UpdatedAt, &t.FinishedAt)
	if err == nil && len(lines) > 0 {
		err = json.Unmarshal(lines, &t.Lines)
	}
	return t, err
}

type execer interface {
	Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error)
}

func insertTask(ctx context.Context, db execer, t Task) error {
	lines := t.Lines
	if lines == nil {
		lines = []TaskLine{}
	}
	b, err := json.Marshal(lines)
	if err != nil {
		return err
	}
	_, err = db.Exec(ctx, `INSERT INTO voice_tasks (id, kind, voice_id, device_id, lang, lines, idem_key, priority,
		status, error, attempts, worker, run_after, created_at, updated_at, finished_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 0, '', $11, $12, $12, $13)`,
		t.ID, t.Kind, t.VoiceID, t.DeviceID, t.Lang, b, t.IdemKey, t.Priority, t.Status, t.Error, t.RunAfter,
		t.CreatedAt, t.FinishedAt)
	return err
}

func (s *PGStore) OpenLineTask(ctx context.Context, voiceID, idemKey string) (*Task, error) {
	t, err := scanTask(s.Pool.QueryRow(ctx, `SELECT `+taskCols+` FROM voice_tasks
		WHERE kind = 'lines' AND voice_id = $1 AND idem_key = $2 AND status IN ('queued', 'running')
		ORDER BY created_at LIMIT 1`, voiceID, idemKey))
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func (s *PGStore) CreateTask(ctx context.Context, t Task) error { return insertTask(ctx, s.Pool, t) }

func (s *PGStore) GetTask(ctx context.Context, id string) (Task, error) {
	t, err := scanTask(s.Pool.QueryRow(ctx, `SELECT `+taskCols+` FROM voice_tasks WHERE id = $1`, id))
	return t, noRows(err)
}

const runnableSQL = `((status = 'queued' AND run_after <= $1) OR (status = 'running' AND lease_until < $1))`

func (s *PGStore) PendingTasks(ctx context.Context, now time.Time) (int, error) {
	var n int
	err := s.Pool.QueryRow(ctx, `SELECT count(*) FROM voice_tasks WHERE `+runnableSQL, now).Scan(&n)
	return n, err
}

func (s *PGStore) ClaimTask(ctx context.Context, worker string, now, leaseUntil time.Time) (*Task, error) {
	t, err := scanTask(s.Pool.QueryRow(ctx, `UPDATE voice_tasks SET status = 'running', worker = $2, lease_until = $3,
		attempts = attempts + 1, updated_at = $1
		WHERE id = (SELECT id FROM voice_tasks WHERE `+runnableSQL+`
			ORDER BY priority DESC, created_at, id LIMIT 1 FOR UPDATE SKIP LOCKED)
		RETURNING `+taskCols, now, worker, leaseUntil))
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func (s *PGStore) HeartbeatTask(ctx context.Context, id, worker string, now, leaseUntil time.Time) error {
	tag, err := s.Pool.Exec(ctx, `UPDATE voice_tasks SET lease_until = $3, updated_at = $4
		WHERE id = $1 AND worker = $2 AND status = 'running'`, id, worker, leaseUntil, now)
	if err == nil && tag.RowsAffected() == 0 {
		return ErrLeaseLost
	}
	return err
}

func (s *PGStore) FinishTask(ctx context.Context, id, worker, status, msg string, runAfter, now time.Time) error {
	var tag pgconn.CommandTag
	var err error
	if status == TaskQueued {
		tag, err = s.Pool.Exec(ctx, `UPDATE voice_tasks SET status = $3, error = $4, run_after = $5, worker = '',
			lease_until = NULL, updated_at = $6 WHERE id = $1 AND worker = $2 AND status = 'running'`,
			id, worker, status, msg, runAfter, now)
	} else {
		tag, err = s.Pool.Exec(ctx, `UPDATE voice_tasks SET status = $3, error = $4, lease_until = NULL, updated_at = $5,
			finished_at = $5 WHERE id = $1 AND worker = $2 AND status = 'running'`, id, worker, status, msg, now)
	}
	if err == nil && tag.RowsAffected() == 0 {
		return ErrLeaseLost
	}
	return err
}
