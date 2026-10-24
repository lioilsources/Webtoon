"""Style benchmark candidates → data/style_bench/candidates.json (+ scenes.json).

    python3 m0/style_bench_gen.py            # rewrites both files; deterministic, ids are stable

Candidates = every preset in data/styles.json (id = preset id, fields copied verbatim) + new combinations
checkpoint × artist tags × aesthetic family from the COMBOS table below (id = <family>_<ckpt>[_<artist>…]).
Appending rows to COMBOS never renames an existing id; removing a row drops only that id.
LoRA axis (source "lora"): each STYLE_LORAS entry × its checkpoints × strengths, some STYLE_PLUS_QUALITY rows with
one quality LoRA, and PRESET_QUALITY quality-LoRA-only variants of existing presets. Ids:
<family>_<ckpt>_lora-<short>-<strength×10>[_q-<quality>-<strength×10>] and <preset>_q-<quality>-<strength×10>.
Only files in LORA_ALLOWLIST (SFW SDXL-family) are ever referenced; check_loras() asserts it plus the rules:
style LoRAs only on anime checkpoints, Detail_Tweaker/xl_more_art only on photoreal ones, realism-slider and
gothic-niji never kids, Spacecraft only for the landscape scene (`scenes_only`) and the superhero audience.

Audiences (who may get a style): kids · harlequin (adult romance) · superhero (teen + adult action cast) · free
(adult free world). Checkpoint rules (memory, styles.json _note):
  - humans only on NoobAI / Illustrious / Hassaku / Animagine;
  - photoreal (RealVis, Juggernaut, CyberRealistic) only with ADULT casts → harlequin + free; never kids, and not
    superhero either, because a superhero cast may be teenage;
  - WAI / Lustify / Pony only for non-human characters → such a candidate would get no audiences and only the
    landscape scene (none of the Spark checkpoints is one today, the rule is kept for later additions).
Scene gating (style_bench.py): scene a (kid hero) needs "kids", b/c (adults) need harlequin/superhero/free, d always.
"""

import json
import re

from common import DATA, load_json, save_json

OUT_DIR = DATA / "style_bench"
ALL = ["kids", "harlequin", "superhero", "free"]
ADULT = ["harlequin", "superhero", "free"]
PHOTO = ["harlequin", "free"]
NONHUMAN_ONLY = re.compile(r"wai|lustify|pony", re.I)

# Checkpoint short name → (file, preset whose prediction/quality/sampler fields new candidates inherit, Czech label)
CKPT = {
    "noob": ("noobai-xl-eps11.safetensors", "clean_webtoon", "NoobAI"),
    "hassaku": ("HassakuXL_Illustrious_v3.4.safetensors", "hassaku_soft", "Hassaku"),
    "illu": ("Illustrious-XL-v2.0.safetensors", "western_comic", "Illustrious"),
    "anim": ("animagine-xl-40-opt.safetensors", "manga_mono", "Animagine"),
    "realvis": ("RealVisXL_V5.0.safetensors", "photo_realvis_film", "RealVis"),
    "jugg": ("Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors", "photo_juggernaut", "Juggernaut"),
    "jugglight": ("Juggernaut-XL-Lightning_4Steps.safetensors", "photo_lightning", "Juggernaut Lightning"),
    "cyber": ("CyberRealisticXL_v10.safetensors", "photo_cyberreal_night", "CyberRealistic"),
}
PHOTO_CKPTS = {"realvis", "jugg", "jugglight", "cyber"}

# Danbooru artist tags NoobAI/Illustrious know. key → (tag, weight, kids_ok, display name).
# kids_ok=False: the artist's body of work leans fanservice; such a candidate is not offered to kids.
ARTISTS = {
    "ningenmame": ("ningen mame", 0.8, True, "Ningen Mame"),
    "ciloranko": ("ciloranko", 0.7, True, "Ciloranko"),
    "wlop": ("wlop", 0.7, True, "WLOP"),
    "kantoku": ("kantoku", 0.8, True, "Kantoku"),
    "mikapikazo": ("mika pikazo", 0.7, True, "Mika Pikazo"),
    "askzy": ("ask (askzy)", 0.7, True, "Ask"),
    "as109": ("as109", 0.7, False, "as109"),
    "sho": ("sho (sho lwlw)", 0.7, True, "Sho"),
    "rella": ("rella", 0.8, True, "Rella"),
    "toosaka": ("toosaka asagi", 0.7, False, "Toosaka Asagi"),
    "fuzichoco": ("fuzichoco", 0.8, True, "Fuzichoco"),
    "nardack": ("nardack", 0.7, True, "Nardack"),
    "hiten": ("hiten (hitenkei)", 0.7, True, "Hiten"),
    "mignon": ("mignon", 0.7, False, "Mignon"),
    "tiv": ("tiv", 0.7, False, "Tiv"),
    "redjuice": ("redjuice", 0.7, True, "Redjuice"),
    "murata": ("range murata", 0.8, True, "Range Murata"),
    "yoneyama": ("yoneyama mai", 0.8, True, "Yoneyama Mai"),
    "lack": ("lack", 0.7, True, "LAM/Lack"),
    "anmi": ("anmi", 0.7, True, "Anmi"),
    "kuvshinov": ("ilya kuvshinov", 0.8, True, "Kuvshinov"),
    "torino": ("torino aqua", 0.7, True, "Torino Aqua"),
    "kawacy": ("kawacy", 0.7, True, "Kawacy"),
    "atdan": ("atdan", 0.7, True, "Atdan"),
    "amano": ("amano yoshitaka", 0.8, True, "Amano"),
    "takeuchi": ("takeuchi takashi", 0.7, True, "Takeuchi Takashi"),
    "mochizuki": ("mochizuki kei", 0.8, True, "Mochizuki Kei"),
    "kishida": ("kishida mel", 0.7, True, "Kishida Mel"),
    "mucha": ("alphonse mucha", 0.8, True, "Mucha"),
}

