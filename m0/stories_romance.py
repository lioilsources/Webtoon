"""Ten hand-written romance stories for adults (SFW) → data/stories/r_<id>/{world,storyboard}.json (no LLM).

    python3 m0/stories_romance.py
    python3 m0/render.py --world data/stories/r_ny/world.json --storyboard data/stories/r_ny/storyboard.json --run r_ny

Each story is drawn in a different medium (world.style_id) — photoreal, watercolour, western comic, mono manga,
webtoon, film, oil, city pop, flat minimalism — so the set doubles as a style experiment. Characters carry booru
`base` tags plus named `outfits` (a panel picks one with {"id": .., "outfit": ..}) and a `photo` sentence for the
photoreal presets. Audience "adult" adds adult_negative (no childlike faces, nothing revealing); kisses stay
on-screen, nothing more. Dialogue is the author's text, verbatim.
"""

from common import DATA, save_json


def char(id, name, count, base, outfits, photo):
    outfits = {"default": outfits} if isinstance(outfits, str) else outfits
    return {"id": id, "name": name, "role": "playable", "count_tag": count, "human": True, "description": photo,
            "base": base, "outfits": outfits, "photo": photo, "tag_prompt": base + ", " + outfits["default"],
            "identity_level": "prompt", "reference_images": []}


def loc(id, name, tags):
    return {"id": id, "name": name, "description": name, "tag_prompt": tags, "mood": ""}


def panel(shot, loc_id, chars, tags, bubbles=(), sfx=(), gap="medium"):
    cs = [{"id": c.split(":")[0], **({"outfit": c.split(":")[1]} if ":" in c else {})} for c in chars]
    if len(cs) == 2:
        tags = "couple, hetero, " + tags
    return {"shot": shot, "location_id": loc_id, "characters": cs,
            "visual_tags": [t.strip() for t in tags.split(",") if t.strip()],
            "bubbles": [{"speaker_id": b[0], "text": b[1], "kind": b[2] if len(b) > 2 else "speech"} for b in bubbles],
            "sfx": [{"text": s, "style": "bold"} for s in sfx], "gap_after": gap}


def N(text):  # narration box
    return ("", text, "narration")


def world(id, title, synopsis, style, characters, locations):
    return {"id": id, "title": title, "synopsis": synopsis, "tone": "romantický, něžný, s humorem",
            "audience": "adult", "language": "cs", "style_id": style,
            "bible": {"rules": ["SFW: polibek ano, nahota ne."], "factions": []},
            "canon": {"nodes": [], "constraints": ["Dobrý konec."]},
            "permissions": {"allowed_locations": [l["id"] for l in locations]},
            "characters": characters, "locations": locations}


def story(w, panels):
    return w, {"title": w["title"], "fonts": "romance", "panels": panels}


STORIES = {}

# 1. New York — photoreal ------------------------------------------------------------------------
STORIES["ny"] = story(world("w_r_ny", "New York – Dívka z Prahy a muž z Manhattanu",
    "Eliška přijíždí z Prahy za prací, Daniel jí na chodníku podá kabát.", "photo_juggernaut", [
    char("eliska", "Eliška", "1girl", "adult, curvy, wide hips, small breasts, long hair, dark brown hair, brown eyes",
         {"default": "cream sweater, blue jeans, ankle boots", "rain": "beige trench coat, cream sweater, wet hair"},
         "a petite curvy Czech woman aged 29, long dark brown hair, brown eyes, natural look, little makeup"),
    char("daniel", "Daniel", "1boy", "mature male, dark-skinned male, very dark skin, tall, muscular, short hair, black hair, brown eyes",
         {"default": "black leather jacket, white shirt, dark jeans", "suit": "charcoal suit, white shirt"},
         "a tall athletic African American man aged 34, short black hair, calm attentive eyes"),
], [
    loc("l_street", "Brooklyn", "outdoors, brooklyn, brownstone, yellow taxi, sidewalk, autumn leaves, daytime"),
    loc("l_cafe", "Kavárna", "indoors, small cafe, window, coffee cup, warm light, brooklyn"),
    loc("l_river", "East River", "outdoors, east river, promenade, manhattan skyline, evening, string lights"),
    loc("l_awning", "Markýza", "outdoors, night, rain, under awning, wet street, neon reflections, new york"),
]), [
    panel("establishing", "l_street", [], "busy street, people walking, city noise", [N("New York kolem ní hučí.")]),
    panel("medium", "l_street", ["eliska"], "standing, holding suitcase, looking up, determined, small smile",
          [("eliska", "Tak dobře. Nový život.")]),
    panel("wide", "l_street", ["eliska"], "open suitcase, suitcase fallen on sidewalk, clothes spilled, surprised, open mouth",
          [N("Kufr se převrátí. Obsah se vysype na chodník.")], sfx=["BUM!"], gap="small"),
    panel("medium", "l_street", ["daniel"], "holding coat, offering coat, looking down, calm",
          [("daniel", "Potřebujete pomoct?")]),
    panel("medium", "l_street", ["eliska", "daniel"], "kneeling woman looking up, man holding coat, blush, embarrassed",
          [("eliska", "Já… děkuju."), ("daniel", "New York vás právě přivítal.")]),
    panel("close-up", "l_street", ["daniel"], "first smile, gentle smile", gap="large"),
    panel("medium", "l_cafe", ["eliska"], "sitting by window, coffee cup, alone, looking outside",
          [N("O několik dní později."), ("daniel", "Takže jste přežila první týden.")]),
    panel("medium", "l_cafe", ["eliska", "daniel:suit"], "sitting across table, two coffee cups, smile",
          [("eliska", "Těsně."), ("daniel", "Káva?"), ("eliska", "Tohle je moje první americké rande?")]),
    panel("close-up", "l_cafe", ["daniel:suit"], "smile, warm eyes",
          [("daniel", "Já doufal, že je to moje první americké rande.")], gap="large"),
    panel("wide", "l_river", ["eliska", "daniel"], "walking side by side, evening, looking at skyline",
          [("eliska", "Víš, co je zvláštní? V Praze jsem si připadala obyčejná."), ("daniel", "A tady?")]),
    panel("close-up", "l_river", ["eliska"], "looking down, sad smile",
          [("eliska", "Tady si připadám ještě obyčejnější.")]),
    panel("medium", "l_river", ["daniel"], "looking at viewer, gentle smile",
          [("daniel", "Já tě vidím úplně jinak."), ("eliska", "Jak?"), ("daniel", "Jako někoho, koho chci poznat.")], gap="large"),
    panel("medium", "l_awning", ["eliska:rain", "daniel"], "rain, under awning, man brushing wet hair from her face, hand on cheek, looking at each other",
          [("daniel", "Můžu?")]),
    panel("close-up", "l_awning", ["eliska:rain", "daniel"], "kiss, closed eyes, rain, tender", gap="small"),
    panel("medium", "l_awning", ["eliska:rain", "daniel"], "smiling at each other, blush, rain",
          [("eliska", "Tohle nebylo v mém plánu."), ("daniel", "Naštěstí.")], gap="large"),
])

