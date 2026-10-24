package pack

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

// ResolveNames fills the catalog-mode names from rules naming: with Type and N the pack id, product id (paid
// packs) and title; the release tag always (pack-<id>-v<version> style for a hand-named pack). Explicit values win.
func (o *Options) ResolveNames(r Rules) error {
	if o.Type != "" {
		if _, ok := r.Type(o.Type); !ok {
			return fmt.Errorf("unknown pack type %q (rules/base/pack.yaml types)", o.Type)
		}
	}
	vars := o.nameVars("")
	if o.N > 0 {
		if o.Type == "" {
			return errors.New("-n needs a pack type (-type, or worlds of one type)")
		}
		if o.ID == "" {
			o.ID = Fill(r.Naming.PackID, vars)
		}
		if o.ProductID == "" && !o.Free {
			o.ProductID = Fill(r.Naming.ProductID, vars)
		}
		if o.Title == "" {
			if t, ok := r.Type(o.Type); ok && t.TitleI18n["cs"] != "" {
				o.Title = fmt.Sprintf("%s %d", t.TitleI18n["cs"], o.N)
			}
		}
	}
	if o.ReleaseTag == "" {
		if o.N > 0 {
			o.ReleaseTag = Fill(r.Naming.ReleaseTag, o.nameVars(""))
		} else {
			o.ReleaseTag = fmt.Sprintf("pack-%s-v%d", o.ID, o.Version)
		}
	}
	if !releaseTagRe.MatchString(o.ReleaseTag) {
		// tags are free-form on GitHub, but the app puts them into a URL: keep them plain
		return fmt.Errorf("release tag %q: use [a-z0-9.-]", o.ReleaseTag)
	}
	return nil
}

var releaseTagRe = regexp.MustCompile(`^[a-z0-9.-]+$`)

func (o Options) nameVars(part string) map[string]string {
	return map[string]string{"type": o.Type, "n": strconv.Itoa(o.N), "version": strconv.Itoa(o.Version),
		"part": part, "id": o.ID}
}

// AssetName is the release asset of one part: rules naming.asset for a numbered pack, else <id>-<part>.zip.
func (o Options) AssetName(part string) string {
	if o.N > 0 && o.Type != "" {
		return Fill(rule().Naming.Asset, o.nameVars(part))
	}
	if part == "" {
		return o.ID + ".zip"
	}
	return o.ID + "-" + part + ".zip"
}

// TitleI18n of a numbered pack: "<type title> <n>" in every language of the type.
func (o Options) TitleI18n(r Rules) map[string]string {
	t, ok := r.Type(o.Type)
	if !ok || o.N == 0 {
		return nil
	}
	out := map[string]string{}
	for l, title := range t.TitleI18n {
		out[l] = fmt.Sprintf("%s %d", title, o.N)
	}
	return out
}

// WorldType is the pack type of a world: the profile of its world.json in the repo (data/stories/<id without
// w_>/world.json, key `profile`, via type_from_profile), else its audience via type_from_audience. root is the
// repository root (RepoRoot); a world without a world.json there falls back to its audience.
func WorldType(w dbq.World, root string, r Rules) (string, error) {
	if root != "" {
		path := filepath.Join(root, "data", "stories", strings.TrimPrefix(w.ID, "w_"), "world.json")
		if raw, err := os.ReadFile(path); err == nil {
			var wj struct {
				Profile string `json:"profile"`
				Free    bool   `json:"free"`
			}
			if err := json.Unmarshal(raw, &wj); err != nil {
				return "", fmt.Errorf("%s: %w", path, err)
			}
			if wj.Free {
				return "", fmt.Errorf("world %s is a free world (never published)", w.ID)
			}
			if wj.Profile != "" {
				t, ok := r.TypeFromProfile[wj.Profile]
				if !ok {
					return "", fmt.Errorf("world %s: profile %s has no pack type (type_from_profile)", w.ID, wj.Profile)
				}
				return t, nil
			}
		}
	}
	t, ok := r.TypeFromAudience[w.Audience]
	if !ok {
		return "", fmt.Errorf("world %s: audience %q has no pack type (type_from_audience); give -type", w.ID, w.Audience)
	}
	return t, nil
}

// AssignTypes sets Story.Type: a pick's type stays, else -type, else WorldType. In catalog mode every story must
// end up with one type, which becomes the pack's type when -type is not given; notes say where -type overrides a
// world's own type. Starter mode tolerates unknown and mixed types.
func AssignTypes(stories []Story, opts *Options, root string, r Rules) (notes []string, err error) {
	catalog := opts.OutDir != ""
	for i := range stories {
		s := &stories[i]
		own, werr := WorldType(s.World, root, r)
		switch {
		case s.Type != "":
		case opts.Type != "":
			s.Type = opts.Type
			if werr == nil && own != opts.Type {
				notes = append(notes, fmt.Sprintf("story %s: world %s is %s, exported as -type %s", s.Campaign.ID, s.World.ID, own, opts.Type))
			}
		case werr != nil:
			if catalog {
				return notes, werr
			}
		default:
			s.Type = own
		}
	}
	if !catalog || opts.Type != "" {
		return notes, nil
	}
	for _, s := range stories {
		if opts.Type == "" {
			opts.Type = s.Type
		} else if s.Type != opts.Type {
			return notes, fmt.Errorf("the selected worlds are of different types (%s, %s); a pack has one type: give -type", opts.Type, s.Type)
		}
	}
	return notes, nil
}

// GhCommand is the `gh release create` that uploads the zips of a catalog export (printed, never run).
func GhCommand(repo, tag, title string, files []string, notes string) string {
	q := func(s string) string { return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'" }
	parts := []string{"gh", "release", "create", q(tag)}
	for _, f := range files {
		parts = append(parts, q(f))
	}
	parts = append(parts, "--repo", q(repo), "--title", q(title), "--notes", q(notes))
	return strings.Join(parts, " ")
}