# family → (Czech name, aesthetic tags, audiences before checkpoint/artist rules)
FAMILIES = {
    "watercolor": ("Akvarel", ["watercolor (medium)", "traditional media", "soft colors", "paper texture"], ALL),
    "ink": ("Tuš", ["ink (medium)", "traditional media", "lineart", "limited palette", "hatching (texture)"], ALL),
    "cel": ("Cel shading", ["cel shading", "anime coloring", "clean lineart", "vivid colors"], ALL),
    "flat": ("Plochá barva", ["flat color", "clean lineart", "simple shading", "bright colors"], ALL),
    "painterly": ("Malba", ["painterly", "brush strokes", "realistic lighting", "rich colors"], ALL),
    "retro90s": ("Retro anime 90s", ["1990s (style)", "retro artstyle", "anime screencap", "cel shading", "film grain"], ALL),
    "cyberpunk": ("Kyberpunk neon", ["cyberpunk", "neon lights", "glowing", "night", "chromatic aberration"], ALL),
    "storybook": ("Pohádková kniha", ["storybook", "children's book illustration", "colored pencil (medium)", "soft colors",
                                      "whimsical"], ["kids"]),
    "gouache": ("Kvaš", ["gouache (medium)", "traditional media", "matte colors", "painterly"], ALL),
    "pastel": ("Pastel", ["pastel colors", "soft lighting", "light particles", "bloom"], ALL),
    "chibi": ("Čibi", ["chibi", "super deformed", "flat color", "cute"], ["kids"]),
    "comic": ("Komiks raster", ["western comics (style)", "halftone", "bold lineart", "dynamic pose", "vivid colors"], ALL),
    "sketch": ("Skica", ["sketch", "pencil (medium)", "graphite (medium)", "traditional media", "unfinished"], ALL),
    "render3d": ("3D render", ["3d", "blender (medium)", "toon shading", "cinematic lighting", "stylized"], ALL),
    "pixel": ("Pixel art", ["pixel art", "limited palette", "dithering", "retro game"], ALL),
    "stainedglass": ("Vitráž", ["stained glass", "black outline", "jewel tones", "glowing", "mosaic"], ALL),
    "papercut": ("Vystřihovánka", ["paper cutout", "papercraft", "layered paper", "drop shadow", "flat color"], ALL),
    "crayon": ("Pastelky", ["crayon (medium)", "traditional media", "colorful", "naive art", "paper texture"], ["kids"]),
    "gamecg": ("Herní CG", ["game cg", "detailed background", "lens flare", "vibrant colors", "dramatic lighting"], ALL),
    "fantasy": ("Fantasy", ["fantasy", "magic", "glowing", "ornate", "detailed background"], ALL),
    "woodblock": ("Dřevořez", ["ukiyo-e", "woodblock print", "flat color", "textured paper", "limited palette"], ALL),
    "artnouveau": ("Secese", ["art nouveau", "ornate border", "flowers", "decorative"], ALL),
    "shoujo": ("Šódžo romance", ["shoujo manga", "sparkle", "soft focus", "romantic atmosphere", "flower background"], ADULT),
    "noir": ("Noir", ["(monochrome:1.3)", "(greyscale:1.3)", "film noir", "high contrast", "dramatic shadows"], ADULT),
    # photoreal families (natural-language presets; artist tags are ignored by prompts._natural)
    "photo": ("Foto", [], PHOTO),
}

