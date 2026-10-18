"""Five hand-written kids stories → data/stories/<id>/{world,storyboard}.json (no LLM: the script is given).

    python3 m0/stories_kids.py
    python3 m0/render.py --world data/stories/park/world.json --storyboard data/stories/park/storyboard.json --run kids_park
    python3 m0/compose.py --storyboard data/stories/park/storyboard.json --panels out/<day>/kids_park --out strip.png

Humans are drawn with NoobAI (count_tag 1girl/1boy); pets and creatures have no count_tag, so a panel
with animals only gets "no humans". Children are always fully dressed (audience kids → stricter negatives
and the WD14 "sensitive" check).
"""

from common import DATA, save_json


def char(id, name, count, tags, desc=""):
    return {"id": id, "name": name, "role": "playable" if count else "npc", "count_tag": count,
            "human": bool(count), "description": desc, "tag_prompt": tags, "identity_level": "prompt",
            "reference_images": []}


def loc(id, name, tags):
    return {"id": id, "name": name, "description": name, "tag_prompt": tags, "mood": ""}


def panel(shot, loc_id, chars, tags, bubbles=(), sfx=(), gap="medium"):
    return {"shot": shot, "location_id": loc_id, "characters": [{"id": c} for c in chars],
            "visual_tags": [t.strip() for t in tags.split(",") if t.strip()],
            "bubbles": [{"speaker_id": b[0], "text": b[1], "kind": b[2] if len(b) > 2 else "speech"} for b in bubbles],
            "sfx": [{"text": s, "style": "bold"} for s in sfx], "gap_after": gap}


def world(id, title, synopsis, characters, locations):
    return {"id": id, "title": title, "synopsis": synopsis, "tone": "veselý, laskavý", "audience": "kids",
            "language": "cs", "style_id": "clean_webtoon_noartist",
            "bible": {"rules": [], "factions": []}, "canon": {"nodes": [], "constraints": ["Vždy dobrý konec."]},
            "permissions": {"allowed_locations": [l["id"] for l in locations]},
            "characters": characters, "locations": locations}


KID_GIRL = "1girl, female child"

STORIES = {}

# 1. Veselý den v parku --------------------------------------------------------------------------
STORIES["park"] = (
    world("w_park", "Veselý den v parku", "Anička a pes Maxík hledají v parku poklad.", [
        char("anicka", "Anička", "1girl", "female child, (brown hair:1.3), twintails, hair bobbles, brown eyes, "
             "yellow shirt, short sleeves, blue overalls, white socks, red sneakers"),
        char("maxik", "Maxík", "", "dog, small dog, brown dog, floppy ears, red collar"),
        char("novakova", "Paní Nováková", "1girl", "old woman, grey hair, hair bun, glasses, green cardigan, "
             "long skirt, holding basket, bread"),
        char("tomas", "Tomáš", "1boy", "male child, black hair, messy hair, striped shirt, green shorts, "
             "bandaid on nose, sneakers"),
    ], [
        loc("l_park", "Park", "outdoors, park, grass, trees, flowers, path, sunlight, blue sky, morning"),
        loc("l_sand", "Pískoviště", "outdoors, playground, sandbox, sand, park, trees, sunlight"),
        loc("l_bench", "Lavička", "outdoors, park, park bench, trees, flowers, sunlight, afternoon"),
    ]),
    {"title": "Veselý den v parku", "choices": [], "panels": [
        panel("wide", "l_park", ["anicka", "maxik"], "running, holding leash, leash, smile, open mouth, dog running",
              [("anicka", "Maxíku, dnes bude nejlepší den! Pojďme hledat poklad!")]),
        panel("medium", "l_park", ["maxik"], "barking, open mouth, wagging tail, happy, looking at viewer",
              sfx=["HAF! HAF!"], gap="small"),
        panel("medium", "l_sand", ["anicka"], "kneeling, digging, holding shovel, toy shovel, sand on face, excited, "
              "open mouth", [("anicka", "Tohle je mapa! Tady je X!")]),
        panel("wide", "l_park", ["anicka", "maxik"], "dog running, squirrel, pulled by dog, holding leash, "
              "surprised, motion lines, running", sfx=["FRRR!"]),
        panel("wide", "l_park", ["anicka", "tomas"], "collision, ice cream, ice cream cone, dropping, surprised, "
              "open mouth, motion lines, falling", [("tomas", "Ááá! Moje zmrzlina!", "shout")], sfx=["BUM!"],
              gap="small"),
        panel("medium", "l_park", ["anicka"], "apologizing, embarrassed, sweatdrop, hands together, bowing",
              [("anicka", "Promiň! Maxík jen hledal poklad!")]),
        panel("medium", "l_park", ["maxik"], "(dog focus:1.3), (close to viewer:1.2), full body, dog licking "
              "ice cream, (ice cream cone on ground:1.2), melting ice cream, wagging tail, happy, grass",
              sfx=["LÍZ LÍZ"]),
        panel("medium", "l_bench", ["novakova", "anicka"], "sitting on bench, holding cookie, giving, smile, "
              "kind smile", [("novakova", "Tady máte sušenku pro statečného lovce pokladů.")], gap="small"),
        panel("wide", "l_bench", ["anicka", "maxik"], "hugging dog, laughing, closed eyes, happy, dog eating, cookie",
              [("anicka", "Díky! Maxíku, jsi nejlepší pes na světě!")], gap="large"),
    ]},
)