# 2. Paříž — watercolour -------------------------------------------------------------------------
STORIES["pariz"] = story(world("w_r_pariz", "Paříž – Zrzka a muž v modrém saku",
    "Sofie, ilustrátorka z Dublinu, a Mathieu, kurátor galerie.", "watercolor_paris", [
    char("sofie", "Sofie", "1girl", "adult, tall female, curvy, large breasts, red hair, long hair, wavy hair, green eyes, freckles",
         {"default": "beige trench coat, turtleneck, long skirt", "red_dress": "red dress, long sleeves, high neckline"},
         "a tall curvy Irish woman aged 31, long wavy copper red hair, green eyes, freckles"),
    char("mathieu", "Mathieu", "1boy", "mature male, slender, dark hair, curly hair, short hair, brown eyes",
         "blue blazer, white shirt, elegant",
         "a slender elegant French man aged 35, dark curly hair, brown eyes"),
], [
    loc("l_montmartre", "Montmartre", "outdoors, montmartre, stone stairs, sacre-coeur, paris, windy, morning"),
    loc("l_gallery", "Galerie", "indoors, art gallery, paintings, white walls, soft light"),
    loc("l_bistro", "Bistro", "indoors, parisian bistro, small table, candle, wine glass, evening, warm light"),
    loc("l_seine", "Seina", "outdoors, seine, river, bridge, eiffel tower, night, city lights"),
]), [
    panel("wide", "l_montmartre", ["sofie"], "walking up stairs, wind, hair blowing, holding sketchbook"),
    panel("medium", "l_montmartre", ["sofie"], "sketchbook flying, paper flying, surprised, reaching out", sfx=["FÍÍÍ"], gap="small"),
    panel("medium", "l_montmartre", ["mathieu"], "catching sketchbook, holding sketchbook, smile",
          [("mathieu", "Tohle hledáte?")]),
    panel("medium", "l_montmartre", ["sofie", "mathieu"], "man handing sketchbook, looking at each other",
          [("sofie", "Ano."), ("mathieu", "Máte krásné kresby."), ("sofie", "To říkáte každé cizince?")]),
    panel("close-up", "l_montmartre", ["mathieu"], "smirk, gentle eyes",
          [("mathieu", "Ne. Jen těm, které mě zaujmou.")], gap="large"),
    panel("wide", "l_gallery", ["sofie", "mathieu"], "walking, looking at painting",
          [N("Sofie dostane práci v malé galerii."), ("sofie", "Vždycky jsem chtěla žít v Paříži."), ("mathieu", "A teď?")]),
    panel("close-up", "l_gallery", ["sofie"], "looking away, worried",
          [("sofie", "Teď se bojím, že sem nepatřím.")]),
    panel("medium", "l_gallery", ["mathieu"], "turning, looking at viewer, smile",
          [("mathieu", "Paříž není klub s členskou kartou.")], gap="large"),
    panel("medium", "l_bistro", ["sofie:red_dress"], "sitting at table, candle, blush, looking away",
          [("sofie", "Co je?"), ("mathieu", "Přemýšlím, proč se pořád snažíš být méně nápadná.")]),
    panel("close-up", "l_bistro", ["sofie:red_dress"], "sad smile, candlelight",
          [("sofie", "Protože jsem celý život byla příliš nápadná.")]),
    panel("medium", "l_bistro", ["mathieu"], "looking at viewer, gentle smile, candlelight",
          [("mathieu", "Mně se líbíš přesně taková.")], gap="large"),
    panel("wide", "l_seine", ["sofie:red_dress", "mathieu"], "holding hands, walking, night",
          [("mathieu", "Mohu tě políbit?"), ("sofie", "Tentokrát se nemusíš ptát.")]),
    panel("wide", "l_seine", ["sofie:red_dress", "mathieu"], "kiss, closed eyes, eiffel tower in background, night", gap="large"),
])