# (family, checkpoint, [artist keys], extra aesthetic tags or None)
COMBOS = [
    ("watercolor", "noob", ["ningenmame"], None),
    ("watercolor", "hassaku", ["rella"], None),
    ("watercolor", "illu", ["fuzichoco"], None),
    ("watercolor", "anim", [], None),
    ("watercolor", "noob", ["kishida"], None),
    ("ink", "noob", ["murata"], None),
    ("ink", "anim", ["amano"], None),
    ("ink", "illu", [], None),
    ("cel", "noob", ["kantoku"], None),
    ("cel", "noob", ["askzy"], None),
    ("cel", "illu", ["sho"], None),
    ("cel", "anim", ["hiten"], None),
    ("cel", "hassaku", ["as109"], None),
    ("flat", "noob", ["mochizuki"], None),
    ("flat", "illu", ["ciloranko"], None),
    ("flat", "anim", ["kawacy"], None),
    ("flat", "hassaku", ["ningenmame", "ciloranko"], None),
    ("painterly", "noob", ["wlop"], None),
    ("painterly", "illu", ["wlop"], None),
    ("painterly", "hassaku", ["kuvshinov"], None),
    ("painterly", "noob", ["atdan"], None),
    ("painterly", "illu", ["amano"], None),
    ("retro90s", "noob", [], None),
    ("retro90s", "anim", [], None),
    ("retro90s", "illu", ["takeuchi"], None),
    ("retro90s", "noob", ["toosaka"], None),
    ("cyberpunk", "noob", ["mikapikazo"], None),
    ("cyberpunk", "noob", ["redjuice"], None),
    ("cyberpunk", "illu", ["yoneyama"], None),
    ("cyberpunk", "anim", ["lack"], None),
    ("cyberpunk", "hassaku", ["tiv"], None),
    ("storybook", "hassaku", [], None),
    ("storybook", "illu", [], None),
    ("storybook", "noob", ["mochizuki"], None),
    ("storybook", "noob", ["kishida"], None),
    ("gouache", "noob", ["torino"], None),
    ("gouache", "hassaku", [], None),
    ("gouache", "illu", ["fuzichoco"], None),
    ("gouache", "noob", ["anmi"], None),
    ("pastel", "noob", ["kantoku"], None),
    ("pastel", "hassaku", ["rella"], None),
    ("pastel", "anim", [], None),
    ("pastel", "illu", ["anmi"], None),
    ("chibi", "noob", [], None),
    ("chibi", "anim", [], None),
    ("chibi", "hassaku", ["ningenmame"], None),
    ("comic", "noob", [], None),
    ("comic", "anim", [], None),
    ("comic", "illu", ["murata"], None),
    ("comic", "noob", ["sho"], None),
    ("sketch", "noob", [], None),
    ("sketch", "anim", [], None),
    ("sketch", "illu", ["lack"], None),
    ("render3d", "noob", [], None),
    ("render3d", "illu", [], None),
    ("render3d", "hassaku", [], None),
    ("pixel", "noob", [], None),
    ("pixel", "illu", [], None),
    ("pixel", "anim", [], None),
    ("stainedglass", "noob", [], None),
    ("stainedglass", "illu", ["mikapikazo"], None),
    ("stainedglass", "hassaku", [], None),
    ("papercut", "noob", [], None),
    ("papercut", "illu", [], None),
    ("papercut", "hassaku", [], None),
    ("crayon", "noob", [], None),
    ("crayon", "hassaku", [], None),
    ("gamecg", "noob", ["hiten"], None),
    ("gamecg", "illu", ["nardack"], None),
    ("gamecg", "noob", ["nardack"], None),
    ("fantasy", "noob", ["fuzichoco"], None),
    ("fantasy", "illu", ["wlop"], None),
    ("fantasy", "hassaku", ["amano"], None),
    ("woodblock", "illu", [], None),
    ("woodblock", "hassaku", [], None),
    ("artnouveau", "noob", ["mucha"], None),
    ("artnouveau", "illu", ["mucha"], None),
    ("shoujo", "noob", ["kuvshinov"], None),
    ("shoujo", "hassaku", ["mignon"], None),
    ("noir", "noob", ["murata"], None),
    # photoreal: the family's own tags are empty, each row brings its look
    ("photo", "jugg", [], ["black and white photograph", "high contrast", "film noir lighting", "fine grain"]),
    ("photo", "jugg", [], ["pastel color grade", "soft diffused light", "dreamy", "shallow depth of field"]),
    ("photo", "realvis", [], ["cinematic teal and orange grade", "anamorphic lens flare", "shallow depth of field"]),
    ("photo", "realvis", [], ["black and white photo", "leica", "fine grain", "street photography"]),
    ("photo", "cyber", [], ["rainy night street", "wet reflections", "neon signs", "cinematic"]),
    ("photo", "cyber", [], ["natural daylight", "documentary photo", "candid", "soft shadows"]),
    ("photo", "jugglight", [], ["neon night", "bokeh", "moody lighting"]),
    ("photo", "jugglight", [], ["fashion editorial", "studio lighting", "crisp detail"]),
]
PHOTO_LOOK_ID = {  # stable slugs for the photo rows (keyed by their first extra tag)
    "black and white photograph": "noir", "pastel color grade": "pastel", "cinematic teal and orange grade": "teal",
    "black and white photo": "bw", "rainy night street": "rain", "natural daylight": "daylight",
    "neon night": "neon", "fashion editorial": "editorial",
}
PHOTO_LOOK_CS = {"noir": "noir", "pastel": "pastel", "teal": "film teal", "bw": "č/b ulice", "rain": "déšť neon",
                 "daylight": "denní světlo", "neon": "neon", "editorial": "editorial"}

