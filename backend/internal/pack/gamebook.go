package pack

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

// GamebookSchema is the gamebook.json schema (docs/gamebook.md); GamebookFile its name in the zip.
const (
	GamebookSchema = 1
	GamebookFile   = "gamebook.json"
)

// Graph is data/gamebooks/<id>/graph.yaml: the outline every node of the gamebook was drawn from (m0/gamebook.py).
// Each node is its own story in world w_gb_<id>_<node>.
type Graph struct {
	ID         string            `yaml:"id"`
	Title      string            `yaml:"title"`
	TitleI18n  map[string]string `yaml:"title_i18n"`
	World      string            `yaml:"world"`
	Audience   string            `yaml:"audience"`
	Type       string            `yaml:"type"`
	Start      string            `yaml:"start"`
	Characters []string          `yaml:"characters"`
	Locations  []GraphLocation   `yaml:"locations"`
	Nodes      map[string]Node   `yaml:"nodes"`
	order      []string          // node ids in file order
}

type GraphLocation struct {
	ID          string `yaml:"id" json:"id"`
	Name        string `yaml:"name" json:"name"`
	Description string `yaml:"description" json:"description,omitempty"`
}

// Node is one node of the graph; Beats / Panels / Location only steer the storyboard and are not exported.
type Node struct {
	Title   string   `yaml:"title"`
	Next    string   `yaml:"next"`
	Choices []Edge   `yaml:"choices"`
	Sets    []string `yaml:"sets"`
	Ending  string   `yaml:"ending"`
	RetryTo string   `yaml:"retry_to"`
}

// Edge is one choice: If is a flag expression ("a", "a or b", "a and b", "not a").
type Edge struct {
	ID       string            `yaml:"id" json:"id"`
	Text     string            `yaml:"text" json:"text"`
	TextI18n map[string]string `yaml:"text_i18n" json:"text_i18n,omitempty"`
	To       string            `yaml:"to" json:"to"`
	If       string            `yaml:"if" json:"if,omitempty"`
}

// ReadGraph parses and checks graph.yaml: every edge, next and retry_to names a node, every node is reachable from
// start, a node ends, has choices or has next.
func ReadGraph(path string) (*Graph, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	g := &Graph{}
	if err := yaml.Unmarshal(raw, g); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	var doc struct {
		Nodes yaml.Node `yaml:"nodes"`
	}
	if err := yaml.Unmarshal(raw, &doc); err == nil {
		for i := 0; i+1 < len(doc.Nodes.Content); i += 2 {
			g.order = append(g.order, doc.Nodes.Content[i].Value)
		}
	}
	if g.ID == "" || !packIDRe.MatchString(g.ID) {
		return nil, fmt.Errorf("%s: gamebook id %q: use [a-z0-9-]", path, g.ID)
	}
	if _, ok := g.Nodes[g.Start]; !ok {
		return nil, fmt.Errorf("%s: start %q is not a node", path, g.Start)
	}
	for _, id := range g.order {
		n := g.Nodes[id]
		targets := []string{n.Next, n.RetryTo}
		for _, e := range n.Choices {
			if e.To == "" {
				return nil, fmt.Errorf("%s: node %s choice %s has no target", path, id, e.ID)
			}
			targets = append(targets, e.To)
		}
		for _, t := range targets {
			if _, ok := g.Nodes[t]; t != "" && !ok {
				return nil, fmt.Errorf("%s: node %s points to unknown node %q", path, id, t)
			}
		}
		if n.Ending == "" && n.Next == "" && len(n.Choices) == 0 {
			return nil, fmt.Errorf("%s: node %s has no choices, next or ending", path, id)
		}
	}
	seen := map[string]bool{}
	for todo := []string{g.Start}; len(todo) > 0; {
		id := todo[len(todo)-1]
		todo = todo[:len(todo)-1]
		if seen[id] {
			continue
		}
		seen[id] = true
		n := g.Nodes[id]
		for _, e := range n.Choices {
			todo = append(todo, e.To)
		}
		if n.Next != "" {
			todo = append(todo, n.Next)
		}
	}
	for _, id := range g.order {
		if !seen[id] {
			return nil, fmt.Errorf("%s: node %s is unreachable from %s", path, id, g.Start)
		}
	}
	return g, nil
}

// NodeWorld is the world a node was imported as (m0/gamebook.py story id gb_<id>_<node>).
func (g *Graph) NodeWorld(node string) string { return "w_gb_" + g.ID + "_" + node }

// Selection is every node's world.
func (g *Graph) Selection() Selection {
	var s Selection
	for _, id := range g.order {
		s.Worlds = append(s.Worlds, g.NodeWorld(id))
	}
	return s
}

