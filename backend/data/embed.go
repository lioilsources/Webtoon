// Package data embeds copies of ../data (Webtoon/data): the M0 seed world, style presets
// and the WD14 tag vocabulary used to filter storyboard tags.
package data

import _ "embed"

//go:embed world_m0.json
var WorldM0 []byte

//go:embed styles.json
var Styles []byte

//go:embed wd14_tags.json
var WD14Tags []byte