# Existing presets: family + audiences (by hand; the preset fields are copied verbatim).
PRESET_META = {
    "clean_webtoon": ("flat", ALL, "Čistý webtoon"),
    "clean_webtoon_noartist": ("flat", ALL, "Čistý webtoon bez autora"),
    "hassaku_soft": ("pastel", ALL, "Hassaku jemný"),
    "photo_juggernaut": ("photo", PHOTO, "Foto Juggernaut"),
    "photo_realvis_film": ("photo", PHOTO, "Foto film RealVis"),
    "photo_cyberreal_night": ("photo", PHOTO, "Foto noc CyberReal"),
    "watercolor_paris": ("watercolor", ALL, "Akvarel Paříž"),
    "art_nouveau_mucha": ("artnouveau", ALL, "Secese Mucha"),
    "western_comic": ("comic", ALL, "Západní komiks"),
    "manga_mono": ("ink", ALL, "Manga č/b"),
    "webtoon_romance": ("shoujo", ["harlequin", "free"], "Webtoon romance"),
    "webtoon_romance_artist": ("shoujo", ["harlequin", "free"], "Webtoon romance WLOP"),
    "painterly_oil": ("painterly", ALL, "Olejomalba"),
    "retro_citypop": ("retro90s", ALL, "Retro city pop"),
    "minimal_flat": ("flat", ALL, "Minimalismus"),
    "photo_lightning": ("photo", PHOTO, "Foto rychlé"),
    "ink_wash": ("ink", ALL, "Tušová malba"),
    "noir_mono": ("noir", ADULT, "Noir č/b"),
    "ligne_claire": ("comic", ALL, "Ligne claire"),
    "pastel_shoujo": ("pastel", ALL, "Pastelové šódžo"),
    "vintage_poster": ("retro90s", ALL, "Retro plakát"),
    "ukiyoe": ("woodblock", ALL, "Ukijoe"),
    "fashion_editorial": ("photo", PHOTO, "Módní editorial"),
    "photo_glossy": ("photo", PHOTO, "Foto lesklé"),
    "semireal_25d": ("painterly", ADULT, "Poloreál 2.5D"),
    "fantasy_colorlines": ("fantasy", ALL, "Fantasy barevné linky"),
    "thin_paint": ("painterly", ALL, "Tenká malba"),
    "anime_screencap": ("cel", ALL, "Anime screencap"),
    "flat_anime_mema": ("flat", ALL, "Ploché anime MeMa"),
    "pixar_3d": ("render3d", ADULT, "Pixar 3D"),  # its tags ask for "stylized adult characters"
}

PRESET_KEYS = ["checkpoint", "prediction", "natural", "artist_tags", "aesthetic_tags", "quality_pos", "quality_neg",
               "sampler", "scheduler", "steps", "cfg", "loras"]


def artist_tag(key):
    tag, w, _, _ = ARTISTS[key]
    tag = tag.replace("(", r"\(").replace(")", r"\)")  # ComfyUI weight syntax: literal parens must be escaped
    return f"(artist:{tag}:{w})"


def ckpt_key(file):
    return next((k for k, v in CKPT.items() if v[0] == file), None)


def audiences_for(checkpoint, base, artists=()):
    """Applies the human-checkpoint rules on top of the family's audiences."""
    if NONHUMAN_ONLY.search(checkpoint):
        return []
    k = ckpt_key(checkpoint)
    aud = [a for a in base if a in PHOTO] if k in PHOTO_CKPTS else list(base)
    if any(not ARTISTS[a][2] for a in artists):
        aud = [a for a in aud if a != "kids"]
    return aud


def preset_fields(p):
    """Preset dict with the styles.json key order (optional keys only when present)."""
    out = {}
    for k in PRESET_KEYS:
        if k in p and (k not in ("natural", "loras") or p[k]):
            out[k] = p[k]
    for k in p:  # anything styles.json grows later is carried over untouched
        out.setdefault(k, p[k])
    return out


