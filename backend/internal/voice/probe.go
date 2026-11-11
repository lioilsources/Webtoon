package voice

import (
	"encoding/binary"
	"errors"
)

// The API never writes a plaintext sample to disk, so it reads the duration from the container
// itself instead of running ffprobe on a temp file: mvhd of an MP4/M4A, the fmt and data chunks
// of a WAV. The worker and the audio service validate the audio again.

// SniffAudio returns the sample format (m4a, wav) from magic bytes.
func SniffAudio(head []byte) (string, bool) {
	switch {
	case len(head) >= 12 && string(head[0:4]) == "RIFF" && string(head[8:12]) == "WAVE":
		return "wav", true
	case len(head) >= 8 && string(head[4:8]) == "ftyp":
		return "m4a", true
	}
	return "", false
}

var errNoDuration = errors.New("no duration in audio container")

// AudioDuration returns the duration in seconds of an m4a or wav file.
func AudioDuration(ext string, b []byte) (float64, error) {
	switch ext {
	case "m4a":
		return mp4Duration(b)
	case "wav":
		return wavDuration(b)
	}
	return 0, errors.New("unsupported audio format")
}

// boxes walks ISO BMFF boxes in b and calls fn with each type and payload.
func boxes(b []byte, fn func(typ string, payload []byte) bool) error {
	for len(b) >= 8 {
		size := uint64(binary.BigEndian.Uint32(b[0:4]))
		typ := string(b[4:8])
		hdr := uint64(8)
		switch size {
		case 1:
			if len(b) < 16 {
				return errNoDuration
			}
			size, hdr = binary.BigEndian.Uint64(b[8:16]), 16
		case 0:
			size = uint64(len(b))
		}
		if size < hdr || size > uint64(len(b)) {
			return errNoDuration
		}
		if !fn(typ, b[hdr:size]) {
			return nil
		}
		b = b[size:]
	}
	return nil
}

func mp4Duration(b []byte) (float64, error) {
	var moov []byte
	if err := boxes(b, func(typ string, p []byte) bool {
		if typ == "moov" {
			moov = p
			return false
		}
		return true
	}); err != nil {
		return 0, err
	}
	if moov == nil {
		return 0, errNoDuration
	}
	var d float64
	found := false
	if err := boxes(moov, func(typ string, p []byte) bool {
		if typ != "mvhd" || len(p) < 4 {
			return true
		}
		var scale uint32
		var dur uint64
		switch p[0] {
		case 0:
			if len(p) < 20 {
				return false
			}
			scale, dur = binary.BigEndian.Uint32(p[12:16]), uint64(binary.BigEndian.Uint32(p[16:20]))
		case 1:
			if len(p) < 32 {
				return false
			}
			scale, dur = binary.BigEndian.Uint32(p[20:24]), binary.BigEndian.Uint64(p[24:32])
		default:
			return false
		}
		if scale > 0 {
			d, found = float64(dur)/float64(scale), true
		}
		return false
	}); err != nil {
		return 0, err
	}
	if !found {
		return 0, errNoDuration
	}
	return d, nil
}

func wavDuration(b []byte) (float64, error) {
	if len(b) < 12 {
		return 0, errNoDuration
	}
	b = b[12:]
	var byteRate uint32
	for len(b) >= 8 {
		id := string(b[0:4])
		size := uint64(binary.LittleEndian.Uint32(b[4:8]))
		body := b[8:]
		// Streaming recorders leave the data size at 0 or 0xFFFFFFFF: take what is there.
		if id == "data" && (size == 0 || size > uint64(len(body))) {
			size = uint64(len(body))
		}
		if size > uint64(len(body)) {
			return 0, errNoDuration
		}
		switch id {
		case "fmt ":
			if size < 16 {
				return 0, errNoDuration
			}
			byteRate = binary.LittleEndian.Uint32(body[8:12])
		case "data":
			if byteRate == 0 {
				return 0, errNoDuration
			}
			return float64(size) / float64(byteRate), nil
		}
		adv := 8 + size + size%2 // chunks are word aligned
		if adv > uint64(len(b)) {
			break
		}
		b = b[adv:]
	}
	return 0, errNoDuration
}
