"""Minimal ComfyUI API client + parametrised SDXL workflow (optionally with IP-Adapter)."""

import json
import time
import urllib.parse
import uuid

from common import COMFY_URL, http, http_json


def workflow(positive, negative, width, height, seed, preset, prefix, ref_image=None, ip_weight=0.6, ip_preset="PLUS (high strength)", ip_end=0.8):
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
    # Style LoRAs: preset["loras"] = [[file, strength], ...], chained after the checkpoint (model + clip).
    model, clip = ["ckpt", 0], ["ckpt", 1]
    for i, (name, strength) in enumerate(preset.get("loras") or []):
        g[f"lora{i}"] = {"class_type": "LoraLoader", "inputs": {"model": model, "clip": clip, "lora_name": name,
                                                                "strength_model": strength, "strength_clip": strength}}
        model, clip = [f"lora{i}", 0], [f"lora{i}", 1]
    g["pos"]["inputs"]["clip"] = g["neg"]["inputs"]["clip"] = clip
    g["sample"]["inputs"]["model"] = model
    if preset.get("prediction") == "v":
        g["vpred"] = {"class_type": "ModelSamplingDiscrete", "inputs": {"model": model, "sampling": "v_prediction", "zsnr": True}}
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


def run_outputs(graph, timeout=900):
    """Queues the graph, waits, returns {node_id: [{"filename", "subfolder", "type", "bytes"}, ...]} for every
    output file (SaveImage PNGs, SaveAnimatedWEBP, VHS videos — ComfyUI lists them under "images" or "gifs")."""
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
            outputs = {}
            for node, out in entry.get("outputs", {}).items():
                for key in ("images", "gifs", "videos"):
                    for f in out.get(key, []):
                        if f.get("type") == "temp":  # previews, not saved results
                            continue
                        q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
                        outputs.setdefault(node, []).append({**f, "bytes": http("GET", f"{COMFY_URL}/view?{q}")})
            return outputs
        time.sleep(1.5)
    raise TimeoutError(f"prompt {pid} not finished in {timeout}s")


def run(graph, timeout=900):
    """Queues the graph, waits, returns list of PNG bytes (SaveImage outputs, graph order)."""
    outs = run_outputs(graph, timeout)
    return [f["bytes"] for node in graph if node in outs for f in outs[node] if f["filename"].lower().endswith(".png")]
