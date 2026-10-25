package pack

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

// GraphDoc is graph.yaml as Studio edits it: JSON with the YAML's key order kept (node order is the book's
// order), and every field kept, also the ones export ignores (beats, panels, location, premise, origin, …).

// ReadGraphDoc returns graph.yaml at path as ordered JSON.
func ReadGraphDoc(path string) (json.RawMessage, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var doc yaml.Node
	if err := yaml.Unmarshal(raw, &doc); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if len(doc.Content) == 0 {
		return nil, fmt.Errorf("%s is empty", path)
	}
	var buf bytes.Buffer
	if err := yamlToJSON(&buf, doc.Content[0]); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// WriteGraphDoc replaces graph.yaml at path with doc (ordered JSON), after checking it like an export would
// (ReadGraph) and that it still has every node of keep (nodes already drawn). The file is written atomically;
// comments of a hand-edited file do not survive (docs/gamebook.md has the format).
func WriteGraphDoc(path string, doc []byte, keep []string) (*Graph, error) {
	node, err := jsonToYAML(json.NewDecoder(bytes.NewReader(doc)))
	if err != nil {
		return nil, fmt.Errorf("graph: %w", err)
	}
	if node.Kind != yaml.MappingNode {
		return nil, errors.New("graph: want an object")
	}
	var out bytes.Buffer
	out.WriteString("# Gamebook graph, edited in Studio. Format: docs/gamebook.md\n")
	enc := yaml.NewEncoder(&out)
	enc.SetIndent(2)
	if err := enc.Encode(node); err != nil {
		return nil, err
	}
	enc.Close()
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, out.Bytes(), 0o644); err != nil {
		return nil, err
	}
	g, err := ReadGraph(tmp)
	if err == nil {
		for _, id := range keep {
			if _, ok := g.Nodes[id]; !ok {
				err = fmt.Errorf("node %s is drawn already and cannot be removed (readers' progress points at it)", id)
				break
			}
		}
	}
	if err != nil {
		os.Remove(tmp)
		return nil, errors.New(strings.ReplaceAll(err.Error(), tmp+": ", ""))
	}
	if err := os.Rename(tmp, path); err != nil {
		return nil, err
	}
	return g, nil
}

// GraphOrder is the node ids of g in file order.
func (g *Graph) GraphOrder() []string { return g.order }

// GamebooksDir is data/gamebooks under the repo.
func GamebooksDir() (string, error) {
	root, err := RepoRoot()
	if err != nil {
		return "", err
	}
	return filepath.Join(root, "data", "gamebooks"), nil
}

// GraphPath is data/gamebooks/<id>/graph.yaml under the repo.
func GraphPath(id string) (string, error) {
	if !packIDRe.MatchString(id) {
		return "", fmt.Errorf("gamebook id %q: use [a-z0-9-]", id)
	}
	dir, err := GamebooksDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, id, "graph.yaml"), nil
}

func yamlToJSON(w *bytes.Buffer, n *yaml.Node) error {
	switch n.Kind {
	case yaml.AliasNode:
		return yamlToJSON(w, n.Alias)
	case yaml.MappingNode:
		w.WriteByte('{')
		for i := 0; i+1 < len(n.Content); i += 2 {
			if i > 0 {
				w.WriteByte(',')
			}
			k, _ := json.Marshal(n.Content[i].Value)
			w.Write(k)
			w.WriteByte(':')
			if err := yamlToJSON(w, n.Content[i+1]); err != nil {
				return err
			}
		}
		w.WriteByte('}')
	case yaml.SequenceNode:
		w.WriteByte('[')
		for i, c := range n.Content {
			if i > 0 {
				w.WriteByte(',')
			}
			if err := yamlToJSON(w, c); err != nil {
				return err
			}
		}
		w.WriteByte(']')
	case yaml.ScalarNode:
		var v any
		if err := n.Decode(&v); err != nil {
			return err
		}
		b, err := json.Marshal(v)
		if err != nil {
			return err
		}
		w.Write(b)
	default:
		return fmt.Errorf("line %d: unsupported YAML node", n.Line)
	}
	return nil
}

// jsonToYAML builds a YAML node from a JSON value, keeping object key order (json.Decoder tokens).
func jsonToYAML(dec *json.Decoder) (*yaml.Node, error) {
	dec.UseNumber()
	tok, err := dec.Token()
	if err != nil {
		if err == io.EOF {
			return nil, errors.New("empty document")
		}
		return nil, err
	}
	return tokenNode(dec, tok)
}

func tokenNode(dec *json.Decoder, tok json.Token) (*yaml.Node, error) {
	switch t := tok.(type) {
	case json.Delim:
		switch t {
		case '{':
			n := &yaml.Node{Kind: yaml.MappingNode, Tag: "!!map"}
			for dec.More() {
				kt, err := dec.Token()
				if err != nil {
					return nil, err
				}
				k, ok := kt.(string)
				if !ok {
					return nil, errors.New("object key is not a string")
				}
				vt, err := dec.Token()
				if err != nil {
					return nil, err
				}
				v, err := tokenNode(dec, vt)
				if err != nil {
					return nil, err
				}
				n.Content = append(n.Content, &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Value: k}, v)
			}
			_, err := dec.Token() // }
			return n, err
		case '[':
			n := &yaml.Node{Kind: yaml.SequenceNode, Tag: "!!seq"}
			for dec.More() {
				vt, err := dec.Token()
				if err != nil {
					return nil, err
				}
				v, err := tokenNode(dec, vt)
				if err != nil {
					return nil, err
				}
				n.Content = append(n.Content, v)
			}
			_, err := dec.Token() // ]
			return n, err
		}
	case string:
		return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Value: t}, nil
	case json.Number:
		if _, err := strconv.ParseInt(string(t), 10, 64); err == nil {
			return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!int", Value: string(t)}, nil
		}
		return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!float", Value: string(t)}, nil
	case bool:
		return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!bool", Value: strconv.FormatBool(t)}, nil
	case nil:
		return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!null", Value: "null"}, nil
	}
	return nil, fmt.Errorf("unexpected JSON token %v", tok)
}
