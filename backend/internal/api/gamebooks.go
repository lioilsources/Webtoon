package api

import (
	"encoding/json"
	"errors"
	"io/fs"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/pack"
)

// Gamebook graphs for Studio's graph editor (docs/gamebook.md): data/gamebooks/<id>/graph.yaml of the repo the
// backend runs from. Drawing new nodes stays the m0 pipeline (m0/gamebook.py + local_strip.sh via the Spark
// broker); the editor shows which nodes are drawn and refuses to remove them.

type gamebookSummary struct {
	ID    string `json:"id"`
	Title string `json:"title"`
	Nodes int    `json:"nodes"`
	Drawn int    `json:"drawn"`
}

type gamebookDoc struct {
	ID         string            `json:"id"`
	Graph      json.RawMessage   `json:"graph"`
	Drawn      map[string]bool   `json:"drawn"`
	Characters []gamebookName    `json:"characters"`
	Locations  []gamebookName    `json:"locations"`
	Draw       string            `json:"draw_command"` // what draws the missing nodes (run by hand, via the broker)
	Errors     map[string]string `json:"errors,omitempty"`
}

type gamebookName struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

func (s *Server) listGamebooks(w http.ResponseWriter, r *http.Request) {
	dir, err := pack.GamebooksDir()
	if err != nil {
		s.fail(w, err)
		return
	}
	paths, _ := filepath.Glob(filepath.Join(dir, "*", "graph.yaml"))
	out := []gamebookSummary{}
	for _, p := range paths {
		g, err := pack.ReadGraph(p)
		if err != nil {
			continue
		}
		drawn := s.drawnNodes(r, g)
		n := 0
		for _, ok := range drawn {
			if ok {
				n++
			}
		}
		out = append(out, gamebookSummary{ID: g.ID, Title: g.Title, Nodes: len(g.Nodes), Drawn: n})
	}
	writeJSON(w, http.StatusOK, map[string]any{"gamebooks": out})
}

func (s *Server) getGamebook(w http.ResponseWriter, r *http.Request) {
	path, err := pack.GraphPath(r.PathValue("id"))
	if err != nil {
		s.fail(w, errf(http.StatusBadRequest, err.Error()))
		return
	}
	doc, err := s.gamebookDoc(r, path)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, doc)
}

func (s *Server) putGamebook(w http.ResponseWriter, r *http.Request) {
	path, err := pack.GraphPath(r.PathValue("id"))
	if err != nil {
		s.fail(w, errf(http.StatusBadRequest, err.Error()))
		return
	}
	old, err := pack.ReadGraph(path)
	if err != nil {
		s.fail(w, notFoundOr(err))
		return
	}
	var req struct {
		Graph json.RawMessage `json:"graph"`
	}
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	var head struct {
		ID string `json:"id"`
	}
	if json.Unmarshal(req.Graph, &head) != nil || head.ID != old.ID {
		s.fail(w, errf(http.StatusBadRequest, "graph.id must stay "+old.ID))
		return
	}
	var keep []string
	for id, ok := range s.drawnNodes(r, old) {
		if ok {
			keep = append(keep, id)
		}
	}
	if _, err := pack.WriteGraphDoc(path, req.Graph, keep); err != nil {
		s.fail(w, errf(http.StatusUnprocessableEntity, err.Error()))
		return
	}
	doc, err := s.gamebookDoc(r, path)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, doc)
}

func notFoundOr(err error) error {
	if errors.Is(err, fs.ErrNotExist) {
		return errf(http.StatusNotFound, "not found")
	}
	return err
}

func (s *Server) gamebookDoc(r *http.Request, path string) (*gamebookDoc, error) {
	g, err := pack.ReadGraph(path)
	if err != nil {
		return nil, notFoundOr(err)
	}
	raw, err := pack.ReadGraphDoc(path)
	if err != nil {
		return nil, err
	}
	doc := &gamebookDoc{ID: g.ID, Graph: raw, Drawn: s.drawnNodes(r, g), Characters: []gamebookName{}, Locations: []gamebookName{},
		Draw: "python3 m0/gamebook.py write " + rel(path) + " && python3 m0/gamebook.py unify " + rel(path) +
			" && m0/local_strip.sh -I -a kids <ids of the new nodes>  # LLM and ComfyUI leases via sparkctl"}
	seen := map[string]bool{}
	addLoc := func(id, name string) {
		if id != "" && !seen[id] {
			seen[id] = true
			doc.Locations = append(doc.Locations, gamebookName{ID: id, Name: name})
		}
	}
	var world struct {
		Characters []gamebookName `json:"characters"`
		Locations  []gamebookName `json:"locations"`
	}
	root, err := pack.RepoRoot()
	if err != nil {
		return nil, err
	}
	if b, err := os.ReadFile(filepath.Join(root, "data", "stories", strings.TrimPrefix(g.World, "w_"), "world.json")); err == nil {
		_ = json.Unmarshal(b, &world)
	}
	doc.Characters = append(doc.Characters, world.Characters...)
	for _, l := range world.Locations {
		addLoc(l.ID, l.Name)
	}
	for _, l := range g.Locations {
		addLoc(l.ID, l.Name)
	}
	var extra []gamebookName // locations the LLM added while writing nodes (m0/gamebook.py unify)
	if b, err := os.ReadFile(filepath.Join(filepath.Dir(path), "locations.json")); err == nil {
		_ = json.Unmarshal(b, &extra)
	}
	for _, l := range extra {
		addLoc(l.ID, l.Name)
	}
	return doc, nil
}

// drawnNodes: a node is drawn once its world (w_gb_<id>_<node>) is imported; import comes after the whole render.
func (s *Server) drawnNodes(r *http.Request, g *pack.Graph) map[string]bool {
	out := map[string]bool{}
	for _, id := range g.GraphOrder() {
		_, err := s.store.Q.GetWorld(r.Context(), g.NodeWorld(id))
		out[id] = err == nil
	}
	return out
}

func rel(path string) string {
	i := strings.Index(path, "/data/gamebooks/")
	if i < 0 {
		return path
	}
	return path[i+1:]
}