# 3. Miami — western comic -----------------------------------------------------------------------
STORIES["miami"] = story(world("w_r_miami", "Miami – Dívka v letních šatech",
    "Camila, fotografka z Brazílie, a Jack, instruktor surfování.", "western_comic", [
    char("camila", "Camila", "1girl", "adult, curvy, tan skin, long hair, black hair, curly hair, brown eyes",
         {"default": "yellow sundress, sun hat", "surf": "rash guard, board shorts, wet hair", "night": "white sundress"},
         "a curvy Brazilian woman aged 27, long black curly hair, tan skin, warm brown eyes"),
    char("jack", "Jack", "1boy", "mature male, tall, muscular, blonde hair, short hair, blue eyes, tan",
         {"default": "white t-shirt, board shorts", "surf": "rash guard, board shorts", "dinner": "linen shirt, chinos"},
         "a tall athletic white man aged 32, short blond hair, blue eyes, sun-tanned"),
], [
    loc("l_sunrise", "Pláž", "outdoors, beach, sunrise, ocean, palm trees, miami"),
    loc("l_surf", "Vlny", "outdoors, ocean, waves, surfboard, sunny, splash"),
    loc("l_restaurant", "Restaurace", "indoors, small restaurant, string lights, candle, evening, ocean view"),
    loc("l_night", "Noční pláž", "outdoors, beach, night, moon, stars, waves, moonlight"),
]), [
    panel("wide", "l_sunrise", ["camila"], "holding camera, taking photo, sun hat"),
    panel("medium", "l_sunrise", ["camila"], "wind, hat flying away, surprised, reaching out", sfx=["FŮŮ!"], gap="small"),
    panel("medium", "l_sunrise", ["jack"], "catching hat, holding sun hat, smile",
          [("jack", "Myslím, že tenhle patří vám.")]),
    panel("medium", "l_sunrise", ["camila", "jack"], "man handing hat, smile",
          [("camila", "Děkuju."), ("jack", "Fotíte?")]),
    panel("close-up", "l_sunrise", ["camila"], "embarrassed smile, holding camera", [("camila", "Snažím se.")]),
    panel("close-up", "l_sunrise", ["jack"], "grin", [("jack", "Tak tohle bych si rád prohlédl.")], gap="large"),
    panel("wide", "l_surf", ["camila:surf"], "falling off surfboard, splash, water",
          [("camila", "Tohle mělo být romantické?", "shout")], sfx=["ŠPLOUCH!"]),
    panel("medium", "l_surf", ["jack:surf"], "laughing, standing in water, holding surfboard",
          [("jack", "Ještě jsem nezačal.")], gap="large"),
    panel("medium", "l_restaurant", ["camila:night"], "sitting, candle, looking down, shy smile",
          [("camila", "Nikdy jsem si nemyslela, že se do někoho zamiluju tak daleko od domova.")]),
    panel("medium", "l_restaurant", ["jack:dinner"], "serious, looking at viewer", [("jack", "A jsi zamilovaná?")]),
    panel("medium", "l_restaurant", ["camila:night", "jack:dinner"], "smiling at each other, sitting across table",
          [("camila", "Možná."), ("jack", "Já určitě.")], gap="large"),
    panel("wide", "l_night", ["camila:night", "jack:dinner"], "sitting on sand, arm around shoulder, moonlight",
          [("camila", "Ještě pořád si myslím, že nejsem dost hezká."), ("jack", "Tak se na mě podívej.")]),
    panel("close-up", "l_night", ["camila:night", "jack:dinner"], "looking at each other, faces close, moonlight",
          [("jack", "Vidíš, co vidím já?")], gap="small"),
    panel("wide", "l_night", ["camila:night", "jack:dinner"], "kiss, closed eyes, waves, moonlight", gap="large"),
])