// GamebookJSON is gamebook.json inside the zip, next to pack.json (whose stories are the nodes).
type GamebookJSON struct {
	Schema    int                     `json:"schema"`
	ID        string                  `json:"id"`
	Title     string                  `json:"title"`
	TitleI18n map[string]string       `json:"title_i18n"`
	Start     string                  `json:"start"`
	Order     []string                `json:"order"`
	Nodes     map[string]GamebookNode `json:"nodes"`
	Flags     []string                `json:"flags"`
	Endings   int                     `json:"endings"`
	Lore      Lore                    `json:"lore"`
}

type GamebookNode struct {
	Story   string   `json:"story"`   // pack.json story (campaign) id
	Episode string   `json:"episode"` // its one episode
	Title   string   `json:"title"`
	Next    string   `json:"next,omitempty"`
	Choices []Edge   `json:"choices"`
	Sets    []string `json:"sets"`
	Ending  string   `json:"ending,omitempty"` // good | retry
	RetryTo string   `json:"retry_to,omitempty"`
}

// Lore is what the editor kit offers to write with: speakers and places of the book.
type Lore struct {
	Characters []LoreCharacter `json:"characters"`
	Locations  []GraphLocation `json:"locations"`
	Rules      []string        `json:"rules"`
}

type LoreCharacter struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
}

// buildGamebook maps the nodes onto the planned stories: each node world must hold exactly one story of one episode.
func buildGamebook(ctx context.Context, q *dbq.Queries, g *Graph, part Part) (*GamebookJSON, error) {
	byWorld := map[string]StoryJSON{}
	for _, s := range part.Manifest.Stories {
		if _, dup := byWorld[s.WorldID]; dup {
			return nil, fmt.Errorf("world %s has more than one story; a gamebook node is one story", s.WorldID)
		}
		byWorld[s.WorldID] = s
	}
	gb := &GamebookJSON{Schema: GamebookSchema, ID: g.ID, Title: g.Title, TitleI18n: g.TitleI18n, Start: g.Start,
		Order: g.order, Nodes: map[string]GamebookNode{}, Flags: []string{}}
	if gb.TitleI18n == nil {
		gb.TitleI18n = map[string]string{}
	}
	for _, id := range g.order {
		n := g.Nodes[id]
		s, ok := byWorld[g.NodeWorld(id)]
		if !ok {
			return nil, fmt.Errorf("node %s: world %s has no exportable story (render and import it first)", id, g.NodeWorld(id))
		}
		if len(s.Episodes) != 1 {
			return nil, fmt.Errorf("node %s: story %s has %d episodes, want 1", id, s.ID, len(s.Episodes))
		}
		choices, sets := n.Choices, n.Sets
		if choices == nil {
			choices = []Edge{}
		}
		if sets == nil {
			sets = []string{}
		}
		for _, f := range sets {
			if !slices.Contains(gb.Flags, f) {
				gb.Flags = append(gb.Flags, f)
			}
		}
		if n.Ending == "good" {
			gb.Endings++
		}
		gb.Nodes[id] = GamebookNode{Story: s.ID, Episode: s.Episodes[0], Title: n.Title, Next: n.Next, Choices: choices,
			Sets: sets, Ending: n.Ending, RetryTo: n.RetryTo}
	}
	gb.Lore = Lore{Characters: []LoreCharacter{}, Locations: []GraphLocation{}, Rules: []string{}}
	seenLoc := map[string]bool{}
	for _, id := range g.order {
		w := g.NodeWorld(id)
		chars, err := q.ListCharacters(ctx, w)
		if err != nil {
			return nil, err
		}
		for _, c := range chars {
			if !slices.ContainsFunc(gb.Lore.Characters, func(x LoreCharacter) bool { return x.ID == c.ID }) {
				gb.Lore.Characters = append(gb.Lore.Characters, LoreCharacter{ID: c.ID, Name: c.Name, Description: c.Description})
			}
		}
		locs, err := q.ListLocations(ctx, w)
		if err != nil {
			return nil, err
		}
		for _, l := range locs {
			if !seenLoc[l.ID] {
				seenLoc[l.ID] = true
				gb.Lore.Locations = append(gb.Lore.Locations, GraphLocation{ID: l.ID, Name: l.Name, Description: l.Description})
			}
		}
		if len(gb.Lore.Rules) == 0 {
			if world, err := q.GetWorld(ctx, w); err == nil {
				var bible struct {
					Rules []string `json:"rules"`
				}
				if json.Unmarshal(world.Bible, &bible) == nil && bible.Rules != nil {
					gb.Lore.Rules = bible.Rules
				}
			}
		}
	}
	return gb, nil
}

