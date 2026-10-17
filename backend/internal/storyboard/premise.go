package storyboard

import (
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/pyfmt"
)

// FirstPremise is the premise of a campaign's first episode: the world's first canon node,
// or its synopsis when there is no canon.
func FirstPremise(w *domain.World) string {
	if len(w.Canon.Nodes) > 0 && w.Canon.Nodes[0].Text != "" {
		return w.Canon.Nodes[0].Text
	}
	return w.Synopsis
}

// ContinuationPremise = the premise m0/state.py builds from the previous episode and the player's choice.
func ContinuationPremise(prev *domain.Storyboard, chosen string) string {
	texts := []string{}
	loc := any(nil)
	if prev != nil && len(prev.Panels) > 0 {
		last := prev.Panels[len(prev.Panels)-1]
		for _, b := range last.Bubbles {
			texts = append(texts, b.Text)
		}
		loc = last.LocationID
	}
	title := ""
	if prev != nil {
		title = prev.Title
	}
	locStr := "None"
	if s, ok := loc.(string); ok {
		locStr = s
	}
	return "Previous episode: \"" + title + "\". It ended with: " + pyfmt.Repr(texts) + " at " + locStr + ".\n" +
		"The player chose: \"" + chosen + "\". Continue directly from that moment."
}