# 4. Londýn — monochrome manga -------------------------------------------------------------------
STORIES["londyn"] = story(world("w_r_londyn", "Londýn – Kovboj v dešti",
    "Emily z Texasu studuje v Londýně hudbu, Oliver restauruje staré domy.", "manga_mono", [
    char("emily", "Emily", "1girl", "adult, tall female, slender, athletic, blonde hair, long hair, blue eyes",
         "plaid shirt, denim jacket, jeans, cowboy boots",
         "a tall slender athletic Texan woman aged 30, long blond hair, blue eyes"),
    char("oliver", "Oliver", "1boy", "mature male, muscular, brown hair, short hair, stubble, brown eyes",
         "old leather jacket, grey t-shirt, jeans",
         "a muscular British man aged 33, short brown hair, stubble"),
], [
    loc("l_station", "Nádraží", "outdoors, train station entrance, london, rain, umbrellas, double-decker bus"),
    loc("l_pub", "Pub", "indoors, pub, wooden bar, pint glass, warm light"),
    loc("l_farm", "Farma", "outdoors, countryside, farm, horse, wooden fence, green hills, cloudy sky"),
    loc("l_platform", "Peron", "indoors, train station platform, train, departure board"),
]), [
    panel("establishing", "l_station", [], "rain, heavy rain, puddles", [N("Londýn. Déšť.")]),
    panel("medium", "l_station", ["emily"], "broken umbrella, holding umbrella, wet, rain, annoyed", sfx=["KŘUP"], gap="small"),
    panel("medium", "l_station", ["oliver"], "holding umbrella, smile, rain", [("oliver", "Potřebujete zachránit?")]),
    panel("medium", "l_station", ["emily", "oliver"], "sharing umbrella, rain",
          [("emily", "Můj deštník nebo mě?"), ("oliver", "Podle situace obojí.")], gap="large"),
    panel("wide", "l_pub", ["emily", "oliver"], "sitting at bar, beer",
          [("emily", "Všichni tady vypadají, jako by se narodili v Londýně."), ("oliver", "Já ne.")]),
    panel("medium", "l_pub", ["oliver"], "deadpan, holding pint glass",
          [("emily", "Ty ano."), ("oliver", "Narodil jsem se ve Walesu.")], gap="small"),
    panel("close-up", "l_pub", ["emily"], "laughing, closed eyes", gap="large"),
    panel("wide", "l_farm", ["emily"], "petting horse, smile, happy", [N("Oliver zjistí, že Emily miluje koně.")]),
    panel("medium", "l_farm", ["emily", "oliver"], "leaning on fence, horse in background",
          [("emily", "Takže ty nejsi kovboj."), ("oliver", "Ne."), ("emily", "Škoda.")]),
    panel("close-up", "l_farm", ["oliver"], "smile, holding cowboy hat", [("oliver", "Můžu se to naučit.")], gap="large"),
    panel("medium", "l_platform", ["emily"], "holding plane ticket, looking down",
          [("oliver", "Kdy odlétáš?"), ("emily", "Za dva dny.")]),
    panel("close-up", "l_platform", ["oliver"], "worried, sad", gap="small"),
    panel("medium", "l_platform", ["emily"], "small smile, looking at viewer", [("emily", "Ale možná ji nepoužiju.")]),
    panel("medium", "l_platform", ["emily", "oliver"], "hug, smile",
          [("emily", "Tohle je rozhodně lepší než londýnský deštník.")], gap="small"),
    panel("close-up", "l_platform", ["emily", "oliver"], "kiss, closed eyes", gap="large"),
])

# 5. Praha — webtoon -----------------------------------------------------------------------------
STORIES["praha"] = story(world("w_r_praha", "Praha – Muž, který nevěřil na lásku",
    "Nina, fotografka, a Adam, automechanik, který se umí obléknout.", "webtoon_romance", [
    char("nina", "Nina", "1girl", "adult, asian, short hair, black hair, bob cut, brown eyes, bright smile",
         {"default": "black turtleneck, wide pants, white sneakers", "black_dress": "black dress, simple dress"},
         "a petite Vietnamese-Czech woman aged 32, short black bob hair, bright smile"),
    char("adam", "Adam", "1boy", "mature male, tall, muscular, brown hair, short hair, stubble, brown eyes",
         {"default": "blue overalls, white t-shirt, grease stains", "walk": "black leather jacket, black t-shirt, jeans",
          "jacket": "dark blazer, white shirt"},
         "a tall strong Czech man aged 38, short brown hair, stubble"),
], [
    loc("l_garage", "Autoservis", "indoors, auto repair shop, garage, car, open hood, tools, daylight"),
    loc("l_bridge", "Karlův most", "outdoors, charles bridge, statues, prague castle, old town, sunset"),
    loc("l_restaurant", "Restaurace", "indoors, elegant restaurant, candle, evening, warm light"),
    loc("l_night", "Noční most", "outdoors, charles bridge, night, street lamps, prague, city lights, river"),
]), [
    panel("wide", "l_garage", ["nina"], "standing by car, arms crossed",
          [("adam", "Co se stalo?"), ("nina", "Auto přestalo poslouchat.")]),
    panel("medium", "l_garage", ["adam"], "wiping hands, rag, smirk", [("adam", "A vy?")]),
    panel("close-up", "l_garage", ["nina"], "smile, confident", [("nina", "Já poslouchám vždycky.")], gap="large"),
    panel("medium", "l_garage", ["adam"], "talking on phone, holding phone, smile",
          [("adam", "Auto je hotové."), ("nina", "Kolik dlužím?"), ("adam", "Jednu kávu.")]),
    panel("medium", "l_bridge", ["nina"], "holding phone, laughing",
          [("nina", "To je velmi drahá oprava."), ("adam", "Byl to složitý problém.")], gap="large"),
    panel("wide", "l_bridge", ["nina", "adam:walk"], "walking, old town",
          [("nina", "Víš, co je můj problém?"), ("adam", "Jaký?")]),
    panel("close-up", "l_bridge", ["nina"], "looking down, vulnerable",
          [("nina", "Vždycky čekám, že mě někdo odmítne, ještě než mě pozná.")]),
    panel("medium", "l_bridge", ["nina", "adam:walk"], "holding hands", [("adam", "Tak mě nech poznat tě.")], gap="large"),
    panel("medium", "l_restaurant", ["nina:black_dress"], "sitting, surprised, smile",
          [("nina", "Nikdy bych neřekla, že automechanik může vypadat takhle.")]),
    panel("medium", "l_restaurant", ["adam:jacket"], "smile, leaning forward",
          [("adam", "A já nikdy neřekl, že fotografka může být tak nebezpečná.")]),
    panel("medium", "l_restaurant", ["nina:black_dress"], "laughing",
          [("nina", "Nebezpečná?"), ("adam", "Ukradla jsi mi srdce.")], gap="large"),
    panel("wide", "l_night", ["nina:black_dress", "adam:jacket"], "hug, night, city lights",
          [("nina", "Myslíš, že tohle vydrží?"), ("adam", "Nevím.")]),
    panel("close-up", "l_night", ["nina:black_dress"], "pout, amused",
          [("nina", "To není moc romantické."), ("adam", "Tak jinak.")], gap="small"),
    panel("close-up", "l_night", ["nina:black_dress", "adam:jacket"], "kiss, closed eyes, night", gap="small"),
    panel("medium", "l_night", ["nina:black_dress", "adam:jacket"], "hug, smile, closed eyes",
          [("adam", "Chci zjistit, jestli ano.")], gap="large"),
])

