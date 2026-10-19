package comfy

import "fmt"

// Motion panels: a 1–3 s seamless loop rendered from the finished still with Wan 2.2 I2V 14B
// (Lightning 4-step LoRAs), port of video-stack/workflows/flf2v_lightning_portrait.json.
// WanFirstLastFrameToVideo gets the same image as first and last frame, so the loop closes
// without a cut and the character's identity is the still itself. Output is an animated WebP
// (Flutter plays it natively) plus three single frames for the WD14 check.

const (
	VideoFPS = 16
	// 480p tier of the video stack (~0.34 Mpx): HD costs 5× and a phone cannot tell.
	videoLong  = 704
	videoShort = 480

	wanHighNoise = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
	wanLowNoise  = "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
	wanLoraHigh  = "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors"
	wanLoraLow   = "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_low_noise_model.safetensors"
	wanCLIP      = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
	wanVAE       = "wan_2.1_vae.safetensors"

	// chain.py default negative for Wan beats.
	VideoNegative = "blurry, static, low quality, watermark, text"
)

// VideoLength = frames for a loop of n seconds: Wan's VAE compresses time 4:1, so 4k+1.
func VideoLength(seconds int) int { return VideoFPS*seconds + 1 }

// VideoSize picks the render size from the still's aspect (portrait 480×704, landscape 704×480).
func VideoSize(stillW, stillH int) (w, h int) {
	if stillW > stillH {
		return videoLong, videoShort
	}
	return videoShort, videoLong
}

// VideoEstimateSeconds is the render-time hint shown in the editor (phase3_bench: 155 s for
// 33 frames at 0.4 Mpx with Lightning; shorter loops pay the model load, longer ones scale).
func VideoEstimateSeconds(loopSeconds int) int {
	switch loopSeconds {
	case 1:
		return 100
	case 3:
		return 200
	default:
		return 155
	}
}

// VideoWorkflow builds the FLF2V loop graph. start = the still's file name already uploaded to
// ComfyUI input/. Outputs: one animated WebP (save_webp) and three PNG frames (first, middle,
// last) for the safety check; ComfyUI reports them in map order, so callers tell them apart by
// content, not position.
func VideoWorkflow(start, motion, negative string, width, height, length int, seed int64, prefix string) Graph {
	if negative == "" {
		negative = VideoNegative
	}
	sampler := func(model string, addNoise bool, latent []any, from, to int) map[string]any {
		noise, leftover := "disable", "disable"
		if addNoise {
			noise, leftover = "enable", "enable"
		}
		return map[string]any{
			"model": []any{model, 0}, "positive": []any{"flf", 0}, "negative": []any{"flf", 1}, "latent_image": latent,
			"add_noise": noise, "noise_seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
			"start_at_step": from, "end_at_step": to, "return_with_leftover_noise": leftover,
		}
	}
	frame := func(index int) map[string]any {
		return map[string]any{"image": []any{"decode", 0}, "batch_index": index, "length": 1}
	}
	g := Graph{
		"unet_high":  node("UNETLoader", map[string]any{"unet_name": wanHighNoise, "weight_dtype": "default"}),
		"lora_high":  node("LoraLoaderModelOnly", map[string]any{"model": []any{"unet_high", 0}, "lora_name": wanLoraHigh, "strength_model": 1.0}),
		"shift_high": node("ModelSamplingSD3", map[string]any{"model": []any{"lora_high", 0}, "shift": 5.0}),
		"unet_low":   node("UNETLoader", map[string]any{"unet_name": wanLowNoise, "weight_dtype": "default"}),
		"lora_low":   node("LoraLoaderModelOnly", map[string]any{"model": []any{"unet_low", 0}, "lora_name": wanLoraLow, "strength_model": 1.0}),
		"shift_low":  node("ModelSamplingSD3", map[string]any{"model": []any{"lora_low", 0}, "shift": 5.0}),
		"clip":       node("CLIPLoader", map[string]any{"clip_name": wanCLIP, "type": "wan", "device": "default"}),
		"pos":        node("CLIPTextEncode", map[string]any{"clip": []any{"clip", 0}, "text": motion}),
		"neg":        node("CLIPTextEncode", map[string]any{"clip": []any{"clip", 0}, "text": negative}),
		"start":      node("LoadImage", map[string]any{"image": start}),
		"vae":        node("VAELoader", map[string]any{"vae_name": wanVAE}),
		"flf": node("WanFirstLastFrameToVideo", map[string]any{
			"positive": []any{"pos", 0}, "negative": []any{"neg", 0}, "vae": []any{"vae", 0},
			"width": width, "height": height, "length": length, "batch_size": 1,
			"start_image": []any{"start", 0}, "end_image": []any{"start", 0}}),
		"sample_high": node("KSamplerAdvanced", sampler("shift_high", true, []any{"flf", 2}, 0, 2)),
		"sample_low":  node("KSamplerAdvanced", sampler("shift_low", false, []any{"sample_high", 0}, 2, 4)),
		"decode":      node("VAEDecode", map[string]any{"samples": []any{"sample_low", 0}, "vae": []any{"vae", 0}}),
		"save_webp": node("SaveAnimatedWEBP", map[string]any{"images": []any{"decode", 0}, "filename_prefix": prefix,
			"fps": float64(VideoFPS), "lossless": false, "quality": 80, "method": "default"}),
		"frame_first": node("ImageFromBatch", frame(0)),
		"frame_mid":   node("ImageFromBatch", frame(length/2)),
		"frame_last":  node("ImageFromBatch", frame(length-1)),
		"save_first":  node("SaveImage", map[string]any{"images": []any{"frame_first", 0}, "filename_prefix": prefix + "_f0"}),
		"save_mid":    node("SaveImage", map[string]any{"images": []any{"frame_mid", 0}, "filename_prefix": fmt.Sprintf("%s_f%d", prefix, length/2)}),
		"save_last":   node("SaveImage", map[string]any{"images": []any{"frame_last", 0}, "filename_prefix": fmt.Sprintf("%s_f%d", prefix, length-1)}),
	}
	return g
}

// IsWebP reports whether the bytes are a RIFF/WEBP container (the loop among the graph's outputs).
func IsWebP(b []byte) bool {
	return len(b) >= 12 && string(b[:4]) == "RIFF" && string(b[8:12]) == "WEBP"
}
