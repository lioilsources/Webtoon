package voiceworker

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
)

// Line audio for the phone's video export (VOICE_EXPORT_PLAN): the TTS takes of one line joined
// with a short gap, silence trimmed at both ends, two-pass linear loudnorm to -16 LUFS,
// AAC mono 48 kHz in .m4a. Loudnorm and the take checks are ported from Hajánek
// forge/internal/audio/ffmpeg.go.

// EncodeOpts sets the line format.
type EncodeOpts struct {
	LUFS       float64 // -16
	TruePeak   float64 // -1.5
	LRA        float64 // 11
	Bitrate    string  // 96k
	SampleRate int     // 48000
	GapS       float64 // silence between the sentences of one line
	TrimDB     float64 // silence threshold for trimming, -45 dB
	KeepS      float64 // silence kept at each end after trimming
}

func ffmpeg(ctx context.Context, args ...string) (string, error) {
	full := append([]string{"-hide_banner", "-nostdin", "-y"}, args...)
	cmd := exec.CommandContext(ctx, "ffmpeg", full...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		s := stderr.String()
		if len(s) > 1500 {
			s = s[len(s)-1500:]
		}
		return stderr.String(), fmt.Errorf("ffmpeg: %w\n%s", err, s)
	}
	return stderr.String(), nil
}

// Probe returns the duration of an audio file (ffprobe).
func Probe(ctx context.Context, path string) (float64, error) {
	out, err := exec.CommandContext(ctx, "ffprobe", "-v", "error", "-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1", path).Output()
	if err != nil {
		return 0, fmt.Errorf("ffprobe: %w", err)
	}
	return strconv.ParseFloat(strings.TrimSpace(string(out)), 64)
}

var reI = regexp.MustCompile(`(?m)^\s*I:\s+(-?[\d.]+|-inf) LUFS`)

// measurePad: EBU R128 gates 400 ms blocks, so a short word alone reads -inf; with trailing
// silence it measures close to the word's loudness.
const measurePad = "apad=pad_dur=0.5,"

// Loudness returns the integrated loudness (LUFS, -999 for silence).
func Loudness(ctx context.Context, path string) (float64, error) {
	s, err := ffmpeg(ctx, "-nostats", "-i", path, "-filter_complex", measurePad+"ebur128", "-f", "null", "-")
	if err != nil {
		return 0, err
	}
	if i := strings.LastIndex(s, "Summary:"); i >= 0 {
		s = s[i:]
	}
	m := reI.FindStringSubmatch(s)
	if m == nil || m[1] == "-inf" {
		return -999, nil
	}
	return strconv.ParseFloat(m[1], 64)
}

// MeasureTake returns the duration and loudness of one TTS take.
func MeasureTake(ctx context.Context, path string) (float64, float64, error) {
	d, err := Probe(ctx, path)
	if err != nil {
		return 0, 0, err
	}
	l, err := Loudness(ctx, path)
	return d, l, err
}

type loudnormStats struct {
	InputI       string `json:"input_i"`
	InputTP      string `json:"input_tp"`
	InputLRA     string `json:"input_lra"`
	InputThresh  string `json:"input_thresh"`
	TargetOffset string `json:"target_offset"`
}

// prefilter joins the parts and trims silence at both ends; it ends in the label [pre].
func prefilter(n int, o EncodeOpts) string {
	var g strings.Builder
	for i := range n {
		fmt.Fprintf(&g, "[%d:a]aresample=%d,aformat=sample_fmts=flt:channel_layouts=mono", i, o.SampleRate)
		if i < n-1 && o.GapS > 0 {
			fmt.Fprintf(&g, ",apad=pad_dur=%g", o.GapS)
		}
		fmt.Fprintf(&g, "[s%d];", i)
	}
	for i := range n {
		fmt.Fprintf(&g, "[s%d]", i)
	}
	trim := fmt.Sprintf("silenceremove=start_periods=1:start_threshold=%gdB:start_silence=%g", o.TrimDB, o.KeepS)
	fmt.Fprintf(&g, "concat=n=%d:v=0:a=1,%s,areverse,%s,areverse[pre]", n, trim, trim)
	return g.String()
}

// EncodeLine writes out (.m4a) and returns its duration in seconds.
func EncodeLine(ctx context.Context, parts []string, out string, o EncodeOpts) (float64, error) {
	if len(parts) == 0 {
		return 0, fmt.Errorf("encode: no input")
	}
	var in []string
	for _, p := range parts {
		in = append(in, "-i", p)
	}
	pre := prefilter(len(parts), o)
	first := fmt.Sprintf("%s;[pre]%sloudnorm=I=%g:TP=%g:LRA=%g:print_format=json[ln]", pre, measurePad, o.LUFS, o.TruePeak, o.LRA)
	s, err := ffmpeg(ctx, append(in, "-filter_complex", first, "-map", "[ln]", "-f", "null", "-")...)
	if err != nil {
		return 0, err
	}
	i, j := strings.LastIndex(s, "{"), strings.LastIndex(s, "}")
	if i < 0 || j < i {
		return 0, fmt.Errorf("loudnorm: no stats in output")
	}
	var st loudnormStats
	if err := json.Unmarshal([]byte(s[i:j+1]), &st); err != nil {
		return 0, fmt.Errorf("loudnorm stats: %w", err)
	}
	if v, err := strconv.ParseFloat(st.InputI, 64); err != nil || v < -70 {
		return 0, fmt.Errorf("encode: silent input (integrated %s LUFS)", st.InputI)
	}
	second := fmt.Sprintf("%s;[pre]loudnorm=I=%g:TP=%g:LRA=%g:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true,aresample=%d[out]",
		pre, o.LUFS, o.TruePeak, o.LRA, st.InputI, st.InputTP, st.InputLRA, st.InputThresh, st.TargetOffset, o.SampleRate)
	args := append(in, "-filter_complex", second, "-map", "[out]", "-c:a", "aac", "-b:a", o.Bitrate, "-ac", "1",
		"-ar", strconv.Itoa(o.SampleRate), "-map_metadata", "-1", "-movflags", "+faststart", "-f", "mp4", out)
	if _, err := ffmpeg(ctx, args...); err != nil {
		return 0, err
	}
	return Probe(ctx, out)
}