# 6. Havana — analogue film photo ----------------------------------------------------------------
STORIES["havana"] = story(world("w_r_havana", "Havana – Boxer, který přijel zapomenout",
    "Mateo, bývalý boxer, a Isabel, která v kavárně ví víc, než říká.", "photo_realvis_film", [
    char("mateo", "Mateo", "1boy", "mature male, dark skin, tall, muscular, broad shoulders, short hair, black hair, calm",
         "white linen shirt, dark trousers",
         "a tall muscular Cuban man aged 35, former boxer, broad shoulders, short black hair, calm gaze"),
    char("isabel", "Isabel", "1girl", "adult, dark-skinned female, dark skin, long hair, curly hair, black hair, bright smile",
         {"default": "white blouse, apron", "dance": "flowing orange dress, knee-length dress"},
         "a petite Afro-Cuban woman aged 30, long curly black hair, wide bright smile"),
    char("raul", "Raúl", "1boy", "old man, grey hair, grey mustache, wrinkles, dark skin",
         "tank top, towel on shoulder",
         "a 62-year-old Cuban man, grey hair, grey moustache, weathered face, boxing gym owner"),
], [
    loc("l_bus", "Ulice", "outdoors, havana street, old bus, colonial buildings, pastel facades, vintage cars, morning sun"),
    loc("l_cafe", "Kavárna", "indoors, small havana cafe, wooden counter, espresso cups, sunlight through shutters"),
    loc("l_dance", "Večerní ulice", "outdoors, havana street, evening, string lights, music, warm light"),
    loc("l_malecon", "Malecón", "outdoors, malecon seawall, sunset, ocean, havana skyline"),
]), [
    panel("establishing", "l_bus", [], "vintage cars, colonial buildings", [N("Havana.")]),
    panel("medium", "l_bus", ["mateo"], "holding suitcase, getting off bus, serious"),
    panel("medium", "l_bus", ["raul"], "arms crossed, smile", [("raul", "Takže ses opravdu vrátil.")]),
    panel("close-up", "l_bus", ["mateo"], "serious, looking away",
          [("mateo", "Potřeboval jsem místo, kde mě nikdo nezná.")], gap="small"),
    panel("medium", "l_bus", ["raul"], "laughing, pointing", [("raul", "Havana tě vždycky pozná.")], gap="large"),
    panel("medium", "l_cafe", ["isabel"], "placing coffee cup on counter, smile, behind counter", [("isabel", "Dvě cukrové.")]),
    panel("medium", "l_cafe", ["mateo"], "sitting at counter, coffee cup, puzzled",
          [("mateo", "Já si nedávám cukr."), ("isabel", "Já vím.")]),
    panel("close-up", "l_cafe", ["isabel"], "teasing smile, leaning on counter",
          [("mateo", "Jak to víš?"), ("isabel", "Protože tě pozoruju už týden.")], gap="small"),
    panel("close-up", "l_cafe", ["mateo"], "laughing, first smile", gap="large"),
    panel("wide", "l_dance", ["isabel:dance"], "dancing, salsa, twirling, dress flowing"),
    panel("medium", "l_dance", ["isabel:dance", "mateo"], "woman reaching out hand, man standing shy",
          [("isabel", "Ty netančíš?"), ("mateo", "Já boxuju."), ("isabel", "To není odpověď.")]),
    panel("wide", "l_dance", ["isabel:dance", "mateo"], "dancing together, salsa, holding hands, laughing",
          [("isabel", "Bojuješ s hudbou."), ("mateo", "Hudba začala první.")], gap="large"),
    panel("wide", "l_malecon", ["isabel", "mateo"], "sitting on seawall, sunset",
          [("mateo", "Myslel jsem, že jsem přijel do Havany, abych zapomněl."), ("isabel", "A podařilo se?")]),
    panel("close-up", "l_malecon", ["mateo"], "looking at her, soft expression",
          [("mateo", "Ne."), ("mateo", "Potkal jsem tebe.")]),
    panel("close-up", "l_malecon", ["isabel"], "smile, sunset light",
          [("isabel", "To zní jako docela dobrý důvod nezapomenout.")], gap="small"),
    panel("medium", "l_malecon", ["isabel", "mateo"], "kiss, embrace, sunset, closed eyes", gap="large"),
])

