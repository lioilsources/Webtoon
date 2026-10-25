package pack

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"slices"
	"time"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/episodejson"
)

// Fields of GET /episodes/{id} that a pack leaves out (PACK_FORMAT.md).

// stripPanel clears the panel fields a pack leaves out: seed, identity_score, error, video_error,
// estimate_seconds (all omitempty in the shared shape).
func stripPanel(p episodejson.Panel) episodejson.Panel {
	p.Seed, p.IdentityScore, p.Error, p.VideoError, p.EstimateSeconds = 0, nil, "", "", 0
	return p
}

type fileKind int

const (
	kindConvert fileKind = iota // PNG panel → WebP q85, same size
	kindCopy                    // animated WebP loop, as is
	kindCover                   // p00 of the first episode → 416×608 WebP
)

// File is one media entry of a zip: Path inside the zip, Src under MEDIA_DIR.
type File struct {
	Path string
	Src  string
	Kind fileKind
}

// Part is one zip to write: its manifest and media, in zip order.
type Part struct {
	Name     string // "" when the pack is a single zip
	Manifest Manifest
	Files    []File
	Stories  []Story
	Panels   int
	Loops    int
	Extra    map[string][]byte // more JSON next to pack.json (gamebook.json), deflated
}

// panelPath / loopPath / coverPath are the paths inside the zip (relative, as pack.json needs them).
func panelPath(episodeID string, idx int32) string {
	return fmt.Sprintf("media/%s/p%02d.webp", episodeID, idx)
}

func loopPath(episodeID string, idx int32) string {
	return fmt.Sprintf("media/%s/p%02d_loop.webp", episodeID, idx)
}

func coverPath(storyID string) string { return "covers/" + storyID + ".webp" }

// hasLoop mirrors episodejson.PanelJSON: video_url exists only for a ready loop of an animated panel.
func hasLoop(p dbq.Panel) bool { return p.Animate && p.VideoStatus == "ready" && p.VideoPath != "" }

// SplitParts chunks stories into parts of rules part_size (names a, b, c…). Up to that many stories, or
// when single is set (the starter), everything goes into one unnamed part.
func SplitParts(stories []Story, single bool) [][]Story {
	size := rule().PartSize
	if single || len(stories) <= size {
		return [][]Story{stories}
	}
	var out [][]Story
	for i := 0; i < len(stories); i += size {
		out = append(out, stories[i:min(i+size, len(stories))])
	}
	return out
}

func partName(i, n int, always bool) string {
	if n == 1 && !always {
		return ""
	}
	return string(rune('a' + i))
}

// Plan lays out the zips of a pack: stories are already filtered (Filter). Media sources are
// resolved against mediaDir; nothing is read from disk here.
func Plan(opts Options, stories []Story) ([]Part, error) {
	if !packIDRe.MatchString(opts.ID) {
		return nil, fmt.Errorf("pack id %q: use [a-z0-9-]", opts.ID)
	}
	if opts.Title == "" {
		return nil, fmt.Errorf("pack title is empty")
	}
	if opts.Version < 1 {
		return nil, fmt.Errorf("pack version must be ≥ 1")
	}
	if len(stories) == 0 {
		return nil, fmt.Errorf("no story to export")
	}
	now := opts.Now
	if now.IsZero() {
		now = time.Now()
	}
	chunks := SplitParts(stories, opts.Starter != "" || opts.Gamebook != nil)
	parts := make([]Part, 0, len(chunks))
	for i, chunk := range chunks {
		// Catalog parts are always named (a, b, …): the release asset name carries the part.
		p, err := planPart(opts, partName(i, len(chunks), opts.OutDir != "" && opts.Gamebook == nil), chunk, now)
		if err != nil {
			return nil, err
		}
		parts = append(parts, p)
	}
	return parts, nil
}

