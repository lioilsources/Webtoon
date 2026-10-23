"""Minimal ComfyUI API client + parametrised SDXL workflow (optionally with IP-Adapter)."""

import json
import time
import urllib.parse
import uuid

from common import COMFY_URL, http, http_json


REGION_OVERLAP = 0.2  # each character's strip reaches this far past the frame's 1/n, so the pair can touch


def strips(n):
    """(x, width) of each character's vertical strip, as fractions of the frame, left to right."""
    w = min(1.0, 1 / max(n, 1) + REGION_OVERLAP)
    return [(round(i * (1 - w) / (n - 1), 3) if n > 1 else 0.0, round(w, 3)) for i in range(n)]


def workflow(positive, negative, width, height, seed, preset, prefix, ref_image=None, ip_weight=0.6, ip_preset="PLUS (high strength)", ip_end=0.8,
             regions=None, refs=None):
    """API-format graph. ref_image = filename already uploaded to ComfyUI input/.
    regions = one prompt per character, left to right, each over its vertical strip (core area conditioning).
    refs = [(uploaded filename, strip or None)]: one IP-Adapter per character reference, masked to its strip."""
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
    cond = ["pos", 0]
    for i, (text, (x, w)) in enumerate(zip(regions or [], strips(len(regions or [])))):
        g[f"rpos{i}"] = {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": clip}}
        g[f"rarea{i}"] = {"class_type": "ConditioningSetAreaPercentage", "inputs": {
            "conditioning": [f"rpos{i}", 0], "width": w, "height": 1.0, "x": x, "y": 0.0, "strength": 1.0}}
        g[f"rcomb{i}"] = {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": cond, "conditioning_2": [f"rarea{i}", 0]}}
        cond = [f"rcomb{i}", 0]
    g["sample"]["inputs"]["positive"] = cond
    g["sample"]["inputs"]["model"] = model
    if preset.get("prediction") == "v":
        g["vpred"] = {"class_type": "ModelSamplingDiscrete", "inputs": {"model": model, "sampling": "v_prediction", "zsnr": True}}
        g["sample"]["inputs"]["model"] = ["vpred", 0]
    refs = refs or ([(ref_image, None)] if ref_image else [])
    if refs:
        model = g["sample"]["inputs"]["model"]
        g["ipload"] = {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": model, "preset": ip_preset}}
        model = ["ipload", 0]
        for i, (image, strip) in enumerate(refs):
            g[f"refimg{i}"] = {"class_type": "LoadImage", "inputs": {"image": image}}
            inputs = {"model": model, "ipadapter": ["ipload", 1], "image": [f"refimg{i}", 0],
                      "weight": ip_weight, "weight_type": "linear", "combine_embeds": "concat",
                      "start_at": 0.0, "end_at": ip_end, "embeds_scaling": "V only"}
            if strip:  # without the mask both faces blend into each person
                x, w = strip
                g[f"mzero{i}"] = {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": width, "height": height}}
                g[f"mone{i}"] = {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": round(w * width), "height": height}}
                g[f"mask{i}"] = {"class_type": "MaskComposite", "inputs": {
                    "destination": [f"mzero{i}", 0], "source": [f"mone{i}", 0], "x": round(x * width), "y": 0, "operation": "add"}}
                inputs["attn_mask"] = [f"mask{i}", 0]
            g[f"ipapply{i}"] = {"class_type": "IPAdapterAdvanced", "inputs": inputs}
            model = [f"ipapply{i}", 0]
        g["sample"]["inputs"]["model"] = model
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
