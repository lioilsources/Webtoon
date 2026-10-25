package pack

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

// Run exports one pack: loads the selection, applies the format rules, converts media on a worker
// pool and writes the zip(s); in catalog mode it also writes covers/ and merges catalog.json.
// The database is only read.
func Run(ctx context.Context, q *dbq.Queries, opts Options, sel Selection) (*Summary, error) {
	r, err := LoadRules()
	if err != nil {
		return nil, err
	}
	if (opts.Starter == "") == (opts.OutDir == "") {
		return nil, errors.New("give either -starter <zip> or -out <dir>")
	}
	if len(sel.Picks) > 0 && opts.Starter == "" {
		return nil, errors.New("-starter-pick builds the starter: give -starter <zip>")
	}
	if opts.Gamebook != nil && opts.OutDir == "" {
		return nil, errors.New("-gamebook writes a catalog gamebook: give -out <dir>")
	}
	if opts.Now.IsZero() {
		opts.Now = time.Now()
	}
	if err := CheckCwebp(); err != nil {
		return nil, err
	}
	root, err := RepoRoot()
	if err != nil {
		return nil, err
	}
	stories, err := Load(ctx, q, sel)
	if err != nil {
		return nil, err
	}
	stories, notes := Filter(stories)
	typeNotes, err := AssignTypes(stories, &opts, root, r)
	if err != nil {
		return nil, err
	}
	notes = append(notes, typeNotes...)
	if g := opts.Gamebook; g != nil {
		gamebookNames(&opts, r)
	}
	if opts.OutDir != "" {
		if err := opts.ResolveNames(r); err != nil {
			return nil, err
		}
		if opts.ID == "" || opts.Title == "" {
			return nil, errors.New("a catalog pack needs -pack and -title, or -type and -n")
		}
		if opts.Free == (opts.ProductID != "") {
			return nil, errors.New("a catalog pack is either -free or has a -product id (-n derives it)")
		}
	}
	parts, err := Plan(opts, stories)
	if err != nil {
		return nil, err
	}
	if opts.Gamebook != nil {
		gb, err := buildGamebook(ctx, q, opts.Gamebook, parts[0])
		if err != nil {
			return nil, err
		}
		body, err := json.Marshal(gb)
		if err != nil {
			return nil, err
		}
		parts[0].Extra = map[string][]byte{GamebookFile: body}
	}
	sum := &Summary{Notes: notes}
	for i := range parts {
		path := zipPath(opts, parts[i].Name)
		if _, err := os.Stat(path); err == nil && !opts.Force {
			return nil, fmt.Errorf("%s exists; pack files are never overwritten, bump -version (or -force)", path)
		}
	}
	for i := range parts {
		ps, err := buildPart(ctx, opts, parts[i])
		if err != nil {
			return nil, err
		}
		sum.Parts = append(sum.Parts, ps)
	}
	if opts.OutDir == "" {
		return sum, nil
	}
	write := writeCatalog
	if opts.Gamebook != nil {
		write = writeGamebookCatalog
	}
	if err := write(opts, parts, sum); err != nil {
		return nil, err
	}
	sum.ReleaseTag = opts.ReleaseTag
	var files []string
	for _, p := range sum.Parts {
		files = append(files, p.Path)
	}
	sum.GhCommand = GhCommand(r.Repo, opts.ReleaseTag, fmt.Sprintf("%s v%d", opts.Title, opts.Version), files,
		fmt.Sprintf("%s v%d: %d stories in %d part(s), catalog version %d", opts.ID, opts.Version, storyCount(parts), len(parts), sum.CatalogVersion))
	return sum, nil
}

func storyCount(parts []Part) int {
	n := 0
	for _, p := range parts {
		n += len(p.Stories)
	}
	return n
}

// zipPath: the starter zip, or <out>/releases/<tag>/<asset> (uploaded with gh, never committed to the Pages repo).
func zipPath(opts Options, part string) string {
	if opts.Starter != "" {
		return opts.Starter
	}
	return filepath.Join(opts.OutDir, "releases", opts.ReleaseTag, opts.AssetName(part))
}