# 7. Nairobi — oil painting ----------------------------------------------------------------------
STORIES["nairobi"] = story(world("w_r_nairobi", "Nairobi – Muž v obleku a žena z parku",
    "David, finanční analytik, a Amara, veterinářka.", "painterly_oil", [
    char("david", "David", "1boy", "mature male, dark-skinned male, very dark skin, tall, short hair, black hair, elegant",
         {"default": "navy suit, white shirt, tie", "coat": "navy suit, long coat"},
         "a tall elegant Kenyan man aged 41, very dark skin, short black hair, perfectly tailored suit"),
    char("amara", "Amara", "1girl", "adult, dark-skinned female, very dark skin, athletic, very short hair, afro",
         {"default": "white shirt, khaki pants, sneakers", "blue_dress": "blue dress, simple dress"},
         "an athletic Kenyan woman aged 34, very dark skin, short natural hair"),
    char("jonas", "Jonas", "1boy", "mature male, dark-skinned male, dark skin, glasses, short hair, black hair, grin",
         "grey suit", "a Kenyan man aged 40 with glasses, grey suit, cheeky grin"),
], [
    loc("l_office", "Kancelář", "indoors, office, large window, cityscape, nairobi skyline, desk, laptop"),
    loc("l_park", "Park", "outdoors, park, acacia tree, green grass, sunny, nairobi"),
    loc("l_restaurant", "Restaurace", "indoors, restaurant, warm light, evening, candle"),
    loc("l_city", "Večerní město", "outdoors, city street, night, street lights, nairobi"),
]), [
    panel("wide", "l_office", ["david"], "sitting at desk, alone, looking out window"),
    panel("medium", "l_office", ["jonas"], "placing two tickets on desk, grin", [("jonas", "V sobotu jdeš ven.")]),
    panel("medium", "l_office", ["david"], "sitting at desk, tired",
          [("david", "Nemůžu."), ("jonas", "Můžeš."), ("david", "Mám práci.")], gap="small"),
    panel("close-up", "l_office", ["jonas"], "smirk, pointing", [("jonas", "Práce ti nikdy neřekne, že tě miluje.")], gap="small"),
    panel("close-up", "l_office", ["david"], "laughing", gap="large"),
    panel("wide", "l_park", ["amara"], "kneeling, injured dog, small dog, bandage"),
    panel("medium", "l_park", ["david:coat"], "standing, looking down, concerned",
          [("david", "Potřebujete pomoc?"), ("amara", "Pokud umíte držet psa.")]),
    panel("medium", "l_park", ["david:coat"], "taking off coat, kneeling",
          [("amara", "Vy jste přišel z kanceláře?"), ("david", "Je to tak vidět?")]),
    panel("medium", "l_park", ["amara", "david"], "kneeling together, holding dog, dog licking hand, smile",
          [("amara", "Trochu.")], gap="large"),
    panel("medium", "l_restaurant", ["amara:blue_dress"], "walking, smile", [N("O několik dní později.")]),
    panel("close-up", "l_restaurant", ["david"], "surprised, speechless, open mouth",
          [("amara", "Je něco špatně?"), ("david", "Ne.")]),
    panel("medium", "l_restaurant", ["amara:blue_dress"], "sitting, head tilt, smile", [("amara", "Tak proč se tak díváte?")]),
    panel("medium", "l_restaurant", ["david"], "gentle smile, sitting",
          [("david", "Protože jsem právě zjistil, že můj oblíbený pohled není výhled z kanceláře.")], gap="large"),
    panel("wide", "l_city", ["amara:blue_dress", "david"], "walking, night",
          [("amara", "Ty pořád přemýšlíš."), ("david", "Je to moje práce."), ("amara", "A kdy přestaneš?")]),
    panel("close-up", "l_city", ["david"], "stopping, soft determined look", [("david", "Teď.")], gap="small"),
    panel("medium", "l_city", ["amara:blue_dress", "david"], "kiss, holding hands, closed eyes, night", gap="small"),
    panel("close-up", "l_city", ["amara:blue_dress"], "smile, laughing",
          [("amara", "Tohle už vypadá jako dobrá změna kariéry.")], gap="large"),
])