# --- LoRA axis -------------------------------------------------------------------------------------------------
# Allowlist of SFW SDXL-family LoRAs on Spark (names relative to ComfyUI/models/loras, as /object_info lists them).
# Nothing outside it may ever be referenced: the disk also holds Flux/Pony/video/NSFW/character/personal files.
ANIME_CKPTS = {"noob", "hassaku", "illu", "anim"}
# short → (file, family, Czech name, tags added to aesthetic_tags, checkpoints, strengths, audiences, scenes_only)
STYLE_LORAS = {
    "screencap": ("style-anime-screencap.safetensors", "cel", "Anime screencap",
                  ["anime screencap", "anime coloring", "cel shading"], ["noob", "illu", "hassaku"], [0.6, 0.9], ALL, None),
    "gothic": ("style-gothic-niji.safetensors", "gothic", "Gotika niji",
               ["gothic", "dark fantasy", "ornate", "dramatic lighting"], ["noob", "illu", "hassaku"], [0.6, 0.9], ADULT, None),
    "illupack": ("style-illustrious-pack.safetensors", "stylepack", "Illustrious pack",
                 ["illustration", "detailed background", "vibrant colors"], ["illu", "hassaku", "noob"], [0.6, 0.9], ALL, None),
    "thinpaint": ("style-usnr-thin-paint.safetensors", "painterly", "Tenká malba",
                  ["usnr", "thin paint", "painterly", "soft brush strokes"], ["noob", "illu", "hassaku"], [0.6, 0.9], ALL, None),
    "realism": ("style-realism-slider.safetensors", "semireal", "Realism slider",  # a slider: 1.5 is its usual push
                ["realistic", "semi-realistic", "2.5d", "detailed face"], ["illu", "noob", "hassaku"], [0.9, 1.5], ADULT, None),
    "mema": ("NoobAI/MeMaXL_Flat_Anime_Style_-_NoobIllustriousPonyXL.safetensors", "flat", "MeMa ploché anime",
             ["flat color", "flat anime style", "clean lineart"], ["noob", "illu", "hassaku"], [0.6, 0.9], ALL, None),
    "aidump": ("NoobAI/AI_styles_dump_AnimaIllustriousRouWeiNoob.safetensors", "stylepack", "AI styles dump",
               ["illustration", "vibrant colors"], ["noob", "illu"], [0.6, 0.9], ALL, None),
    "velvets": ("Illustrious_WAI/Velvets_Mythic_Fantasy_Styles__Flux__Pony__illustrious__ZiT__Anima__Krea2.safetensors",
                "fantasy", "Velvet fantasy", ["c0lorl1nes", "fantasy illustration", "vibrant colored lines", "glowing light"],
                ["illu", "noob", "hassaku"], [0.6, 0.9], ALL, None),
    "pixaril": ("Pixar_Illustrious/Pixar_Illustrious.safetensors", "render3d", "Pixar Illustrious",
                ["3d", "pixar style", "cinematic lighting"], ["illu", "noob", "hassaku"], [0.6, 0.9], ALL, None),
    "pixarxl": ("Pixar_SDXL/PixarXL.safetensors", "render3d", "PixarXL",
                ["3d", "pixar style", "cinematic lighting"], ["illu", "noob"], [0.6, 0.9], ALL, None),
    "spacecraft": ("Spacecraft.safetensors", "scifi", "Vesmírné lodě",  # landscape / sci-fi only
                   ["science fiction", "spacecraft", "flying", "sky"], ["noob", "illu"], [0.6, 0.9], ["superhero"],
                   ["d_landscape"]),
}
# SDXL-base style LoRAs (loras/SDXL_style/, sha256-verified from Hugging Face). Trained on SDXL base, so they may
# transfer weaker to the anime checkpoints: each one on Illustrious + NoobAI at 0.7 and 1.0, trigger word in the tags.
SDXL_STYLE = {
    "pixelxl": ("SDXL_style/pixel-art-xl.safetensors", "pixel", "Pixel art XL", ["pixel art", "limited palette"]),
    "watercolorxl": ("SDXL_style/watercolor_v1_sdxl.safetensors", "watercolor", "Akvarel XL",
                     ["watercolor", "watercolor (medium)", "paper texture"]),
    "crayonxl": ("SDXL_style/crayons_v1_sdxl.safetensors", "crayon", "Pastelky XL", ["crayon drawing", "crayon (medium)"]),
    "kidsbook": ("SDXL_style/StorybookRedmondV2-KidsBook-KidsRedmAF.safetensors", "storybook", "Kids book Redmond",
                 ["KidsRedmAF", "kids book", "storybook illustration"]),
    "lineani": ("SDXL_style/LineAniRedmond-LineAniAF.safetensors", "ink", "LineAni Redmond",
                ["LineAniAF", "lineart", "manga"]),
    "coloring": ("SDXL_style/ColoringBookRedmond-ColoringBook-ColoringBookAF.safetensors", "coloringbook",
                 "Omalovánky Redmond", ["ColoringBookAF", "coloring book", "lineart", "monochrome"]),
    "toy": ("SDXL_style/ToyRedmond-FnkRedmAF.safetensors", "toy", "Hračky Redmond", ["FnkRedmAF", "toy", "figurine"]),
    "clay": ("SDXL_style/ClayAnimationRedm.safetensors", "clay", "Plastelína Redmond",
             ["Clay Animation", "claymation", "clay"]),
    "stickers": ("SDXL_style/StickersRedmond.safetensors", "stickers", "Samolepky Redmond",
                 ["Stickers", "sticker", "white outline"]),
    "render3dxl": ("SDXL_style/3d_render_style_xl.safetensors", "render3d", "3D render XL", ["3d style", "3d"]),
    "papercutxl": ("SDXL_style/papercut.safetensors", "papercut", "Papercut XL", ["papercut", "paper cutout", "layered paper"]),
    "storyboard": ("SDXL_style/Storyboard_sketch.safetensors", "sketch", "Storyboard skica",
                   ["storyboard sketch", "sketch", "monochrome"]),
}
for _k, (_f, _fam, _cs, _tags) in SDXL_STYLE.items():
    STYLE_LORAS[_k] = (_f, _fam, _cs, _tags, ["illu", "noob"], [0.7, 1.0], ALL, None)