# 2. Dobrodružství u moře -----------------------------------------------------------------------
STORIES["more"] = (
    world("w_more", "Dobrodružství u moře", "Eliška a králík Rybka hledají na pláži nejkrásnější mušli.", [
        char("eliska", "Eliška", "1girl", "female child, black hair, long hair, straw hat, blue eyes, white shirt, "
             "short sleeves, red capri pants, sandals"),
        char("rybka", "Rybka", "", "rabbit, white rabbit, white fur, black spot on ear, long ears"),
        char("deda", "Dědeček", "1boy", "old man, grey hair, white beard, fisherman, bucket hat, blue vest, "
             "rolled up sleeves, rubber boots"),
        char("racek", "Racek", "", "seagull, bird, white feathers"),
    ], [
        loc("l_beach", "Pláž", "outdoors, beach, sand, ocean, waves, seashell, blue sky, clouds, sunlight"),
        loc("l_shore", "U vody", "outdoors, beach, shore, waves, wet sand, seashell, ocean, sunlight"),
        loc("l_fire", "Oheň", "outdoors, beach, campfire, sunset, orange sky, evening, ocean, warm lighting"),
    ]),
    {"title": "Dobrodružství u moře", "choices": [], "panels": [
        panel("wide", "l_beach", ["eliska", "rybka"], "walking, carrying basket, (rabbit in basket:1.3), wicker basket, smile, happy",
              [("eliska", "Rybko, dnes najdeme nejkrásnější mušli!")]),
        panel("medium", "l_beach", ["rybka"], "(rabbit in basket:1.2), wicker basket, grooming, paw on ear, (black spot on ear:1.2), "
              "cute, front view",
              gap="small"),
        panel("medium", "l_shore", ["eliska"], "squatting, picking up seashell, holding seashell, smile"),
        panel("wide", "l_shore", ["rybka"], "jumping, hopping, rabbit running, toward waves, splash",
              sfx=["HOP HOP"], gap="small"),
        panel("medium", "l_shore", ["eliska"], "worried, open mouth, reaching out, outstretched arm",
              [("eliska", "Ne! Voda není pro králíky!", "shout")], gap="small"),
        panel("medium", "l_beach", ["racek"], "(bird focus:1.4), (seagull:1.4), (close to viewer:1.2), white bird, "
              "yellow beak, (seashell in beak:1.3), standing on sand, wings spread",
              sfx=["KRÁÁ!"]),
        panel("medium", "l_shore", ["eliska"], "worried, pointing, shouting, looking back",
              [("eliska", "Dědo, pomoz! Rybka chce plavat!", "shout")], gap="small"),
        panel("medium", "l_shore", ["deda"], "holding fishing net, walking, kind smile, calm",
              [("deda", "Pojď sem, malý hrdino.")]),
        panel("close-up", "l_shore", ["deda", "rybka"], "holding rabbit, gentle, hands, rabbit, scared, wet fur",
              gap="large"),
        panel("wide", "l_fire", ["eliska", "rybka"], "sitting, holding rabbit, rabbit on lap, holding seashell, "
              "big seashell, smile, campfire", [("eliska", "Vidíš? I bez plavání jsme našli poklad.")], gap="large"),
    ]},
)