# 8. Jakarta — 80s city pop anime ----------------------------------------------------------------
STORIES["jakarta"] = story(world("w_r_jakarta", "Jakarta – Mechanik a dívka v červených šatech",
    "Rafi, automechanik, a Maya, sebevědomá jen na první pohled.", "retro_citypop", [
    char("rafi", "Rafi", "1boy", "mature male, asian, tan skin, muscular, burly, short hair, black hair",
         {"default": "work overalls, grey t-shirt, oil stains", "suit": "dark suit, white shirt"},
         "a muscular burly Indonesian man aged 33, short black hair, mechanic"),
    char("maya", "Maya", "1girl", "adult, asian, tan skin, tall female, long hair, black hair, straight hair, elegant",
         {"default": "white blouse, black pants, sunglasses on head", "red_dress": "red dress, long dress"},
         "a tall elegant Indonesian woman aged 29, long straight black hair"),
    char("budi", "Budi", "1boy", "mature male, asian, tan skin, chubby, short hair, grin, baseball cap",
         "hawaiian shirt", "a chubby cheerful Indonesian man aged 35, baseball cap, hawaiian shirt"),
], [
    loc("l_shop", "Dílna", "indoors, auto workshop, garage, car, open hood, tools, jakarta"),
    loc("l_party", "Večírek", "indoors, party, ballroom, chandelier, evening, crowd"),
    loc("l_roof", "Střecha", "outdoors, rooftop, night, jakarta skyline, city lights, neon"),
]), [
    panel("wide", "l_shop", ["maya"], "standing by car, confident"),
    panel("medium", "l_shop", ["maya"], "hand on hip, smile", [("maya", "Prý jste nejlepší mechanik v Jakartě.")]),
    panel("medium", "l_shop", ["rafi"], "wiping hands, rag, shy", [("rafi", "To říká Budi.")], gap="small"),
    panel("medium", "l_shop", ["budi"], "grin, thumbs up", [("budi", "A taky to říká tvoje máma.")], gap="small"),
    panel("close-up", "l_shop", ["rafi"], "rolling eyes, annoyed", gap="large"),
    panel("wide", "l_shop", ["rafi"], "repairing engine, leaning over car, focused"),
    panel("medium", "l_shop", ["maya"], "sitting on chair, watching, curious",
          [("maya", "Vždycky jste tak soustředěný?"), ("rafi", "Když něco opravuju, ano.")]),
    panel("close-up", "l_shop", ["maya"], "smile", [("maya", "A lidi?")], gap="small"),
    panel("close-up", "l_shop", ["rafi"], "surprised, pause", [("rafi", "Lidi jsou složitější.")], gap="large"),
    panel("wide", "l_party", ["maya:red_dress"], "standing, elegant", [N("Maya pozve Rafiho na večírek.")]),
    panel("medium", "l_party", ["rafi:suit"], "nervous, adjusting collar",
          [("rafi", "Tohle je chyba."), ("maya", "Co?"), ("rafi", "Že jsem sem přišel.")]),
    panel("medium", "l_party", ["maya:red_dress"], "puzzled, head tilt", [("maya", "Proč?")], gap="small"),
    panel("close-up", "l_party", ["rafi:suit"], "looking at viewer, blush",
          [("rafi", "Protože teď už nedokážu myslet na nic jiného.")], gap="large"),
    panel("wide", "l_roof", ["maya:red_dress", "rafi:suit"], "sitting on rooftop, night skyline",
          [("maya", "Víš, co jsem si o tobě myslela?"), ("rafi", "Co?"), ("maya", "Že jsi jen mechanik.")]),
    panel("close-up", "l_roof", ["maya:red_dress"], "soft smile, blush",
          [("rafi", "A teď?"), ("maya", "Teď vím, že jsi muž, do kterého se můžu zamilovat.")]),
    panel("medium", "l_roof", ["maya:red_dress", "rafi:suit"], "holding hands", [("rafi", "Já už se zamiloval.")], gap="small"),
    panel("close-up", "l_roof", ["maya:red_dress", "rafi:suit"], "kiss, closed eyes, city lights", gap="large"),
])

# 9. Bombaj — flat minimalism --------------------------------------------------------------------
STORIES["bombaj"] = story(world("w_r_bombaj", "Bombaj – Muž, který čekal na múzu",
    "Arjun, fotograf bez inspirace, a Priya v monzunovém dešti.", "minimal_flat", [
    char("arjun", "Arjun", "1boy", "mature male, indian, brown skin, tall, slender, long hair, ponytail, black hair, stubble",
         "linen kurta, scarf, bead necklace",
         "a tall slender Indian man aged 37, long black hair in a ponytail, bohemian style"),
    char("priya", "Priya", "1girl", "adult, indian, brown skin, long hair, black hair, big brown eyes",
         "mustard kurta, blue jeans",
         "a petite Indian woman aged 32, long black hair, big expressive brown eyes"),
    char("dev", "Dev", "1boy", "mature male, indian, brown skin, glasses, short hair, beard", "white shirt",
         "an Indian man aged 38, glasses, short beard, white shirt"),
], [
    loc("l_gallery", "Galerie", "indoors, art gallery, studio, blank canvas, white wall"),
    loc("l_rain", "Monzun", "outdoors, mumbai street, monsoon, heavy rain, puddles, umbrellas"),
    loc("l_studio", "Ateliér", "indoors, photo studio, softbox, camera on tripod"),
    loc("l_marina", "Marine Drive", "outdoors, marine drive, sea, sunset, promenade"),
]), [
    panel("wide", "l_gallery", ["arjun"], "standing, from behind, blank canvas"),
    panel("medium", "l_gallery", ["dev"], "arms crossed, concerned", [("dev", "Už tři měsíce jsi nic nenafotil.")]),
    panel("close-up", "l_gallery", ["arjun"], "looking away, calm",
          [("arjun", "Čekám."), ("dev", "Na co?"), ("arjun", "Na múzu.")], gap="large"),
    panel("wide", "l_rain", ["priya"], "running, rain, umbrella falling, wet hair", [N("Prudký monzunový déšť.")]),
    panel("medium", "l_rain", ["arjun"], "offering umbrella, holding umbrella, rain", gap="small"),
    panel("medium", "l_rain", ["priya", "arjun"], "woman holding umbrella, man in rain, wet",
          [("priya", "A vy?"), ("arjun", "Já déšť přežiju.")]),
    panel("close-up", "l_rain", ["priya"], "wet hair, looking up",
          [("priya", "A já?"), ("arjun", "Vy vypadáte, že přežijete všechno.")], gap="small"),
    panel("close-up", "l_rain", ["priya"], "smile, rain", gap="large"),
    panel("medium", "l_studio", ["priya"], "standing, shy, hands together",
          [("priya", "Nejsem fotogenická."), ("arjun", "To říkají lidé, kteří nevědí, co na nich hledat.")]),
    panel("medium", "l_studio", ["arjun"], "holding camera, taking photo", sfx=["CVAK"], gap="small"),
    panel("close-up", "l_studio", ["arjun"], "looking at camera screen, silent, surprised",
          [("dev", "Našel jsi ji?"), ("arjun", "Ano.")], gap="large"),
    panel("wide", "l_marina", ["priya", "arjun"], "sitting by sea, sunset",
          [("priya", "Takže jsem tvoje múza?"), ("arjun", "Ne.")]),
    panel("close-up", "l_marina", ["priya"], "surprised", gap="small"),
    panel("close-up", "l_marina", ["arjun"], "gentle smile", [("arjun", "Jsi důvod, proč zase vidím svět.")]),
    panel("medium", "l_marina", ["priya", "arjun"], "holding hands, woman looking down, blush", gap="small"),
    panel("close-up", "l_marina", ["priya", "arjun"], "kiss, closed eyes, sunset", gap="large"),
])

