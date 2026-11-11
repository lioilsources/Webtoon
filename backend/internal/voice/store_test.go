package voice

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/ol1n/webtoon/backend/internal/db"
)

// storeContract checks the semantics both stores must share. It runs on MemStore always and on
// PGStore when WEBTOON_TEST_DATABASE_URL is set (CI: the Postgres service of backend.yml).
func storeContract(t *testing.T, st Store) {
	ctx := context.Background()
	now := t0
	must := func(err error) {
		t.Helper()
		if err != nil {
			t.Fatal(err)
		}
	}
	must(st.CreateDevice(ctx, Device{ID: "dev_a", TokenHash: "ha", Platform: "ios", CreatedAt: now, LastSeenAt: now}))
	must(st.CreateDevice(ctx, Device{ID: "dev_b", TokenHash: "hb", CreatedAt: now, LastSeenAt: now}))
	if _, err := st.DeviceByTokenHash(ctx, "nope", now); !errors.Is(err, ErrNotFound) {
		t.Fatal(err)
	}
	d, err := st.DeviceByTokenHash(ctx, "ha", now.Add(2*time.Hour))
	must(err)
	if d.ID != "dev_a" || !d.LastSeenAt.Equal(now.Add(2*time.Hour)) {
		t.Fatalf("%+v", d)
	}

	vid := "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
	task := func(id, kind, vid string, prio int, at time.Time) Task {
		return Task{ID: id, Kind: kind, VoiceID: vid, DeviceID: "dev_a", Priority: prio, Status: TaskQueued, RunAfter: at, CreatedAt: at, UpdatedAt: at}
	}
	v := Voice{ID: vid, DeviceID: "dev_a", Status: StatusQueued, SampleFile: "voices/x/sample.m4a.enc", SampleExt: "m4a", SampleBytes: 100,
		SampleDurationS: 12.5, ReceiptPlatform: "ios", ReceiptOrigID: "orig", ReceiptTxID: "tx", CreatedAt: now, UpdatedAt: now, LastUsedAt: now}
	c := Consent{VoiceID: vid, DeviceID: "dev_a", Text: "Souhlasím.", SHA256: SHA256Hex("Souhlasím."), Version: "1", ConsentedAt: now}
	must(st.CreateVoice(ctx, v, c, task("t_create", KindVoiceCreate, vid, 5, now)))
	v2 := v
	v2.ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
	c2 := c
	c2.VoiceID = v2.ID
	if err := st.CreateVoice(ctx, v2, c2, task("t_create2", KindVoiceCreate, v2.ID, 5, now)); !errors.Is(err, ErrVoiceExists) {
		t.Fatalf("one voice per device: %v", err)
	}
	got, err := st.GetVoice(ctx, vid)
	must(err)
	if got.DeviceID != "dev_a" || got.SampleDurationS != 12.5 || got.ReceiptOrigID != "orig" || !got.CreatedAt.Equal(now) {
		t.Fatalf("%+v", got)
	}
	if av, err := st.ActiveVoiceByDevice(ctx, "dev_a"); err != nil || av == nil || av.ID != vid {
		t.Fatal(av, err)
	}
	if av, err := st.ActiveVoiceByDevice(ctx, "dev_b"); err != nil || av != nil {
		t.Fatal(av, err)
	}
	if n, err := st.ReceiptDevices(ctx, "ios", "orig", "dev_b"); err != nil || n != 1 {
		t.Fatal(n, err)
	}
	if n, _ := st.ReceiptDevices(ctx, "ios", "orig", "dev_a"); n != 0 {
		t.Fatal("own device does not count")
	}

	// queue: priority, then age; leases
	if n, _ := st.PendingTasks(ctx, now); n != 1 {
		t.Fatal(n)
	}
	cl, err := st.ClaimTask(ctx, "w1", now, now.Add(10*time.Minute))
	must(err)
	if cl == nil || cl.ID != "t_create" || cl.Attempts != 1 || cl.Status != TaskRunning {
		t.Fatalf("%+v", cl)
	}
	if cl2, _ := st.ClaimTask(ctx, "w2", now, now.Add(10*time.Minute)); cl2 != nil {
		t.Fatal("held task")
	}
	if err := st.HeartbeatTask(ctx, "t_create", "w2", now, now); !errors.Is(err, ErrLeaseLost) {
		t.Fatal(err)
	}
	must(st.HeartbeatTask(ctx, "t_create", "w1", now, now.Add(20*time.Minute)))
	must(st.FinishTask(ctx, "t_create", "w1", TaskQueued, "engine down", now.Add(time.Minute), now))
	if n, _ := st.PendingTasks(ctx, now); n != 0 {
		t.Fatal("retry waits")
	}
	cl, _ = st.ClaimTask(ctx, "w1", now.Add(time.Minute), now.Add(time.Hour))
	if cl == nil || cl.Attempts != 2 || cl.Error != "engine down" {
		t.Fatalf("%+v", cl)
	}
	// an expired lease is reclaimable
	cl, _ = st.ClaimTask(ctx, "w9", now.Add(2*time.Hour), now.Add(3*time.Hour))
	if cl == nil || cl.Worker != "w9" || cl.Attempts != 3 {
		t.Fatalf("reclaim %+v", cl)
	}
	if err := st.FinishTask(ctx, "t_create", "w1", TaskDone, "", now, now); !errors.Is(err, ErrLeaseLost) {
		t.Fatal(err)
	}
	must(st.FinishTask(ctx, "t_create", "w9", TaskDone, "", now, now))
	must(st.SetVoiceStatus(ctx, vid, StatusReady, "", now))

	// lines and quota
	lt := task("t_lines", KindLines, vid, 0, now.Add(time.Second))
	lt.Lang, lt.IdemKey = "cs", "idem1"
	lt.Lines = []TaskLine{{Key: "k1", Text: "Ahoj.", Hash: strings.Repeat("a", 64)}, {Key: "k2", Text: "Čau.", Hash: strings.Repeat("b", 64)}}
	must(st.CreateTask(ctx, lt))
	ot, err := st.OpenLineTask(ctx, vid, "idem1")
	must(err)
	if ot == nil || ot.ID != "t_lines" || len(ot.Lines) != 2 || ot.Lines[1].Text != "Čau." || ot.Lang != "cs" {
		t.Fatalf("%+v", ot)
	}
	if ot, _ := st.OpenLineTask(ctx, vid, "other"); ot != nil {
		t.Fatal(ot)
	}
	must(st.PutLine(ctx, Line{VoiceID: vid, Hash: strings.Repeat("a", 64), Lang: "cs", File: "f", Bytes: 10, DurationS: 1.5, CreatedAt: now}))
	must(st.PutLine(ctx, Line{VoiceID: vid, Hash: strings.Repeat("a", 64), Lang: "cs", File: "f2", Bytes: 11, DurationS: 1.5, CreatedAt: now}))
	ls, err := st.Lines(ctx, vid, []string{strings.Repeat("a", 64), strings.Repeat("b", 64)})
	must(err)
	if len(ls) != 1 || ls[strings.Repeat("a", 64)].File != "f2" || ls[strings.Repeat("a", 64)].DurationS != 1.5 {
		t.Fatalf("%+v", ls)
	}
	if u, ok, err := st.AddQuota(ctx, "dev_a", "2026-11-11", 3, 5); err != nil || !ok || u != 3 {
		t.Fatal(u, ok, err)
	}
	if u, ok, _ := st.AddQuota(ctx, "dev_a", "2026-11-11", 3, 5); ok || u != 3 {
		t.Fatal(u, ok)
	}
	if u, ok, _ := st.AddQuota(ctx, "dev_a", "2026-11-11", 2, 5); !ok || u != 5 {
		t.Fatal(u, ok)
	}
	if u, ok, _ := st.AddQuota(ctx, "dev_a", "2026-11-11", 0, 5); !ok || u != 5 {
		t.Fatal(u, ok)
	}
	if u, ok, _ := st.AddQuota(ctx, "dev_a", "2026-11-12", 6, 5); ok || u != 0 {
		t.Fatal(u, ok)
	}

	// delete: detach, cancel open tasks, drop lines, close consent, queue the AiStack delete
	cl, _ = st.ClaimTask(ctx, "w1", now.Add(time.Minute), now.Add(time.Hour))
	if cl == nil || cl.ID != "t_lines" {
		t.Fatalf("%+v", cl)
	}
	must(st.BeginDeleteVoice(ctx, vid, "user", now.Add(time.Hour), task("t_del", KindVoiceDelete, vid, 10, now.Add(time.Hour))))
	if err := st.BeginDeleteVoice(ctx, vid, "user", now, task("t_del2", KindVoiceDelete, vid, 10, now)); !errors.Is(err, ErrNotFound) {
		t.Fatal("twice", err)
	}
	if err := st.HeartbeatTask(ctx, "t_lines", "w1", now, now.Add(time.Hour)); !errors.Is(err, ErrLeaseLost) {
		t.Fatal("cancelled task", err)
	}
	if tk, _ := st.GetTask(ctx, "t_lines"); tk.Status != TaskCancelled || tk.FinishedAt == nil {
		t.Fatalf("%+v", tk)
	}
	if err := st.PutLine(ctx, Line{VoiceID: vid, Hash: strings.Repeat("b", 64), Lang: "cs", File: "f", Bytes: 1, DurationS: 1, CreatedAt: now}); !errors.Is(err, ErrNotFound) {
		t.Fatal("no lines for a deleting voice", err)
	}
	if ls, _ := st.Lines(ctx, vid, []string{strings.Repeat("a", 64)}); len(ls) != 0 {
		t.Fatal(ls)
	}
	if err := st.SetVoiceStatus(ctx, vid, StatusReady, "", now); !errors.Is(err, ErrNotFound) {
		t.Fatal(err)
	}
	got, _ = st.GetVoice(ctx, vid)
	if got.Status != StatusDeleting || got.DeviceID != "" || got.SampleFile != "" {
		t.Fatalf("%+v", got)
	}
	if av, _ := st.ActiveVoiceByDevice(ctx, "dev_a"); av != nil {
		t.Fatal(av)
	}
	cs, err := st.GetConsent(ctx, vid)
	must(err)
	if cs.DeletedAt == nil || cs.DeleteReason != "user" || cs.Text != "Souhlasím." {
		t.Fatalf("%+v", cs)
	}
	must(st.CreateVoice(ctx, v2, c2, task("t_create2", KindVoiceCreate, v2.ID, 5, now)))
	cl, _ = st.ClaimTask(ctx, "w1", now.Add(2*time.Hour), now.Add(3*time.Hour))
	if cl == nil || cl.ID != "t_del" {
		t.Fatalf("delete has priority: %+v", cl)
	}
	must(st.FinishTask(ctx, "t_del", "w1", TaskDone, "", now, now.Add(2*time.Hour)))
	must(st.FinishDeleteVoice(ctx, vid))
	if _, err := st.GetVoice(ctx, vid); !errors.Is(err, ErrNotFound) {
		t.Fatal(err)
	}

	// retention
	must(st.TouchVoice(ctx, v2.ID, now.Add(48*time.Hour)))
	if ids, _ := st.StaleVoices(ctx, now.Add(24*time.Hour)); len(ids) != 0 {
		t.Fatal(ids)
	}
	if ids, _ := st.StaleVoices(ctx, now.Add(72*time.Hour)); len(ids) != 1 || ids[0] != v2.ID {
		t.Fatal(ids)
	}
	if ids, _ := st.StaleDevices(ctx, now.Add(72*time.Hour)); len(ids) != 1 || ids[0] != "dev_b" {
		t.Fatalf("dev_a has a voice: %v", ids)
	}
	must(st.Cleanup(ctx, now.Add(2*time.Hour), now.Add(3*time.Hour), "2026-11-12"))
	if _, err := st.GetConsent(ctx, vid); !errors.Is(err, ErrNotFound) {
		t.Fatal("consent dropped after retention", err)
	}
	if _, err := st.GetConsent(ctx, v2.ID); err != nil {
		t.Fatal("live consent kept", err)
	}
	if _, err := st.GetTask(ctx, "t_del"); !errors.Is(err, ErrNotFound) {
		t.Fatal("old finished task dropped", err)
	}
	if _, err := st.GetTask(ctx, "t_create2"); err != nil {
		t.Fatal("open task kept", err)
	}
	if u, _, _ := st.AddQuota(ctx, "dev_a", "2026-11-11", 0, 5); u != 0 {
		t.Fatal("old quota rows dropped", u)
	}
	must(st.DeleteDevice(ctx, "dev_a"))
	got, _ = st.GetVoice(ctx, v2.ID)
	if got.DeviceID != "" {
		t.Fatal("voice detached from a deleted device")
	}
}

func TestMemStoreContract(t *testing.T) { storeContract(t, NewMemStore()) }

func TestPGStoreContract(t *testing.T) {
	base := os.Getenv("WEBTOON_TEST_DATABASE_URL")
	if base == "" {
		t.Skip("WEBTOON_TEST_DATABASE_URL not set")
	}
	ctx := context.Background()
	admin, err := pgx.Connect(ctx, base)
	if err != nil {
		t.Fatal(err)
	}
	var b [4]byte
	rand.Read(b[:]) //nolint:errcheck
	name := "webtoon_voice_test_" + hex.EncodeToString(b[:])
	if _, err := admin.Exec(ctx, "CREATE DATABASE "+name); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		admin.Exec(context.Background(), "DROP DATABASE IF EXISTS "+name+" WITH (FORCE)") //nolint:errcheck
		admin.Close(context.Background())                                                 //nolint:errcheck
	})
	u, err := url.Parse(base)
	if err != nil {
		t.Fatal(err)
	}
	u.Path = "/" + name
	dsn := u.String()
	if err := db.Migrate(dsn); err != nil {
		t.Fatal(err)
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	storeContract(t, NewPGStore(pool))
}