# 3. Záhada v lese ------------------------------------------------------------------------------
STORIES["les"] = (
    world("w_les", "Záhada v lese", "Terezka a kočka Míša najdou v lese ztraceného skřítka.", [
        char("terezka", "Terezka", "1girl", "female child, blonde hair, short hair, bob cut, green eyes, "
             "orange hoodie, backpack, brown pants, brown boots"),
        char("misa", "Míša", "", "cat, grey cat, grey fur, yellow eyes"),
        char("skritek", "Skřítek", "1boy", "gnome, chibi, tiny, pointy ears, big nose, red pointy hat, white beard, "
             "green tunic"),
        char("sova", "Sova", "", "owl, brown feathers, big eyes"),
    ], [
        loc("l_path", "Lesní stezka", "outdoors, forest, path, tall trees, sunbeam, light rays, moss, nature"),
        loc("l_stump", "Pařez", "outdoors, forest, tree stump, moss, mushrooms, ferns, dappled sunlight"),
        loc("l_house", "Stromový domek", "outdoors, forest, tiny house, house in tree, round door, flowers, "
            "warm lighting, fairy tale"),
    ]),
    {"title": "Záhada v lese", "choices": [], "panels": [
        panel("wide", "l_path", ["terezka", "misa"], "walking, looking down, footprints, curious, cat walking ahead",
              [("terezka", "Míšo, někdo tu nechal stopy. Pojďme je sledovat!")]),
        panel("medium", "l_path", ["misa"], "cat walking, meowing, open mouth, tail up, looking back",
              sfx=["MŇAU"], gap="small"),
        panel("medium", "l_stump", ["terezka"], "squatting, holding scarf, red scarf, small scarf, curious, "
              "head tilt", [("terezka", "Komu patří?")]),
        panel("medium", "l_stump", ["sova"], "owl on branch, perched, tree branch, looking at viewer, wise",
              [("sova", "Húú… tomu, kdo se bojí být sám.")]),
        panel("medium", "l_stump", ["skritek"], "peeking out, climbing out of tree stump, teary eyes, sad, "
              "reaching out", [("skritek", "Můj šátek! Děkuju. Ztratil jsem se.")], sfx=["ŠUST"], gap="small"),
        panel("medium", "l_stump", ["terezka"], "kneeling, holding out red scarf, offering, gentle smile, kind, "
              "looking down", [("terezka", "Neboj se. Míša a já tě dovedeme domů.")]),
        panel("close-up", "l_stump", ["misa"], "cat rubbing, nuzzling, closed eyes, happy, purring",
              sfx=["PRRR"], gap="large"),
        panel("medium", "l_house", ["skritek"], "standing in front of tiny house, holding basket of berries, "
              "red scarf, happy, smile, waving", [("skritek", "Jste nejlepší kamarádky. Tady máte lesní bobule.")],
              gap="small"),
        panel("wide", "l_path", ["terezka", "misa"], "holding basket, berries, smile, happy, cat, walking home, "
              "sunset", [("terezka", "Rádi jsme pomohli!")], gap="large"),
    ]},
)

# 4. Zábavný zmatek v kuchyni -------------------------------------------------------------------
STORIES["kuchyne"] = (
    world("w_kuchyne", "Zábavný zmatek v kuchyni", "Lucka peče sušenky a křeček Puntík jí „pomáhá“.", [
        char("lucka", "Lucka", "1girl", "female child, red hair, braid, freckles, blue eyes, pink apron, "
             "white shirt, long sleeves"),
        char("puntik", "Puntík", "", "hamster, brown hamster, small, round"),
        char("mama", "Máma", "1girl", "mature female, brown hair, ponytail, purple sweater, apron"),
        char("honzik", "Honzík", "1boy", "male child, younger, blonde hair, short hair, blue t-shirt, long pants"),
    ], [
        loc("l_kitchen", "Kuchyně", "indoors, kitchen, table, mixing bowl, flour, cookies, baking, warm lighting, "
            "window"),
    ]),
    {"title": "Zábavný zmatek v kuchyni", "choices": [], "panels": [
        panel("wide", "l_kitchen", ["lucka"], "baking, mixing, holding whisk, smile, happy, flour on table"),
        panel("close-up", "l_kitchen", ["puntik"], "hamster in bowl, sitting, cute, mixing bowl, looking up",
              [("lucka", "Puntíku, ty budeš ochutnávač!")], gap="small"),
        panel("medium", "l_kitchen", ["puntik"], "(covered in flour:1.3), (cloud of flour:1.3), white powder, "
              "flour explosion, hamster jumping into flour, mess, motion lines", sfx=["PUF!"], gap="small"),
        panel("medium", "l_kitchen", ["lucka"], "(flour on face:1.2), flour on clothes, shocked, open mouth, "
              "hands up, mess", [("lucka", "Puntíku!!", "shout")], gap="small"),
        panel("medium", "l_kitchen", ["honzik"], "laughing, pointing, closed eyes, open mouth, happy",
              [("honzik", "Haha, sněhulák!")]),
        panel("medium", "l_kitchen", ["mama", "lucka"], "standing in doorway, surprised, hands on hips, "
              "embarrassed, sweatdrop", [("mama", "Co se tady stalo?!", "shout"),
                                         ("lucka", "Puntík chtěl pomoct…")]),
        panel("medium", "l_kitchen", ["lucka"], "wiping table, holding cloth, cleaning, careful, gentle smile, "
              "cookie dough", [("lucka", "Teď už jen opatrně.")]),
        panel("medium", "l_kitchen", ["puntik"], "hamster eating, holding cookie crumb, sitting on table, cute, "
              "happy, cheeks full",
              sfx=["CHROUP"], gap="large"),
        panel("medium", "l_kitchen", ["mama", "lucka"], "sitting at table, plate of cookies, laughing, "
              "happy, hug", [("mama", "Nejlepší pečení je to společné."),
                                ("lucka", "A nejlepší pomocník je Puntík!")], gap="large"),
    ]},
)