# The SDXL-base ones may also go on the photoreal checkpoints (adult casts → harlequin/free): (short, ckpt, strength)
SDXL_ON_PHOTO = [("watercolorxl", "realvis", 0.7), ("papercutxl", "jugg", 0.7), ("clay", "realvis", 0.7),
                 ("render3dxl", "jugg", 0.7)]
# Photo presets' negatives that would fight a stylised look (watercolour, clay, 3d) on a photoreal checkpoint.
STYLIZED_NEG = {"anime", "cartoon", "illustration", "drawing", "painting", "3d render", "cgi", "doll", "plastic skin",
                "airbrushed"}

# short → (file, checkpoints it may go on)
QUALITY_LORAS = {
    "masterpiece": ("NoobAI/Aesthetic_Quality_Modifiers_-_Masterpiece.safetensors", ANIME_CKPTS),
    "detailer": ("NoobAI/NoobAI-XL_Detailer.safetensors", ANIME_CKPTS),
    "stabilizer": ("NoobAI/Stabilizer_ILNAICK.safetensors", ANIME_CKPTS),
    "smooth": ("Illustrious_WAI/Smooth_Detailer_Booster_AnimaSDXLPony.safetensors", ANIME_CKPTS),
    "detailtweak": ("Juggernaut_XL_Lightning/Detail_Tweaker_XL.safetensors", PHOTO_CKPTS),
    "moreart": ("Juggernaut_XL_Lightning/xl_more_art-full__xl_real__Enhancer.safetensors", PHOTO_CKPTS),
}
LORA_ALLOWLIST = {v[0] for v in STYLE_LORAS.values()} | {v[0] for v in QUALITY_LORAS.values()}
# Style LoRA rows that also get one quality LoRA: (style, ckpt, strength, quality, quality strength)
STYLE_PLUS_QUALITY = [
    ("screencap", "noob", 0.6, "stabilizer", 0.4),
    ("screencap", "illu", 0.6, "detailer", 0.4),
    ("gothic", "noob", 0.6, "smooth", 0.4),
    ("illupack", "illu", 0.6, "masterpiece", 0.5),
    ("thinpaint", "noob", 0.6, "masterpiece", 0.4),
    ("realism", "illu", 0.9, "detailer", 0.4),
    ("mema", "illu", 0.6, "stabilizer", 0.4),
    ("aidump", "noob", 0.6, "smooth", 0.4),
    ("velvets", "noob", 0.6, "detailer", 0.3),
    ("pixaril", "illu", 0.6, "smooth", 0.4),
    ("pixarxl", "illu", 0.6, "masterpiece", 0.4),
    ("spacecraft", "noob", 0.6, "detailer", 0.4),
]
# Quality-LoRA-only variants of the strongest existing presets: (preset, [(quality, strength), …])
PRESET_QUALITY = [
    ("clean_webtoon", [("stabilizer", 0.4)]),
    ("clean_webtoon", [("masterpiece", 0.5)]),
    ("clean_webtoon_noartist", [("stabilizer", 0.4)]),
    ("clean_webtoon_noartist", [("detailer", 0.4)]),
    ("hassaku_soft", [("smooth", 0.4)]),
    ("watercolor_paris", [("detailer", 0.4)]),
    ("western_comic", [("detailer", 0.4)]),
    ("webtoon_romance", [("masterpiece", 0.4)]),
    ("anime_screencap", [("stabilizer", 0.4)]),
    ("flat_anime_mema", [("masterpiece", 0.4)]),
    ("pastel_shoujo", [("smooth", 0.4), ("detailer", 0.3)]),
    ("photo_juggernaut", [("detailtweak", 0.5)]),
    ("photo_realvis_film", [("moreart", 0.5)]),
    ("photo_cyberreal_night", [("detailtweak", 0.5)]),
    ("photo_lightning", [("detailtweak", 0.4)]),
]
FAMILIES.update({
    "gothic": ("Gotika", [], ADULT),
    "stylepack": ("Stylový balík", [], ALL),
    "semireal": ("Poloreál", [], ADULT),
    "scifi": ("Sci-fi", [], ["superhero"]),
    "coloringbook": ("Omalovánky", [], ALL),
    "toy": ("Hračky", [], ALL),
    "clay": ("Plastelína", [], ALL),
    "stickers": ("Samolepky", [], ALL),
})


def s10(x):
    """0.6 → "06", 1.5 → "15": strength in an id without a dot (ids are also file and CSS names)."""
    return f"{round(x * 10):02d}"


def check_loras(cand):
    """The allowlist and the checkpoint rules, enforced on every candidate (presets included)."""
    k = ckpt_key(cand["checkpoint"])
    style_files = {v[0]: s for s, v in STYLE_LORAS.items()}
    q_files = {v[0]: v[1] for v in QUALITY_LORAS.values()}
    for f, w in cand.get("loras") or []:
        assert f in LORA_ALLOWLIST, f"{cand['id']}: LoRA {f} not in the SFW allowlist"
        if f in style_files:
            s = style_files[f]
            if k in PHOTO_CKPTS:
                assert s in SDXL_STYLE and set(cand["audiences"]) <= set(PHOTO), \
                    f"{cand['id']}: style LoRA {f} on a photoreal checkpoint"
            else:
                assert k in ANIME_CKPTS, f"{cand['id']}: style LoRA {f} on a non-anime checkpoint"
            if s in ("realism", "gothic"):
                assert "kids" not in cand["audiences"], f"{cand['id']}: {s} never for kids"
            if s == "spacecraft":
                assert cand.get("scenes_only") == ["d_landscape"], f"{cand['id']}: Spacecraft only for scene d"
        else:
            assert k in q_files[f], f"{cand['id']}: quality LoRA {f} not for {k}"


