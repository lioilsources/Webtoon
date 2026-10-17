"""Minimal ComfyUI API client + parametrised SDXL workflow (optionally with IP-Adapter)."""

import json
import time
import urllib.parse
import uuid

from common import COMFY_URL, http, http_json


def workflow(positive, negative, width, height, seed, preset, prefix, ref_image=None, ip_weight=0.6, ip_preset="PLUS (high strength)", ip_end=0.8, loras=()):
    """API-format graph. ref_image = filename already uploaded to ComfyUI input/."""
    g = {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": preset["checkpoint"]}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["ckpt", 1]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["ckpt", 1]}},
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "sample": {"class_type": "KSampler", "inputs": {
            "model": ["ckpt", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
            "seed": seed, "steps": preset["steps"], "cfg": preset["cfg"],
            "sampler_name": preset["sampler"], "scheduler": preset["scheduler"], "denoise": 1.0}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}},
    }
    for k, lora in enumerate(loras):
        # Each LoRA patches model and CLIP; chained so they compose.
        prev = f"lora{k - 1}" if k else "ckpt"
        g[f"lora{k}"] = {"class_type": "LoraLoader", "inputs": {
            "model": [prev, 0], "clip": [prev, 1], "lora_name": lora["name"],
            "strength_model": lora.get("strength", 1.0), "strength_clip": lora.get("strength", 1.0)}}
    if loras:
        last = f"lora{len(loras) - 1}"
        g["sample"]["inputs"]["model"] = [last, 0]
        g["pos"]["inputs"]["clip"] = [last, 1]
        g["neg"]["inputs"]["clip"] = [last, 1]
    if preset.get("prediction") == "v":
        g["vpred"] = {"class_type": "ModelSamplingDiscrete", "inputs": {"model": ["ckpt", 0], "sampling": "v_prediction", "zsnr": True}}
        g["sample"]["inputs"]["model"] = ["vpred", 0]
    if ref_image:
        base = g["sample"]["inputs"]["model"]
        g["ipload"] = {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": base, "preset": ip_preset}}
        g["refimg"] = {"class_type": "LoadImage", "inputs": {"image": ref_image}}
        g["ipapply"] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["ipload", 0], "ipadapter": ["ipload", 1], "image": ["refimg", 0],
            "weight": ip_weight, "weight_type": "linear", "combine_embeds": "concat",
            "start_at": 0.0, "end_at": ip_end, "embeds_scaling": "V only"}}
        g["sample"]["inputs"]["model"] = ["ipapply", 0]
    return g


def flux_workflow(prompt, width, height, seed, preset, prefix, loras=()):
    """FLUX.1-dev graph (same shape as Ol1nLLM's flux_manga_txt2img): UNET + T5/CLIP-L + FluxGuidance, cfg 1."""
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": preset["unet"], "weight_dtype": "fp8_e4m3fn"}},
        "clip": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["clip", 0]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["clip", 0]}},
        "guide": {"class_type": "FluxGuidance", "inputs": {"guidance": preset.get("guidance", 3.5), "conditioning": ["pos", 0]}},
        "latent": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "sample": {"class_type": "KSampler", "inputs": {
            "model": ["unet", 0], "positive": ["guide", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
            "seed": seed, "steps": preset.get("steps", 20), "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}},
    }
    for k, lora in enumerate(loras):
        prev = f"lora{k - 1}" if k else None
        g[f"lora{k}"] = {"class_type": "LoraLoader", "inputs": {
            "model": [prev, 0] if prev else ["unet", 0], "clip": [prev, 1] if prev else ["clip", 0],
            "lora_name": lora["name"], "strength_model": lora.get("strength", 1.0), "strength_clip": lora.get("strength", 1.0)}}
    if loras:
        last = f"lora{len(loras) - 1}"
        g["sample"]["inputs"]["model"] = [last, 0]
        g["pos"]["inputs"]["clip"] = [last, 1]
        g["neg"]["inputs"]["clip"] = [last, 1]
    return g


def is_up():
    try:
        http_json("GET", f"{COMFY_URL}/system_stats", timeout=5)
        return True
    except Exception:
        return False


def upload(png_bytes, name):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png_bytes + \
           f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode()
    res = json.loads(http("POST", f"{COMFY_URL}/upload/image", body,
                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    return res["name"] if not res.get("subfolder") else f"{res['subfolder']}/{res['name']}"


def run(graph, timeout=900):
    """Queues the graph, waits, returns list of PNG bytes."""
    client_id = uuid.uuid4().hex
    pid = http_json("POST", f"{COMFY_URL}/prompt", {"prompt": graph, "client_id": client_id})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = http_json("GET", f"{COMFY_URL}/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error: {json.dumps(status.get('messages', []))[:800]}")
            images = []
            for out in entry.get("outputs", {}).values():
                for im in out.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"], "type": im["type"]})
                    images.append(http("GET", f"{COMFY_URL}/view?{q}"))
            return images
        time.sleep(1.5)
    raise TimeoutError(f"prompt {pid} not finished in {timeout}s")