func buildPart(ctx context.Context, opts Options, part Part) (PartSummary, error) {
	ps := PartSummary{Part: part.Name, Path: zipPath(opts, part.Name), Stories: len(part.Stories),
		Episodes: len(part.Manifest.Episodes), Panels: part.Panels, Loops: part.Loops}
	stageDir, err := os.MkdirTemp("", "webtoon-pack-")
	if err != nil {
		return ps, err
	}
	defer os.RemoveAll(stageDir)
	if err := stage(ctx, stageDir, part.Files, opts.Workers); err != nil {
		return ps, err
	}
	tmp := ps.Path + ".tmp"
	n, sha, err := writeZip(tmp, part.Manifest, part.Extra, stageDir, part.Files, opts.Now)
	if err != nil {
		os.Remove(tmp)
		return ps, err
	}
	if err := os.Rename(tmp, ps.Path); err != nil {
		return ps, err
	}
	ps.Bytes, ps.SHA256 = n, sha
	if opts.OutDir != "" {
		// Covers next to the catalog, so the library shows them before the pack is downloaded.
		if err := os.MkdirAll(filepath.Join(opts.OutDir, "covers"), 0o755); err != nil {
			return ps, err
		}
		for _, f := range part.Files {
			if f.Kind == kindCover {
				if err := copyFile(filepath.Join(stageDir, filepath.FromSlash(f.Path)), filepath.Join(opts.OutDir, filepath.FromSlash(f.Path))); err != nil {
					return ps, err
				}
			}
		}
	}
	return ps, nil
}

func writeCatalog(opts Options, parts []Part, sum *Summary) error {
	path := filepath.Join(opts.OutDir, "catalog.json")
	cat, err := ReadCatalog(path)
	if err != nil {
		return err
	}
	cp := catalogPack(opts, parts, sum)
	var stories []CatalogStory
	for _, p := range parts {
		for _, s := range p.Manifest.Stories {
			audience := ""
			for _, w := range p.Manifest.Worlds {
				if w.ID == s.WorldID {
					audience = w.Audience
				}
			}
			stories = append(stories, CatalogStory{ID: s.ID, PackID: opts.ID, Type: s.Type, WorldID: s.WorldID, Title: s.Title,
				TitleI18n: s.TitleI18n, Cover: s.Cover, Episodes: len(s.Episodes), Audience: audience})
		}
	}
	cat.Merge(cp, stories, opts.Now, opts.BaseURL)
	if err := WriteCatalog(path, cat); err != nil {
		return err
	}
	sum.CatalogPath, sum.CatalogVersion = path, cat.Version
	return nil
}

// catalogPack is the catalog entry of an export: parts as release assets, cover + previews from the story covers.
func catalogPack(opts Options, parts []Part, sum *Summary) CatalogPack {
	r := rule()
	cp := CatalogPack{ID: opts.ID, Type: opts.Type, N: opts.N, Title: opts.Title, TitleI18n: opts.TitleI18n(r),
		Free: opts.Free, ProductID: opts.ProductID, Version: opts.Version,
		Parts: []CatalogPart{}, Languages: packLanguages(parts), Audience: packAudience(parts)}
	if opts.Free {
		cp.ProductID = ""
	}
	for i, p := range parts {
		ps := sum.Parts[i]
		cp.Parts = append(cp.Parts, CatalogPart{Part: p.Name, Release: opts.ReleaseTag, Asset: filepath.Base(ps.Path),
			Bytes: ps.Bytes, SHA256: ps.SHA256, Stories: len(p.Manifest.Stories)})
		cp.Stories += len(p.Manifest.Stories)
		cp.Bytes += ps.Bytes
		for _, s := range p.Manifest.Stories {
			if cp.Cover == "" {
				cp.Cover = s.Cover
			}
			if len(cp.Previews) < r.MaxPreviews {
				cp.Previews = append(cp.Previews, s.Cover)
			}
		}
	}
	return cp
}