# 10. Šanghaj — neon night photo -----------------------------------------------------------------
STORIES["sanghaj"] = story(world("w_r_sanghaj", "Šanghaj – Cizinec, který zůstal",
    "Thomas, Brit ztracený v Šanghaji, a Lin, překladatelka.", "photo_cyberreal_night", [
    char("thomas", "Thomas", "1boy", "mature male, tall, muscular, blonde hair, grey hair, short hair, stubble, blue eyes",
         "navy overcoat, grey suit",
         "a tall strong British man aged 39, former athlete, ash blond hair going grey, light stubble"),
    char("lin", "Lin", "1girl", "adult, asian, short hair, black hair, bob cut, brown eyes",
         "camel coat, black turtleneck",
         "a petite Chinese woman aged 30, short black bob hair, clever amused eyes"),
], [
    loc("l_tower", "Pudong", "outdoors, shanghai, skyscrapers, lujiazui, dusk"),
    loc("l_cafe", "Kavárna", "indoors, shanghai cafe, neon sign, window, coffee cup, evening"),
    loc("l_bund", "Bund", "outdoors, the bund, huangpu river, night, skyline, oriental pearl tower"),
    loc("l_station", "Nádraží", "indoors, railway station, shanghai, high-speed train, platform"),
]), [
    panel("establishing", "l_tower", [], "shanghai skyline, skyscrapers"),
    panel("medium", "l_tower", ["thomas"], "holding phone, looking up, lost", [("thomas", "Nikdo mě tady nezná.")]),
    panel("medium", "l_tower", ["lin"], "smile, hands in pockets", [("lin", "To může být někdy výhoda.")], gap="small"),
    panel("medium", "l_tower", ["thomas", "lin"], "man turning around, surprised",
          [("lin", "Ztratil jste se?"), ("thomas", "Ano.")]),
    panel("close-up", "l_tower", ["lin"], "smirk", [("lin", "Tak jste začal správně.")], gap="large"),
    panel("medium", "l_cafe", ["thomas"], "concentrating, talking, coffee cup",
          [N("Lin mu pomáhá orientovat se ve městě.")]),
    panel("medium", "l_cafe", ["lin"], "laughing, coffee cup", [("lin", "Skoro."), ("thomas", "Skoro?")], gap="small"),
    panel("close-up", "l_cafe", ["lin"], "amused smile", [("lin", "Řekl jste ‚chci kočku‘ místo ‚chci kávu‘.")], gap="small"),
    panel("close-up", "l_cafe", ["thomas"], "laughing, closed eyes", sfx=["PFFF!"], gap="large"),
    panel("wide", "l_bund", ["thomas", "lin"], "walking along river, night skyline",
          [("thomas", "Celý život jsem hledal místo, kam budu patřit."), ("lin", "A našel jste ho?")]),
    panel("close-up", "l_bund", ["thomas"], "looking at her, soft",
          [("thomas", "Možná."), ("lin", "Kde?"), ("thomas", "Tady.")], gap="small"),
    panel("close-up", "l_bund", ["lin"], "smile, blush, city lights", gap="large"),
    panel("medium", "l_station", ["lin"], "standing on platform, sad",
          [N("Thomas má odjet zpět do Londýna."), ("lin", "Takže tohle je sbohem.")]),
    panel("medium", "l_station", ["thomas"], "holding ticket, tearing ticket",
          [("thomas", "Ne."), ("lin", "Ne?"), ("thomas", "Změnil jsem rezervaci.")], sfx=["TRRR"]),
    panel("medium", "l_station", ["lin"], "laughing, happy", [("thomas", "Zůstávám.")], gap="small"),
    panel("medium", "l_station", ["thomas", "lin"], "hug, embrace, closed eyes", gap="small"),
    panel("wide", "l_station", ["thomas", "lin"], "kiss, train passing, motion blur", gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / f"r_{sid}"
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"r_{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