# 5. Halloweenská noc ---------------------------------------------------------------------------
STORIES["halloween"] = (
    world("w_halloween", "Halloweenská noc", "Natálka, pes Stínek a Sofie pomůžou laskavému duchovi.", [
        char("natalka", "Natálka", "1girl", "female child, black hair, long hair, purple eyes, witch costume, "
             "witch hat, purple dress, long sleeves, black cape, orange striped legwear, boots"),
        char("stinek", "Stínek", "", "dog, black dog, black fur, white stripe, medium dog"),
        char("sofie", "Sofie", "1girl", "female child, blonde hair, bob cut, ghost costume, white hooded cloak, "
             "long sleeves"),
        char("duch", "Duch", "", "ghost, cute ghost, transparent, white, floating, round eyes, smile"),
    ], [
        loc("l_street", "Ulice", "outdoors, night, autumn, street, jack-o'-lantern, string lights, autumn leaves, "
            "halloween"),
        loc("l_door", "Starý dům", "outdoors, night, old house, wooden door, cobweb, jack-o'-lantern, moon, "
            "halloween"),
        loc("l_hall", "Chodba", "indoors, night, hallway, candle, candlelight, old furniture, cobweb, dim lighting"),
    ]),
    {"title": "Halloweenská noc", "choices": [], "panels": [
        panel("wide", "l_street", ["natalka", "sofie"], "walking, holding lantern, smile, confident, night",
              [("natalka", "Stínku, dnes budeme stateční!")]),
        panel("medium", "l_street", ["stinek"], "(front view:1.2), full body, dog standing, growling, alert, "
              "ears up, (white stripe on chest:1.2), night, pumpkin", sfx=["VRRR"],
              gap="small"),
        panel("establishing", "l_door", [], "door opening, creaking, spooky", [("duch", "búú…", "thought")],
              sfx=["VRZZ"]),
        panel("medium", "l_door", ["sofie"], "scared, trembling, hands on own cheeks, wide eyes",
              [("sofie", "Jééé… to je strašidelné!")], gap="small"),
        panel("medium", "l_door", ["natalka"], "brave, smile, pointing at door, confident",
              [("natalka", "Pojďme se podívat. Stínek nás ochrání.")]),
        panel("medium", "l_hall", ["duch"], "(cute ghost:1.3), (close to viewer:1.2), floating, sad, "
              "teary eyes, candlelight",
              [("duch", "Nebojte se… jen jsem ztratil svou dýni.")], gap="small"),
        panel("medium", "l_hall", ["natalka"], "smile, determined, raising fist, brave",
              [("natalka", "My ti pomůžeme ji najít!")]),
        panel("medium", "l_hall", ["stinek"], "(front view:1.2), full body, dog barking, open mouth, "
              "(white stripe on chest:1.2), sitting next to pumpkin, jack-o'-lantern, under table, found",
              sfx=["HAF!"], gap="large"),
        panel("wide", "l_street", ["natalka", "sofie"], "holding lantern, candy, holding candy, laughing, happy, "
              "pumpkin, night", [("duch", "Děkuji, statečné holky a pejsku. Šťastný Halloween!"),
                                 ("natalka", "Vidíš, Stínku? I duchové můžou být kamarádi.")], gap="large"),
    ]},
)


def main():
    for key, (w, sb) in STORIES.items():
        d = DATA / "stories" / key
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{key}: {len(sb['panels'])} panels, {len(w['characters'])} characters")


if __name__ == "__main__":
    main()
