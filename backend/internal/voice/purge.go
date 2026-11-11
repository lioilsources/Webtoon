package voice

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"time"
)

// taskRetention: finished tasks (they hold line texts, not voice data) are dropped after a week.
const taskRetention = 7 * 24 * time.Hour

// Purge deletes voices unused for Config.Retention (sample, lines and the AiStack voice), devices
// unseen as long without a voice, consent records past ConsentRetention, old tasks and quota rows,
// and voice directories whose voice is gone (a delete that could not remove its files).
func (s *Server) Purge(ctx context.Context) error {
	now := s.now()
	stale, err := s.store.StaleVoices(ctx, now.Add(-s.cfg.Retention))
	if err != nil {
		return err
	}
	for _, id := range stale {
		if err := s.DeleteVoice(ctx, id, "inactive"); err != nil && !errors.Is(err, ErrNotFound) {
			return err
		}
	}
	devs, err := s.store.StaleDevices(ctx, now.Add(-s.cfg.Retention))
	if err != nil {
		return err
	}
	for _, id := range devs {
		if err := s.store.DeleteDevice(ctx, id); err != nil {
			return err
		}
	}
	if err := s.store.Cleanup(ctx, now.Add(-s.cfg.ConsentRetention), now.Add(-taskRetention), day(now.Add(-48*time.Hour))); err != nil {
		return err
	}
	if len(stale) > 0 || len(devs) > 0 {
		s.log.Info("voice purge", "voices", len(stale), "devices", len(devs))
	}
	return s.sweepDirs(ctx)
}

func (s *Server) sweepDirs(ctx context.Context) error {
	ents, err := os.ReadDir(filepath.Join(s.cfg.DataDir, "voices"))
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	for _, e := range ents {
		if !e.IsDir() || !isUUID(e.Name()) {
			continue
		}
		v, err := s.store.GetVoice(ctx, e.Name())
		if err == nil && v.Status != StatusDeleting {
			continue
		}
		if err != nil && !errors.Is(err, ErrNotFound) {
			return err
		}
		if err := removeVoiceDir(s.cfg.DataDir, e.Name()); err != nil {
			s.log.Error("voice dir not removed", "voice", e.Name(), "err", err)
		}
	}
	return nil
}

// RunPurge calls Purge every interval until ctx ends.
func (s *Server) RunPurge(ctx context.Context, every time.Duration) {
	t := time.NewTicker(every)
	defer t.Stop()
	for {
		if err := s.Purge(ctx); err != nil && ctx.Err() == nil {
			s.log.Error("voice purge", "err", err)
		}
		select {
		case <-ctx.Done():
			return
		case <-t.C:
		}
	}
}

func removeFile(dataDir, rel string) error {
	err := os.Remove(filepath.Join(dataDir, rel))
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	return err
}
