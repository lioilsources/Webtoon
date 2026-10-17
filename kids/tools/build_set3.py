"""Builds kids/stories/11–15 (third set): Juggernaut, FLUX and Pony with LoRAs; pets speak in pictogram bubbles."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "stories"


def P(shot, loc, chars, tags, scene, bubbles=(), sfx=(), gap="medium", **kw):
    return {"shot": shot, "location_id": loc, "characters": [{"id": c} for c in chars], "visual_tags": tags,
            "scene_en": scene, "bubbles": list(bubbles), "sfx": [{"text": s} for s in sfx], "gap_after": gap, **kw}


def S(t, who=None): return {"kind": "speech", "speaker": who, "text": t}
def SH(t, who=None): return {"kind": "shout", "speaker": who, "text": t}
def R(t, who=None): return {"kind": "radio", "speaker": who, "text": t}
def N(t): return {"kind": "narration", "speaker": None, "text": t}
def PET(t, icon, who, tr=None):
    b = {"kind": "pet", "speaker": who, "text": t, "icon": icon}
    if tr:
        b["translation"] = tr
    return b
def C(id, name, count, tags, desc): return {"id": id, "name": name, "count_tag": count, "tag_prompt": tags, "desc_en": desc}
def L(id, tags, desc): return {"id": id, "tag_prompt": tags, "desc_en": desc}


def save(name, wid, title, style, chars, locs, panels):
    d = {"world": {"id": wid, "title": title, "audience": "kids", "language": "cs", "style_id": style,
                   "characters": chars, "locations": locs},
         "storyboard": {"title": title, "panels": panels}}
    (OUT / f"{name}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(name, len(panels), "panels")


# --- 11 --------------------------------------------------------------------
save("11_kolac", "k_cake", "Ztracený recept na nejlepší koláč", "juggernaut_pixar", [
    C("elenka", "Elenka", "1girl", "child, brown hair, two buns, freckles, big smile, yellow dress, white apron, flour on clothes",
      "Elenka, an energetic smiling 8-year-old girl with brown hair in two buns, freckles, a yellow dress and a white apron dusted with flour"),
    C("mopik", "Mopík", None, "pug, fat dog, fawn fur, black muzzle, curly tail",
      "Mopik, a chubby lazy fawn pug with a black wrinkly face and a curly tail"),
    C("babicka", "Babička Lubomíra", "1girl", "old woman, grey hair, hair bun, glasses, floral dress, cardigan, smile",
      "Grandma Lubomira, a cheerful plump 65-year-old woman with grey hair in a bun, round glasses, a floral dress and a cardigan"),
], [L("kitchen", "indoors, kitchen, old kitchen, wooden table, rolling pin, bowls, flour, sunlight",
      "An old sunlit country kitchen, rolling pins and bowls on a wooden table, flour spilled all over the floor."),
    L("hall", "indoors, hallway, wooden floor, wicker basket, door, coat rack, warm lighting",
      "The hallway of an old cottage with a wooden floor and an old wicker basket by the door.")], [
    P("establishing", "kitchen", [], ["no humans", "flour on floor", "shelves", "window"],
      "a cozy old sunlit kitchen with rolling pins, mixing bowls and flour scattered everywhere, empty of people",
      [N("Sluncem zalitá starodávná kuchyně.")], gap="small"),
    P("wide", "kitchen", ["elenka", "mopik"], ["standing on stool", "reaching up", "shelf", "dog under table"],
      "Elenka stands on tiptoes on a wooden stool stretching up towards a high shelf, the pug lies under the table below",
      [S("Mopíku, ještě kousek! Babiččin tajný recept na jahodový koláč musí být někde tady nahoře!", "elenka")]),
    P("close-up", "kitchen", ["mopik"], ["no humans", "pug", "flour on nose", "sneezing", "looking up"],
      "close-up of the pug lying on the floor with a dusting of white flour on his nose, sneezing and looking up hopefully, wagging his tail",
      [PET("Haf! Haf!", "bone", "mopik", "Raději mi hoď ten kousek másla!")], ["PČÍK!"]),
    P("wide", "hall", ["mopik"], ["no humans", "pug", "head in basket", "wicker basket", "sniffing"],
      "the pug pushes his nose deep into an old wicker basket by the door in the hallway",
      [N("Mopík strčí čenich do starého proutěného koše.")], ["čmuch čmuch"]),
    P("medium", "hall", ["elenka", "mopik"], ["pug", "holding paper in mouth", "rolled paper", "ribbon", "clapping", "happy"],
      "the pug holds a yellowed rolled-up paper tied with a red ribbon in his mouth, Elenka claps her hands in delight",
      [S("Ty jsi génius! Našel jsi ho! Babička bude koukat!", "elenka")]),
    P("medium", "hall", ["babicka"], ["shopping bag", "surprised", "smile", "doorway"],
      "grandma comes into the hallway carrying a shopping bag, surprised and smiling",
      [S("Co to tady vy dva vyvádíte?", "babicka"), S("Jéje, vy jste našli recept mé prababičky!", "babicka")]),
    P("wide", "hall", ["elenka", "babicka", "mopik"], ["pug", "sitting", "proud", "holding paper", "happy", "family"],
      "grandma holds the old recipe and laughs with Elenka while the pug sits proudly waiting for a reward",
      [PET("Haf!", "bone", "mopik", "A teď ta odměna!")]),
])

# --- 12 --------------------------------------------------------------------
save("12_more", "k_reef", "Podmořský třpyt", "flux_pixar", [
    C("maja", "Maja", "1girl", "child, black hair, short hair, turquoise swimsuit, diving mask, snorkel, swim fins",
      "Maja, a brave 10-year-old girl with short black hair in a turquoise swimsuit, diving mask, snorkel and swim fins"),
    C("perlicka", "Perlička", None, "sea otter, brown fur, small animal, holding pearl",
      "Perlicka, a playful little brown sea otter"),
    C("straz", "Korálový strážce", None, "octopus, giant octopus, purple, wise, old",
      "the Coral Guardian, a large wise grumpy old purple octopus with bushy eyebrows"),
], [L("reef", "underwater, coral reef, light rays, clear water, fish, bubbles",
      "Clear tropical coral sea, sunbeams shining through the water and drawing light patterns on the sandy bottom."),
    L("cave", "underwater, cave, glowing coral, shipwreck, throne, dark, bioluminescence",
      "An underwater cave full of glowing corals, a throne made from an old shipwreck in the middle.")], [
    P("establishing", "reef", [], ["no humans", "fish", "sand"],
      "a crystal clear coral reef with sunbeams shining through the water, colorful fish, no people",
      [N("Průzračné korálové moře.")], gap="small"),
    P("wide", "reef", ["maja", "perlicka"], ["swimming", "underwater", "pointing", "otter", "glowing pearl"],
      "Maja swims underwater with snorkel and fins, pointing towards a dark cave, while the sea otter does a somersault next to her holding a glowing blue pearl",
      [S("Perličko, podívej! Tam odtud vychází to divné světlo.", "maja")]),
    P("medium", "reef", ["perlicka"], ["no humans", "otter", "holding pearl", "glowing", "bubbles", "excited"],
      "the little sea otter holds up a glowing blue pearl like a lantern towards the cave, blowing bubbles",
      [PET("Píísk! Píísk!", "pearl", "perlicka", "Počkej na mě, mám světlo!")], ["blub blub"]),
    P("establishing", "cave", ["straz"], ["octopus", "throne", "glowing coral"],
      "inside an underwater cave full of glowing corals, a big old octopus sits on a throne made from a shipwreck",
      [N("Jeskyně plná svítících korálů.")], gap="small"),
    P("medium", "cave", ["straz"], ["octopus", "crossed arms", "stern", "glowing coral"],
      "the big wise octopus crosses several tentacles and looks down sternly",
      [S("Kdo se odvažuje vstoupit do Jeskyně vzpomínek?", "straz")]),
    P("wide", "cave", ["maja", "perlicka", "straz"], ["otter", "giving pearl", "pointing", "smile", "octopus"],
      "the sea otter carefully places her glowing pearl in front of the octopus as a gift, Maja points at the otter and smiles",
      [S("Jsme kamarádky! Hledáme ztracenou hvězdu z oceánské koruny!", "maja")]),
    P("medium", "cave", ["straz", "perlicka"], ["octopus", "smile", "raised tentacle", "otter", "glowing"],
      "the old octopus smiles and raises one tentacle in welcome, the otter beams",
      [S("Vydra s tak čistým srdcem tu dlouho nebyla. Vstupte!", "straz")]),
])

# --- 13 --------------------------------------------------------------------
save("13_orbita", "k_orbit", "Záchrana na oběžné dráze", "atomix_space", [
    C("viktorie", "Viktorie", "1girl", "child, orange hair, ponytail, freckles, white spacesuit, goggles on head, oil on face",
      "Viktorie, a brilliant 12-year-old mechanic with an orange ponytail, freckles and a white space suit, welding goggles on her forehead"),
    C("pixel", "Pixel", None, "orange cat, two tails, alien cat, glowing eyes",
      "Pixel, a ginger alien cat with two tails"),
    C("daniel", "Kapitán Daniel", "1boy", "adult, man, short brown hair, beard, captain uniform, headset",
      "Captain Daniel, a calm man with short brown hair and a beard in a captain's uniform with a headset"),
], [L("cockpit", "indoors, spaceship interior, cockpit, control panel, red light, warning lights, science fiction",
      "The cockpit of a spaceship with red warning lights flashing."),
    L("hull", "outdoors, space, spaceship hull, earth (planet), stars, science fiction",
      "The outer hull of a spaceship in open space, planet Earth glowing in the distance."),
    L("bridge", "indoors, space station, bridge, monitors, science fiction, blue light",
      "The command bridge of space station Alpha.")], [
    P("establishing", "cockpit", [], ["no humans", "alarm", "red light"], "a spaceship cockpit with red alarm lights flashing",
      [N("Řídící kabina vesmírné lodi. Bliká alarm.")], ["UÍÍ… UÍÍ…"], gap="small"),
    P("medium", "cockpit", ["viktorie"], ["kneeling", "open panel", "machinery", "wiping forehead", "wrench"],
      "Viktorie kneels at an open engine service panel, wiping oil from her forehead",
      [S("Pixeli, co se děje? Hlavní počítač nehlásí žádnou chybu!", "viktorie")]),
    P("medium", "cockpit", ["pixel"], ["no humans", "cat", "two tails", "fur standing on end", "jumping", "control panel", "sparks"],
      "the ginger two-tailed cat with bristling fur jumps onto the main control panel, both tails pointing at the right fan",
      [PET("Mňau-mňau! Zzzzt!", "bolt", "pixel", "Tamhle! Ventilátor!")]),
    P("establishing", "hull", [], ["no humans", "spaceship", "planet", "space"], "the outer hull of a spaceship in space, Earth glowing far away",
      [N("Venku ve volném vesmíru.")], gap="small"),
    P("wide", "hull", ["viktorie", "pixel"], ["spacewalk", "space helmet", "repairing", "cat in space helmet", "floating", "holding tool in mouth"],
      "Viktorie in a space helmet clings magnetically to the hull replacing a burnt part, the cat in a tiny helmet floats beside her holding a tool in his mouth"),
    P("medium", "bridge", ["daniel"], ["headset", "serious", "monitors", "talking"],
      "Captain Daniel speaks into his headset on the station bridge, worried",
      [R("Viktorie, zbývají dvě minuty do průletu meteoritickým polem! Zvládáš to?", "daniel")]),
    P("close-up", "hull", ["viktorie"], ["space helmet", "determined", "smile", "screwdriver", "stars"],
      "close-up of Viktorie inside her helmet tightening a bolt, smiling with determination",
      [S("Už to bude, tati! Pixel našel uvolněný kabel dřív než senzory!", "viktorie")]),
    P("medium", "hull", ["pixel"], ["no humans", "cat", "two tails", "space helmet", "floating", "closed eyes", "content"],
      "the ginger cat floats in his tiny space helmet next to the ship, eyes closed, purring",
      [PET("Purrr…", "heart", "pixel")]),
])

# --- 14 --------------------------------------------------------------------
save("14_hrad", "k_castle", "Tajemství starého hradu", "flux_manga", [
    C("klarka", "Klárka", "1girl", "child, blonde hair, braid, oversized sweater, knitted sweater, holding flashlight",
      "Klarka, a curious 9-year-old girl with a blonde braid in a far too big knitted sweater, holding a flashlight"),
    C("hugo", "Hugo", None, "owl, eagle owl, orange eyes, ear tufts, brown feathers",
      "Hugo, a big Eurasian eagle-owl with orange eyes and ear tufts"),
    C("jaromir", "Rytíř Jaromír", None, "ghost, knight, armor, translucent, glowing, blue",
      "Sir Jaromir, a kind translucent glowing blue ghost knight in old armor"),
], [L("library", "indoors, castle, library, bookshelf, cobweb, dark, flashlight beam",
      "A huge dark castle library full of cobwebs, tall bookshelves and old books."),
    L("passage", "indoors, castle, secret passage, stone wall, blue light, dust, grandfather clock",
      "A secret stone passage behind the library, dusty air glowing blue, an old grandfather clock.")], [
    P("establishing", "library", [], ["no humans", "books", "cobweb"], "a huge dark castle library with tall bookshelves and cobwebs",
      [N("Obří hradní knihovna plná pavučin.")], gap="small"),
    P("medium", "library", ["klarka", "hugo"], ["owl on shoulder", "flashlight", "whispering", "head turned"],
      "Klarka shines her flashlight at the wall between the books, the owl sits on her shoulder with his head turned all the way round",
      [S("Hugo, osvětli tu horní polici. Určitě tu musí být tajné tlačítko.", "klarka")]),
    P("medium", "library", ["hugo"], ["no humans", "owl", "flying", "coat of arms", "stone lion", "pecking"],
      "the owl flaps up to a family coat of arms on the wall and pecks at the stone lion on it",
      [PET("Húúú! Húúú!", "moon", "hugo", "Tady! Ten lev!")], ["ŤUK!"]),
    P("establishing", "passage", [], ["no humans", "secret passage", "open bookshelf"],
      "the bookshelf swings open revealing a secret stone passage glowing with blue light",
      [N("Za knihovnou se otevře tajná chodba.")], ["SKŘÍÍÍP"], gap="small"),
    P("wide", "passage", ["klarka", "jaromir", "hugo"], ["ghost", "emerging from wall", "surprised", "jumping back", "owl on head"],
      "a glowing translucent ghost knight emerges from the stone wall, Klarka jumps back in surprise while the owl calmly lands on the knight's helmet"),
    P("medium", "passage", ["jaromir", "hugo"], ["ghost", "floating", "scratching head", "owl on head", "friendly"],
      "the friendly ghost knight floats and scratches his helmet, the owl sitting on top",
      [S("Ahoj malá průzkumnice! Neviděla jsi tady někde moje klíče od komnaty?", "jaromir"), S("Hledám je už stovka let!", "jaromir")]),
    P("medium", "passage", ["klarka"], ["smile", "pointing", "flashlight", "grandfather clock"],
      "Klarka smiles and points at an old grandfather clock",
      [S("Nebyly náhodou zavěšené na kyvadle těch starých hodin?", "klarka")]),
    P("close-up", "passage", [], ["no humans", "key", "glowing", "pendulum", "clock"],
      "close-up of a glowing old iron key hanging on the swinging pendulum of a grandfather clock", [], ["tik… tak…"]),
])

# --- 15 --------------------------------------------------------------------
save("15_dynovy_kral", "k_pumpkinking", "Halloweenská noc v Čarodějném lese", "pony_pixar", [
    C("sara", "Sára", "1girl", "child, brown hair, long hair, witch hat, witch costume, purple dress, striped thighhighs, holding broom, pumpkin basket",
      "Sara, a brave 11-year-old girl dressed as a little witch with a pointy hat, purple dress and striped socks, holding a broom and a pumpkin-shaped basket"),
    C("tinek", "Tínek", None, "black cat, kitten, big yellow eyes, scared",
      "Tinek, a very timid little black kitten with huge yellow eyes"),
    C("kral", "Dýňový král", None, "pumpkin head, jack-o'-lantern head, giant, cloak made of autumn leaves, glowing eyes",
      "the Pumpkin King, a giant figure with a glowing carved jack-o'-lantern for a head and a cloak of autumn leaves"),
], [L("forest", "outdoors, night, forest, full moon, fog, jack-o'-lantern, halloween, twisted trees",
      "A Halloween forest at night, full moon, fog creeping over the ground, twisted trees like clawed hands, glowing carved pumpkins everywhere."),
    L("clearing", "outdoors, night, forest clearing, glowing mushrooms, halloween, fog",
      "A forest clearing surrounded by glowing mushrooms.")], [
    P("establishing", "forest", [], ["no humans", "moon", "fog", "pumpkins"],
      "a Halloween forest at night with a full moon, fog and glowing carved pumpkins",
      [N("Halloweenská noc v Čarodějném lese.")], gap="small"),
    P("wide", "forest", ["sara", "tinek"], ["walking", "cat in basket", "peeking", "holding broom", "smile"],
      "Sara walks cheerfully with her broom and pumpkin basket, the black kitten peeks out of the basket with wide eyes",
      [S("Neboj se, Tínku! Dneska je Halloween, všechna strašidla jsou přece jenom převlečení sousedé… nebo ne?", "sara")]),
    P("close-up", "forest", ["tinek"], ["no humans", "kitten", "in basket", "trembling", "scared", "wide-eyed"],
      "close-up of the little black kitten trembling inside the pumpkin basket, only ears and huge eyes showing",
      [PET("M… mňáááu?", "fish", "tinek", "A co byl ten hrozný zvuk za námi?!")]),
    P("establishing", "clearing", ["kral"], ["pumpkin head", "giant", "sack", "candy", "glowing mushrooms"],
      "in a clearing ringed with glowing mushrooms stands the giant Pumpkin King holding a huge sack of sweets",
      [N("Uprostřed mýtiny stojí Dýňový král.")], gap="small"),
    P("wide", "clearing", ["kral", "sara", "tinek"], ["towering", "laughing", "cat on head", "covering eyes"],
      "the Pumpkin King towers over Sara laughing spookily, the kitten has leapt onto her witch hat and covers her eyes with his paws",
      [SH("Muuuhahaha! Kdo se odvažuje žádat o sladkosti v mé noci?!", "kral")]),
    P("medium", "clearing", ["sara", "tinek"], ["holding cat", "holding basket", "brave", "smile"],
      "Sara lifts the kitten off her hat and bravely holds out her basket",
      [S("Koledu, nebo vám něco provedeme! A můj kocour umí strašidelně prskat!", "sara")]),
    P("close-up", "clearing", ["tinek"], ["no humans", "kitten", "hissing", "fur standing on end", "puffed chest", "brave"],
      "close-up of the black kitten puffing out his chest and hissing as bravely as he can",
      [PET("Fíííík! Mňau!", "fish", "tinek")]),
    P("wide", "clearing", ["kral", "sara"], ["laughing", "giant lollipop", "candy", "throwing", "happy"],
      "the Pumpkin King laughs warmly and drops a giant lollipop into Sara's basket",
      [S("To byl ale strašidelný kocour! Tady máte pořádnou odměnu! Šťastný Halloween!", "kral")]),
])