// CatalogGamebook is one entry of catalog.json gamebooks[] (schema 2): one zip with pack.json + gamebook.json.
type CatalogGamebook struct {
	ID           string            `json:"id"`
	ProductID    string            `json:"product_id"`
	KitProductID string            `json:"kit_product_id"`
	Type         string            `json:"type"`
	Title        string            `json:"title"`
	TitleI18n    map[string]string `json:"title_i18n"`
	Audience     string            `json:"audience"`
	Languages    []string          `json:"languages"`
	Cover        string            `json:"cover,omitempty"`
	Free         bool              `json:"free"`
	Status       string            `json:"status"` // ready (planned = announced, no zip)
	Version      int               `json:"version"`
	Nodes        int               `json:"nodes"`
	Endings      int               `json:"endings"`
	Bytes        int64             `json:"bytes"`
	Graph        string            `json:"graph"` // the graph's file inside the zip
	Lore         string            `json:"lore"`  // where the editor kit's lore is (same file)
	Parts        []CatalogPart     `json:"parts"`
}

// MergeGamebook replaces (or appends) the gamebook with gb.ID, refreshes the rules parts like Merge and bumps the
// version. Its nodes never become library stories (catalog stories[]): they are read through the gamebook only.
func (c *Catalog) MergeGamebook(gb CatalogGamebook, now time.Time, pagesURL string) error {
	raw, err := json.Marshal(gb)
	if err != nil {
		return err
	}
	i := slices.IndexFunc(c.Gamebooks, func(x json.RawMessage) bool {
		var head struct {
			ID string `json:"id"`
		}
		return json.Unmarshal(x, &head) == nil && head.ID == gb.ID
	})
	if i >= 0 {
		c.Gamebooks[i] = raw
	} else {
		c.Gamebooks = append(c.Gamebooks, raw)
	}
	c.ApplyRules(rule(), pagesURL)
	c.Touch(now)
	return nil
}

// gamebookNames fills what a gamebook export leaves out: id gamebook-<id>, the graph's title, products from rules
// naming (gamebook_product, kit_product) and release tag gamebook-<id>-v<version>.
func gamebookNames(o *Options, r Rules) {
	g := o.Gamebook
	vars := map[string]string{"id": g.ID}
	if o.ID == "" {
		o.ID = "gamebook-" + g.ID
	}
	if o.Title == "" {
		o.Title = g.Title
	}
	if o.ProductID == "" && !o.Free {
		o.ProductID = Fill(r.Naming.GamebookProduct, vars)
	}
	if o.ReleaseTag == "" {
		o.ReleaseTag = fmt.Sprintf("gamebook-%s-v%d", g.ID, o.Version)
	}
	if o.Type == "" {
		o.Type = g.Type
	}
}

// writeGamebookCatalog puts the one zip into catalog gamebooks[] and the node covers into covers/ (buildPart did).
func writeGamebookCatalog(opts Options, parts []Part, sum *Summary) error {
	path := filepath.Join(opts.OutDir, "catalog.json")
	cat, err := ReadCatalog(path)
	if err != nil {
		return err
	}
	g, p, ps := opts.Gamebook, parts[0], sum.Parts[0]
	var gb GamebookJSON
	if err := json.Unmarshal(p.Extra[GamebookFile], &gb); err != nil {
		return err
	}
	cover := ""
	if n, ok := gb.Nodes[gb.Start]; ok {
		cover = coverPath(n.Story)
	}
	r := rule()
	entry := CatalogGamebook{ID: g.ID, ProductID: opts.ProductID, KitProductID: Fill(r.Naming.KitProduct, map[string]string{"id": g.ID}),
		Type: opts.Type, Title: opts.Title, TitleI18n: gb.TitleI18n, Audience: packAudience(parts), Languages: packLanguages(parts),
		Cover: cover, Status: "ready", Version: opts.Version, Nodes: len(gb.Nodes), Endings: gb.Endings, Bytes: ps.Bytes,
		Graph: GamebookFile, Lore: GamebookFile,
		Parts: []CatalogPart{{Release: opts.ReleaseTag, Asset: filepath.Base(ps.Path), Bytes: ps.Bytes, SHA256: ps.SHA256, Stories: len(p.Manifest.Stories)}}}
	if opts.Free {
		entry.ProductID, entry.KitProductID, entry.Free = "", "", true
	}
	if err := cat.MergeGamebook(entry, opts.Now, opts.BaseURL); err != nil {
		return err
	}
	if err := WriteCatalog(path, cat); err != nil {
		return err
	}
	sum.CatalogPath, sum.CatalogVersion = path, cat.Version
	return nil
}
