// Package pyfmt reproduces the two Python serialisations the M0 prompts were tuned with:
// json.dumps(obj, ensure_ascii=False) and repr() of lists/strings, so the Go port sends
// the LLM the same text the prototype did.
package pyfmt

import (
	"bytes"
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// JSON = json.dumps(v, ensure_ascii=False): ", " and ": " separators, no HTML escaping.
// Key order follows Go marshalling (struct field order; maps sorted).
func JSON(v any) string {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		return "null"
	}
	return Spaced(bytes.TrimRight(buf.Bytes(), "\n"))
}

// Spaced inserts Python's default separators into compact JSON.
func Spaced(compact []byte) string {
	var out strings.Builder
	out.Grow(len(compact) + len(compact)/8)
	inStr, esc := false, false
	for _, c := range compact {
		out.WriteByte(c)
		if inStr {
			switch {
			case esc:
				esc = false
			case c == '\\':
				esc = true
			case c == '"':
				inStr = false
			}
			continue
		}
		switch c {
		case '"':
			inStr = true
		case ',', ':':
			out.WriteByte(' ')
		}
	}
	return out.String()
}

// Repr approximates Python repr() for JSON-like values (str, list, dict, bool, None, numbers).
func Repr(v any) string {
	switch x := v.(type) {
	case nil:
		return "None"
	case string:
		return reprStr(x)
	case bool:
		if x {
			return "True"
		}
		return "False"
	case float64:
		if x == float64(int64(x)) {
			return strconv.FormatInt(int64(x), 10)
		}
		return strconv.FormatFloat(x, 'g', -1, 64)
	case int:
		return strconv.Itoa(x)
	case []string:
		parts := make([]string, len(x))
		for i, s := range x {
			parts[i] = reprStr(s)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case []any:
		parts := make([]string, len(x))
		for i, s := range x {
			parts[i] = Repr(s)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		parts := make([]string, len(keys))
		for i, k := range keys {
			parts[i] = reprStr(k) + ": " + Repr(x[k])
		}
		return "{" + strings.Join(parts, ", ") + "}"
	default:
		return fmt.Sprint(x)
	}
}

func reprStr(s string) string {
	quote := byte('\'')
	if strings.ContainsRune(s, '\'') && !strings.ContainsRune(s, '"') {
		quote = '"'
	}
	var b strings.Builder
	b.WriteByte(quote)
	for _, r := range s {
		switch {
		case r == '\\':
			b.WriteString(`\\`)
		case r == rune(quote):
			b.WriteByte('\\')
			b.WriteRune(r)
		case r == '\n':
			b.WriteString(`\n`)
		case r == '\r':
			b.WriteString(`\r`)
		case r == '\t':
			b.WriteString(`\t`)
		case r < 0x20 || r == 0x7f:
			fmt.Fprintf(&b, `\x%02x`, r)
		default:
			b.WriteRune(r)
		}
	}
	b.WriteByte(quote)
	return b.String()
}