def lora_candidates(presets, existing):
    out = []
    seen = {json.dumps(preset_fields(c), sort_keys=True, default=str): c["id"]
            for c in existing}  # a row equal to an existing preset (e.g. MeMa 0.9 on NoobAI) is not a new style

    def add(c):
        key = json.dumps({k: v for k, v in c.items() if k not in ("id", "name", "family", "source", "audiences",
                                                                   "scenes_only", "lora_axis")}, sort_keys=True)
        if key in seen:
            return
        seen[key] = c["id"]
        out.append(c)

    def style_row(s, ck, w, q=None):
        file, family, cs, tags, _, _, aud, only = STYLE_LORAS[s]
        f_ck, base_id, ck_cs = CKPT[ck]
        base = presets[base_id]
        if ck in PHOTO_CKPTS:
            base = {**base, "quality_neg": [t for t in base["quality_neg"] if t not in STYLIZED_NEG]}
        p = {**base, "checkpoint": f_ck, "artist_tags": [], "aesthetic_tags": list(tags),
             "loras": [[file, w]] + ([[QUALITY_LORAS[q[0]][0], q[1]]] if q else [])}
        cid = f"{family}_{ck}_lora-{s}-{s10(w)}" + (f"_q-{q[0]}-{s10(q[1])}" if q else "")
        name = f"{cs} {w:g} · {ck_cs}" + (f" + {q[0]} {q[1]:g}" if q else "")
        c = {"id": cid, "name": name, "family": family, "source": "lora", "lora_axis": "style+quality" if q else "style",
             "audiences": audiences_for(f_ck, aud), **({"scenes_only": only} if only else {}), **preset_fields(p)}
        return c

    for s, (_, _, _, _, ckpts, strengths, _, _) in STYLE_LORAS.items():
        for ck in ckpts:
            for w in strengths:
                add(style_row(s, ck, w))
    for s, ck, w in SDXL_ON_PHOTO:
        add(style_row(s, ck, w))
    for s, ck, w, q, qw in STYLE_PLUS_QUALITY:
        add(style_row(s, ck, w, (q, qw)))
    for pid, qs in PRESET_QUALITY:
        base = presets[pid]
        family, aud, name = PRESET_META[pid]
        p = {**base, "loras": (base.get("loras") or []) + [[QUALITY_LORAS[q][0], w] for q, w in qs]}
        cid = pid + "_" + "_".join(f"q-{q}-{s10(w)}" for q, w in qs)
        add({"id": cid, "name": name + " + " + " + ".join(f"{q} {w:g}" for q, w in qs), "family": family,
             "source": "lora", "lora_axis": "quality", "audiences": audiences_for(base["checkpoint"], aud),
             **preset_fields(p)})
    return out


def candidates(styles):
    presets = styles["presets"]
    out = []
    for pid, p in presets.items():
        family, aud, name = PRESET_META.get(pid, ("other", ALL, pid))
        out.append({"id": pid, "name": name, "family": family, "source": "preset",
                    "audiences": audiences_for(p["checkpoint"], aud), **preset_fields(p)})
    for family, ck, artists, extra in COMBOS:
        fam_cs, fam_tags, fam_aud = FAMILIES[family]
        file, base_id, ck_cs = CKPT[ck]
        base = presets[base_id]
        if ck in PHOTO_CKPTS:
            slug = PHOTO_LOOK_ID[extra[0]]
            cid, name = f"photo_{ck}_{slug}", f"Foto {PHOTO_LOOK_CS[slug]} · {ck_cs}"
        else:
            cid = "_".join([family, ck, *artists])
            name = " · ".join([fam_cs, ck_cs, *(ARTISTS[a][3] for a in artists)])
        p = {**base, "checkpoint": file, "artist_tags": [artist_tag(a) for a in artists],
             "aesthetic_tags": fam_tags + (extra or [])}
        p.pop("loras", None)  # the base preset's LoRA belongs to its look, not to the checkpoint
        aud = audiences_for(file, fam_aud, artists)
        assert aud or NONHUMAN_ONLY.search(file), f"{cid}: no audience left"
        out.append({"id": cid, "name": name, "family": family, "source": "combo", "audiences": aud, **preset_fields(p)})
    out += lora_candidates(presets, out)
    for c in out:
        check_loras(c)
    ids = [c["id"] for c in out]
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f"duplicate candidate ids: {dup}"
    return out


# --- test scenes -------------------------------------------------------------------------------------------------
# Synthetic world fragments in the pipeline's own shape (stories_kids.char / stories_romance.char), so
# prompts.build() makes the same prompt it would make for a real episode.

