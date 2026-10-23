package pack

import (
	"context"
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
	if (opts.Starter == "") == (opts.OutDir == "") {
		return nil, errors.New("give either -starter <zip> or -out <dir>")
	}
	if opts.OutDir != "" && opts.Free == (opts.ProductID != "") {
		return nil, errors.New("a catalog pack is either -free or has a -product id")
	}
	if opts.BaseURL == "" {
		opts.BaseURL = DefaultBaseURL
	}
	if opts.Now.IsZero() {
		opts.Now = time.Now()
	}
	if err := CheckCwebp(); err != nil {
		return nil, err
	}
	stories, err := Load(ctx, q, sel)
	if err != nil {
		return nil, err
	}
	stories, notes := Filter(stories)
	parts, err := Plan(opts, stories)
	if err != nil {
		return nil, err
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
	if err := writeCatalog(opts, parts, sum); err != nil {
		return nil, err
	}
	return sum, nil
}

func zipPath(opts Options, part string) string {
	if opts.Starter != "" {
		return opts.Starter
	}
	name := fmt.Sprintf("%s-v%d", opts.ID, opts.Version)
	if part != "" {
		name += "-" + part
	}
	return filepath.Join(opts.OutDir, "packs", name+".zip")
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
	n, sha, err := writeZip(tmp, part.Manifest, stageDir, part.Files, opts.Now)
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
	cp := CatalogPack{ID: opts.ID, Title: opts.Title, Free: opts.Free, ProductID: opts.ProductID, Version: opts.Version,
		Parts: []CatalogPart{}, Languages: packLanguages(parts), Audience: packAudience(parts)}
	var stories []CatalogStory
	for i, p := range parts {
		rel, err := filepath.Rel(opts.OutDir, sum.Parts[i].Path)
		if err != nil {
			return err
		}
		cp.Parts = append(cp.Parts, CatalogPart{Path: filepath.ToSlash(rel), Bytes: sum.Parts[i].Bytes, SHA256: sum.Parts[i].SHA256})
		cp.Stories += len(p.Manifest.Stories)
		for _, s := range p.Manifest.Stories {
			audience := ""
			for _, w := range p.Manifest.Worlds {
				if w.ID == s.WorldID {
					audience = w.Audience
				}
			}
			stories = append(stories, CatalogStory{ID: s.ID, PackID: opts.ID, WorldID: s.WorldID, Title: s.Title,
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