func planPart(opts Options, name string, stories []Story, now time.Time) (Part, error) {
	part := Part{Name: name, Stories: stories, Manifest: Manifest{
		Schema: Schema, ID: opts.ID, Title: opts.Title, Version: opts.Version, Part: name,
		GeneratedAt: now.UTC().Format(time.RFC3339),
		Worlds:      []WorldJSON{}, Stories: []StoryJSON{}, Episodes: []map[string]any{},
	}}
	worldsSeen := map[string]bool{}
	var media []File
	for _, s := range stories {
		if len(s.Episodes) == 0 {
			return part, fmt.Errorf("story %s has no episode (call Filter first)", s.Campaign.ID)
		}
		if !worldsSeen[s.World.ID] {
			worldsSeen[s.World.ID] = true
			w := s.World
			part.Manifest.Worlds = append(part.Manifest.Worlds, WorldJSON{ID: w.ID, Title: w.Title, Synopsis: w.Synopsis,
				Tone: w.Tone, Audience: w.Audience, Language: w.Language, StyleID: w.StyleID, Type: s.Type})
		}
		sj := StoryJSON{ID: s.Campaign.ID, WorldID: s.World.ID, Title: s.Campaign.Title, Type: s.Type,
			TitleI18n: json.RawMessage("{}"), Episodes: []string{}, Cover: coverPath(s.Campaign.ID)}
		var langs []string
		for i, e := range s.Episodes {
			if !Exportable(e) {
				return part, fmt.Errorf("episode %s is not exportable (call Filter first)", e.Row.ID)
			}
			ej, files, loops, err := episodeEntry(opts.MediaDir, s.World.Language, e)
			if err != nil {
				return part, err
			}
			part.Manifest.Episodes = append(part.Manifest.Episodes, ej)
			media = append(media, files...)
			part.Panels += len(e.Panels)
			part.Loops += loops
			sj.Episodes = append(sj.Episodes, e.Row.ID)
			epLangs := ej["languages"].([]string)
			if i == 0 {
				langs = slices.Clone(epLangs)
				// A campaign has no title_i18n of its own; when it carries the first episode's
				// title (the usual case) that episode's translations apply.
				if e.Row.Title == s.Campaign.Title {
					sj.TitleI18n = episodejson.RawOr(e.Row.TitleI18n, "{}")
				}
			} else {
				langs = slices.DeleteFunc(langs, func(l string) bool { return !slices.Contains(epLangs, l) })
			}
		}
		// The source language is always readable; translations count only when every episode has them.
		src, _ := part.Manifest.Episodes[len(part.Manifest.Episodes)-len(s.Episodes)]["source_language"].(string)
		sj.Languages = append([]string{src}, slices.DeleteFunc(langs, func(l string) bool { return l == src })...)
		part.Manifest.Stories = append(part.Manifest.Stories, sj)
		p0 := s.Episodes[0].Panels[0]
		part.Files = append(part.Files, File{Path: sj.Cover, Src: filepath.Join(opts.MediaDir, filepath.FromSlash(p0.ImagePath)), Kind: kindCover})
	}
	part.Files = append(part.Files, media...)
	return part, nil
}

// episodeEntry serialises one episode exactly like the API, with image/video URLs pointing into
// the zip and the pack-dropped fields removed. It also lists the media files the episode needs.
func episodeEntry(mediaDir, worldLang string, e Episode) (map[string]any, []File, int, error) {
	urls := map[string]string{}
	var files []File
	loops := 0
	for _, p := range e.Panels {
		urls[p.ImagePath] = panelPath(e.Row.ID, p.Idx)
		files = append(files, File{Path: panelPath(e.Row.ID, p.Idx), Src: filepath.Join(mediaDir, filepath.FromSlash(p.ImagePath)), Kind: kindConvert})
		if hasLoop(p) {
			urls[p.VideoPath] = loopPath(e.Row.ID, p.Idx)
			files = append(files, File{Path: loopPath(e.Row.ID, p.Idx), Src: filepath.Join(mediaDir, filepath.FromSlash(p.VideoPath)), Kind: kindCopy})
			loops++
		}
	}
	var missing []string
	ej := episodejson.EpisodeJSON(e.Row, e.Panels, worldLang, func(rel string) string {
		u, ok := urls[rel]
		if !ok {
			missing = append(missing, rel)
		}
		return u
	})
	if len(missing) > 0 {
		return nil, nil, 0, fmt.Errorf("episode %s: media %v not planned", e.Row.ID, missing)
	}
	for _, k := range rule().DroppedEpisodeFields {
		delete(ej, k)
	}
	panels := ej["panels"].([]episodejson.Panel)
	for i := range panels {
		panels[i] = stripPanel(panels[i])
	}
	ej["panels"] = panels
	return ej, files, loops, nil
}