def char(id, count, tags, photo=None):
    c = {"id": id, "name": id, "role": "playable" if count else "npc", "count_tag": count, "human": bool(count),
         "description": photo or id, "tag_prompt": tags, "identity_level": "prompt", "reference_images": []}
    if photo:
        c["photo"] = photo
    return c


def loc(id, tags):
    return {"id": id, "name": id, "description": id, "tag_prompt": tags, "mood": ""}


SCENES = [
    {"id": "a_kid_creature", "name": "Dítě a tvor – dobrodružství", "seed": 410101, "audience": "kids",
     "requires": ["kids"], "orientation": "portrait",
     "characters": [
         char("kid", "1girl", "female child, (brown hair:1.3), short hair, brown eyes, determined face, red cape, "
                              "white tunic, brown belt, leather boots, holding staff"),
         char("dragon", "", "dragon, small dragon, green scales, big eyes, small wings, small horns, cute expression")],
     "locations": [loc("l_forest", "outdoors, forest, ancient ruins, mossy stones, sunbeams, path, adventure")],
     "panel": {"shot": "medium", "location_id": "l_forest", "characters": [{"id": "kid"}, {"id": "dragon"}],
               "visual_tags": ["smile", "looking at another", "walking", "pointing forward", "adventure"]}},
    {"id": "b_woman_portrait", "name": "Žena – portrét, večerní město", "seed": 420202, "audience": "adult",
     "requires": ADULT, "orientation": "portrait",
     "characters": [
         char("woman", "1girl", "adult, mature female, long hair, (dark brown hair:1.3), wavy hair, brown eyes, "
                                "red lips, beige trench coat, scarf",
              photo="a woman in her early thirties with long wavy dark brown hair and brown eyes, beige trench coat, "
                    "silk scarf")],
     "locations": [loc("l_city", "outdoors, city, evening, street lights, bokeh, buildings, dusk, orange sky")],
     "panel": {"shot": "close-up", "location_id": "l_city", "characters": [{"id": "woman"}],
               "visual_tags": ["looking at viewer", "light smile", "wind", "hair blowing"]}},
    {"id": "c_couple_romance", "name": "Pár – romantika (SFW)", "seed": 430303, "audience": "adult",
     "requires": ADULT, "orientation": "portrait",
     "characters": [
         char("her", "1girl", "adult, mature female, long hair, (blonde hair:1.3), blue eyes, white blouse, long skirt",
              photo="a woman in her late twenties with long blonde hair and blue eyes, white blouse, long skirt"),
         char("him", "1boy", "adult, mature male, short hair, (black hair:1.3), grey eyes, stubble, navy coat, white shirt",
              photo="a man in his early thirties with short black hair, grey eyes and light stubble, navy coat, white shirt")],
     "locations": [loc("l_bridge", "outdoors, bridge, river, evening, string lights, city lights, water reflection")],
     "panel": {"shot": "medium", "location_id": "l_bridge", "characters": [{"id": "her"}, {"id": "him"}],
               "visual_tags": ["couple", "hetero", "holding hands", "looking at another", "smile", "blush"]}},
    {"id": "d_landscape", "name": "Krajina – úvodní záběr", "seed": 440404, "audience": "teen",
     "requires": [], "orientation": "landscape",
     "characters": [],
     "locations": [loc("l_valley", "outdoors, mountains, valley, river, village, forest, clouds, sunrise, "
                                   "dramatic sky, detailed background")],
     "panel": {"shot": "establishing", "location_id": "l_valley", "characters": [], "visual_tags": ["scenery"]}},
]


def main():
    styles = load_json(DATA / "styles.json")
    cands = candidates(styles)
    save_json(OUT_DIR / "candidates.json", {
        "_note": "Generated by m0/style_bench_gen.py — edit the generator, not this file. Preset fields have the "
                 "exact data/styles.json shape; id/name/family/source/audiences are benchmark metadata.",
        "audiences": {"kids": "děti", "harlequin": "dospělá romance", "superhero": "akce, teen + dospělí",
                      "free": "volný svět, dospělí"},
        "families": {k: v[0] for k, v in FAMILIES.items()},
        "candidates": cands})
    save_json(OUT_DIR / "scenes.json", {
        "_note": "Fixed benchmark scenes (style_bench_gen.py). A candidate renders a scene when its audiences "
                 "intersect `requires` (empty = always). `audience` is the synthetic world's audience for prompts.build "
                 "and the WD14 safety thresholds.",
        "scenes": SCENES})
    by = lambda key: {k: sum(1 for c in cands if key(c) == k) for k in sorted({key(c) for c in cands})}
    print(f"{len(cands)} candidates → {OUT_DIR / 'candidates.json'}")
    print("by checkpoint:", by(lambda c: c["checkpoint"].removesuffix(".safetensors")))
    print("by family:", by(lambda c: c["family"]))
    print("by audience:", {a: sum(a in c["audiences"] for c in cands) for a in ALL})
    print("by source:", by(lambda c: c["source"]), "lora axis:", by(lambda c: c.get("lora_axis") or "-"))


if __name__ == "__main__":
    main()
