"""Romance set H — fashion and flirt, ten stories ("5 příběhů z pohledu ženy / 5 příběhů z pohledu muže").

    python3 m0/romance_h.py        → data/stories/rh_*/{world,storyboard}.json

Same building blocks and rules as stories_romance.py: one medium per story, dialogue near-verbatim (typos fixed),
inner monologue as thought bubbles, never two characters of the same gender in one panel. The source scenes were
explicit; here every intimate scene ends with a kiss and a fade to black, the morning after is fully dressed and
the fashion is described without brand names.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}


def ending(w, text):
    w["canon"]["constraints"] = [text]
    return w


# 1. Santorini — fashion editorial ----------------------------------------------------------------
STORIES["rh_01_santorini"] = story(ending(world("w_rh_01_santorini", "Santorini – Ta, která se nedá přehlédnout",
    "Malá Elena si mezi dokonalými lidmi na Santorini připadá neviditelná, dokud ji nezastaví Nikos.", "fashion_editorial", [
    char("elena", "Elena", "1girl", "adult, petite, mature female, curvy, wide hips, olive skin, long hair, wavy hair, dark brown hair, brown eyes",
         {"default": "white silk dress, flowing dress, gold earrings, gold bracelets, high heels",
          "dinner": "white silk dress, off-shoulder, gold necklace, gold earrings, hair up, high heels",
          "morning": "oversized white linen shirt dress, gold earrings, sandals, hair down"},
         "a petite curvy Mediterranean woman aged 27 with long dark wavy hair"),
    char("nikos", "Nikos", "1boy", "mature male, athletic, tan skin, short hair, black hair, brown eyes, stubble",
         {"default": "white linen shirt, beige linen trousers, leather sandals",
          "dinner": "navy linen shirt, white linen trousers, wristwatch"},
         "an athletic Greek man aged 34 with short black hair, tanned skin"),
], [
    loc("l_terrace", "Terasa nad kalderou", "outdoors, santorini, caldera view, whitewashed buildings, blue dome, terrace, sea, sunlight"),
    loc("l_yacht", "Jachta", "outdoors, yacht deck, sunset, sea, wine glasses, candle, orange sky"),
    loc("l_cabin", "Kajuta", "indoors, yacht cabin, wooden interior, porthole, warm lamp light, night"),
]), "Šťastný konec: zůstanou spolu."), [
    panel("establishing", "l_terrace", [], "whitewashed houses, blue domes, caldera, morning sun", [N("Santorini. Terasa s výhledem na kalderu.")]),
    panel("wide", "l_terrace", ["elena"], "standing at railing, looking at sea, wind in hair, alone"),
    panel("close-up", "l_terrace", ["elena"], "sad, looking down, insecure",
          [("elena", "Všichni tady jsou dokonalí… já jsem jen malá.", "thought")], gap="small"),
    panel("medium", "l_terrace", ["nikos"], "walking past, stopping, looking at viewer, smile"),
    panel("medium", "l_terrace", ["elena", "nikos"], "man standing beside woman, woman looking up, surprised, blush",
          [("nikos", "Ty jsi ta, která se nedá přehlédnout.")], gap="large"),
    panel("wide", "l_yacht", ["elena:dinner", "nikos:dinner"], "sitting at table, wine glasses, sunset, talking, smile",
          [N("Večer. Večeře na jachtě."), ("nikos", "Přijela jsi hledat něco skutečného?")]),
    panel("close-up", "l_yacht", ["elena:dinner"], "soft smile, sunset light, looking at viewer", [("elena", "Ano.")], gap="small"),
    panel("medium", "l_cabin", ["elena:dinner", "nikos:dinner"], "man taking off her earrings gently, standing, faces close, warm light",
          [("nikos", "Nech mě se na tebe dívat… pomalu.")]),
    panel("medium", "l_cabin", ["elena:dinner", "nikos:dinner"], "kiss, embrace, eyes closed, warm light",
          [("elena", "Cítím se… hezká.")], gap="small"),
    panel("medium", "l_cabin", [], "lamp going out, porthole, moonlight on water, no humans", [N("Lampa zhasne. Moře šumí dál.")], gap="large"),
    panel("wide", "l_terrace", ["elena:morning", "nikos"], "morning, coffee cups, hugging from behind, looking at sea, smile",
          [("nikos", "Jsi. A jsi moje."), N("Ráno zůstávají.")], gap="large"),
])

# 2. Banff — clean webtoon ------------------------------------------------------------------------
STORIES["rh_02_banff"] = story(ending(world("w_rh_02_banff", "Banff – Jen výhled",
    "Vysoká Chloe hledá v kanadských horách víc než výhled, Ethan jí nabídne jednu noc a pak odjede.", "clean_webtoon_noartist", [
    char("chloe", "Chloe", "1girl", "adult, tall female, slender, long hair, blonde hair, blue eyes",
         {"default": "red puffer jacket, outdoor jacket, beanie, hiking boots, gold earrings",
          "dinner": "cream turtleneck sweater, wool skirt, knee boots, gold earrings",
          "morning": "cream turtleneck sweater, red puffer jacket, carrying backpack"},
         "a tall slender woman aged 29 with long blonde hair"),
    char("ethan", "Ethan", "1boy", "mature male, muscular, broad shoulders, short hair, brown hair, brown eyes, stubble",
         {"default": "dark green outdoor jacket, flannel shirt, hiking boots",
          "dinner": "grey knit sweater, dark jeans",
          "leave": "dark green outdoor jacket, duffel bag over shoulder"},
         "a muscular man aged 36 with short brown hair and an outdoor jacket"),
], [
    loc("l_trail", "Lesní stezka", "outdoors, forest trail, pine trees, mountains, banff, turquoise lake, daytime"),
    loc("l_cabin", "Chata", "indoors, log cabin, fireplace, wooden table, wine glasses, warm light, night, snow outside window"),
    loc("l_porch", "Před chatou", "outdoors, log cabin porch, morning, mist, mountains, cold"),
]), "Smutný konec: on odjede a ona odchází sama."), [
    panel("establishing", "l_trail", [], "turquoise lake, pine forest, mountains", [N("Banff. Kanadské hory.")]),
    panel("medium", "l_trail", ["chloe"], "walking alone, hands in pockets, looking at lake",
          [("chloe", "Jsem moc vysoká a studená…", "thought")]),
    panel("wide", "l_trail", ["chloe", "ethan"], "man coming down trail, meeting, both stopping, smile"),
    panel("close-up", "l_trail", ["ethan"], "smile, looking at viewer, curious",
          [("ethan", "Vypadáš, jako bys hledala něco víc než výhled.")], gap="large"),
    panel("medium", "l_cabin", ["chloe:dinner", "ethan:dinner"], "sitting by fireplace, wine glasses, laughing, close",
          [N("Večer v chatě.")]),
    panel("close-up", "l_cabin", ["ethan:dinner"], "serious, soft gaze, firelight", [("ethan", "Zůstaň přes noc.")], gap="small"),
    panel("medium", "l_cabin", ["chloe:dinner", "ethan:dinner"], "forehead to forehead, kiss, embrace, firelight",
          [("chloe", "Pomalu…")]),
    panel("medium", "l_cabin", [], "fireplace embers, snow falling outside window, no humans", [N("Oheň dohoří. Venku tiše sněží.")], gap="large"),
    panel("medium", "l_porch", ["ethan:leave"], "standing on porch, looking away, guilty, morning mist",
          [("ethan", "Musím odjet. Služební cesta. Nevím, kdy se vrátím.")]),
    panel("close-up", "l_porch", ["chloe:morning"], "sad, holding back tears, cold breath", [("chloe", "Já taky ne.")], gap="small"),
    panel("wide", "l_trail", ["chloe:morning"], "walking away alone, backpack, from behind, mountains, mist",
          [N("Chloe odchází sama. Tiše a bolestivě.")], gap="large"),
])

# 3. Maledivy — flat anime ------------------------------------------------------------------------
STORIES["rh_03_maledivy"] = story(ending(world("w_rh_03_maledivy", "Maledivy – Přesně to, co jsem hledal",
    "Aisha o sobě pochybuje, dokud k jejímu bungalovu nad vodou nepřipluje na kajaku Kai.", "flat_anime_mema", [
    char("aisha", "Aisha", "1girl", "adult, mature female, petite, dark-skinned female, dark skin, short hair, curly hair, black hair, brown eyes",
         {"default": "flowing turquoise beach dress, gold bracelets, sandals",
          "dinner": "gold satin slip dress, gold bracelets, hoop earrings, barefoot",
          "morning": "white linen sundress, gold bracelets, sun hat"},
         "a petite dark-skinned woman aged 26 with short curly black hair and gold bracelets"),
    char("kai", "Kai", "1boy", "mature male, athletic, tan skin, short hair, black hair, dark eyes",
         {"default": "white short-sleeved linen shirt, board shorts, shell necklace",
          "dinner": "cream linen shirt, linen trousers, shell necklace"},
         "an athletic Pacific Islander man aged 32 with short black hair and a linen shirt"),
], [
    loc("l_bungalow", "Bungalov nad vodou", "outdoors, overwater bungalow, wooden deck, turquoise lagoon, maldives, sunny, clear water"),
    loc("l_beach", "Večeře na pláži", "outdoors, beach dinner, table in sand, lanterns, torches, sunset, palm trees"),
    loc("l_room", "Bungalov v noci", "indoors, bungalow interior, white curtains, ocean view, night, candles"),
]), "Šťastný konec: zůstanou spolu další dny."), [
    panel("establishing", "l_bungalow", [], "overwater bungalows, turquoise lagoon", [N("Maledivy. Bungalov nad vodou.")]),
    panel("medium", "l_bungalow", ["aisha"], "sitting on deck, hugging knees, looking at reflection in water, insecure",
          [("aisha", "Jsem moc obyčejná… sem nepatřím.", "thought")]),
    panel("wide", "l_bungalow", ["kai"], "paddling kayak, approaching deck, waving, smile", sfx=["ŠPLÍCH"]),
    panel("medium", "l_bungalow", ["aisha", "kai"], "man in kayak looking up, woman on deck, blush",
          [("kai", "Ty jsi přesně to, co jsem hledal.")], gap="large"),
    panel("wide", "l_beach", ["aisha:dinner", "kai:dinner"], "sitting at table, laughing, lanterns, sunset", [N("Večeře na pláži.")]),
    panel("medium", "l_beach", ["aisha:dinner", "kai:dinner"], "holding hands across table, smile, candlelight"),
    panel("medium", "l_room", ["aisha:dinner", "kai:dinner"], "man taking off her earrings, standing, faces close",
          [("kai", "Nech mě tě obdivovat.")]),
    panel("medium", "l_room", ["aisha:dinner", "kai:dinner"], "kiss, embrace, eyes closed, candlelight", gap="small"),
    panel("medium", "l_room", [], "white curtain blowing in wind, ocean at night, moon, no humans", [N("Záclona vlaje v nočním větru.")], gap="large"),
    panel("medium", "l_bungalow", ["aisha:morning", "kai"], "morning, sitting together on deck, feet over water, her head on his shoulder",
          [("aisha", "Cítím se ženská."), ("kai", "Protože jsi.")]),
    panel("wide", "l_bungalow", ["aisha:morning", "kai"], "both paddling kayak together, lagoon, sunny", [N("Zůstávají spolu další dny.")], gap="large"),
])

# 4. Toskánsko — ligne claire ---------------------------------------------------------------------
STORIES["rh_04_toskansko"] = story(ending(world("w_rh_04_toskansko", "Toskánsko – Celá",
    "Giulia mezi vinicemi potká Lucu, který se dívá na ni celou — ale doma ho někdo čeká.", "ligne_claire", [
    char("giulia", "Giulia", "1girl", "adult, curvy, red hair, long hair, wavy hair, freckles, green eyes, pale skin",
         {"default": "emerald green wrap dress, knee boots, gold earrings",
          "barn": "emerald green wrap dress, cropped denim jacket, knee boots, gold earrings",
          "morning": "white blouse, long skirt, knee boots, hair tied"},
         "a curvy Italian woman aged 28 with long red wavy hair and freckles"),
    char("luca", "Luca", "1boy", "mature male, beard, short hair, brown hair, brown eyes, broad shoulders",
         {"default": "red flannel shirt, jeans, work boots", "evening": "red flannel shirt buttoned, jeans, rolled sleeves"},
         "a bearded Italian mechanic aged 35 in a flannel shirt"),
], [
    loc("l_vine", "Vinice", "outdoors, tuscany, vineyard, cypress trees, rolling hills, dirt road, golden afternoon"),
    loc("l_barn", "Stodola", "indoors, old barn, hay bales, wine bottle, lantern, warm light, evening"),
    loc("l_road", "Cesta za úsvitu", "outdoors, tuscany, dirt road, dawn, mist, cypress trees"),
]), "Smutný konec: on má doma přítelkyni, ona odchází."), [
    panel("establishing", "l_vine", [], "rolling hills, vineyard rows, cypress", [N("Toskánsko. Vinice.")]),
    panel("medium", "l_vine", ["giulia"], "walking on road, adjusting dress, annoyed, looking away",
          [("giulia", "Všichni se dívají jen na… tohle.", "thought")]),
    panel("wide", "l_vine", ["luca"], "leaning on old truck, wiping hands with rag, watching"),
    panel("medium", "l_vine", ["giulia", "luca"], "man walking up to woman, woman crossing arms, suspicious",
          [("luca", "Dívám se na tebe celou.")], gap="large"),
    panel("medium", "l_barn", ["giulia:barn", "luca:evening"], "sitting on hay bale, wine glasses, lantern, laughing",
          [N("Večer ve staré stodole.")]),
    panel("medium", "l_barn", ["giulia:barn", "luca:evening"], "kiss, embrace, lantern light", [("giulia", "Pomalu…")]),
    panel("medium", "l_barn", [], "lantern flame going out, hay, darkness, no humans", [N("Lucerna zhasne.")], gap="large"),
    panel("medium", "l_road", ["luca"], "standing by truck, looking down, guilty, dawn",
          [("luca", "Musím ti něco říct. Doma mám přítelkyni. Tohle byla chyba.")]),
    panel("close-up", "l_road", ["giulia:morning"], "tears, shocked, dawn light", [("giulia", "Chyba…")], gap="small"),
    panel("wide", "l_road", ["giulia:morning"], "walking away on dirt road, from behind, mist, cypress",
          [N("Giulia odchází se slzami v očích.")], gap="large"),
])

# 5. Seychely — pastel shoujo ---------------------------------------------------------------------
STORIES["rh_05_seychely"] = story(ending(world("w_rh_05_seychely", "Seychely – Hlasité ticho",
    "Tichá Mei potká na pláži Olivera, kterému její ticho připadá hlasité.", "pastel_shoujo", [
    char("mei", "Mei", "1girl", "adult, slender, east asian, long hair, straight hair, black hair, dark eyes, glasses",
         {"default": "white wide-leg jumpsuit, silver necklace, silver earrings, sandals, glasses",
          "dinner": "pale blue silk dress, silver earrings, hair up, glasses",
          "morning": "white linen shirt, wide-leg trousers, sun hat, glasses"},
         "a slender East Asian woman aged 30 with long straight black hair and glasses"),
    char("oliver", "Oliver", "1boy", "mature male, slender, short hair, brown hair, glasses, gentle eyes",
         {"default": "beige linen suit, white shirt, glasses", "dinner": "white linen shirt, beige linen trousers, glasses"},
         "a slender office worker aged 38 in a beige linen suit and glasses"),
], [
    loc("l_beach", "Pláž", "outdoors, seychelles, beach, granite boulders, palm trees, turquoise water, sunny"),
    loc("l_yacht", "Jachta", "outdoors, yacht deck, evening, sunset, sea, candles, dinner table"),
    loc("l_cabin", "Kajuta", "indoors, yacht cabin, wooden interior, porthole, lamp, night"),
]), "Šťastný konec: zůstanou spolu."), [
    panel("establishing", "l_beach", [], "granite boulders, palm trees, turquoise sea", [N("Seychely.")]),
    panel("medium", "l_beach", ["mei"], "walking alone on beach, holding sandals, looking down, quiet",
          [("mei", "Jsem moc tichá…", "thought")]),
    panel("wide", "l_beach", ["oliver"], "walking on beach, hands in pockets, noticing someone"),
    panel("medium", "l_beach", ["mei", "oliver"], "walking side by side, woman looking up surprised, man smiling",
          [("oliver", "Tvoje ticho je hlasité.")], gap="large"),
    panel("wide", "l_yacht", ["mei:dinner", "oliver:dinner"], "dinner on yacht, talking, sunset", [N("Večeře na jachtě.")]),
    panel("medium", "l_yacht", ["mei:dinner", "oliver:dinner"], "fingers touching on table, blush, candlelight"),
    panel("medium", "l_cabin", ["mei:dinner", "oliver:dinner"], "man taking off her glasses gently, faces close",
          [("oliver", "Nech mě tě vidět.")]),
    panel("medium", "l_cabin", ["mei:dinner", "oliver:dinner"], "foreheads touching, kiss, eyes closed",
          [("mei", "Cítím se viděná."), ("oliver", "A milovaná.")], gap="small"),
    panel("medium", "l_cabin", [], "porthole, moon over sea, lamp off, no humans", [N("Měsíc nad mořem.")], gap="large"),
    panel("wide", "l_beach", ["mei:morning", "oliver"], "morning, walking hand in hand on beach, smile", [N("Zůstávají spolu.")], gap="large"),
])

# 6. Capri — glossy photo -------------------------------------------------------------------------
STORIES["rh_06_capri"] = story(ending(world("w_rh_06_capri", "Capri – Víc než svaly",
    "Marcus si myslí, že ženy chtějí jen jeho tělo, dokud na skalách Capri nepotká Lilu.", "photo_glossy", [
    char("marcus", "Marcus", "1boy", "mature male, muscular, dark-skinned male, dark skin, short hair, black hair, brown eyes",
         {"default": "white linen shirt, beige linen trousers, loafers", "dinner": "black linen shirt, dark trousers, wristwatch"},
         "a muscular dark-skinned man aged 33 with short black hair"),
    char("lila", "Lila", "1girl", "adult, mature female, petite, curvy, long hair, wavy hair, auburn hair, hazel eyes",
         {"default": "red mini dress, short dress, high heels, gold hoop earrings, sunglasses on head",
          "dinner": "black satin dress, high heels, gold earrings, hair up",
          "morning": "white sundress, sandals, straw hat"},
         "a petite curvy woman aged 27 with long auburn wavy hair"),
], [
    loc("l_rocks", "Skály", "outdoors, capri, cliffs, faraglioni rocks, sea, path, sunshine"),
    loc("l_dinner", "Večeře", "outdoors, restaurant terrace, lemon trees, string lights, sea view, evening"),
    loc("l_villa", "Vila", "indoors, villa, white walls, open balcony door, sea view, night, candles"),
]), "Šťastný konec: zůstanou spolu."), [
    panel("establishing", "l_rocks", [], "faraglioni rocks, cliffs, blue sea", [N("Capri.")]),
    panel("medium", "l_rocks", ["marcus"], "standing on cliff path, looking at sea, sad",
          [("marcus", "Chtějí jen tělo…", "thought")]),
    panel("wide", "l_rocks", ["lila"], "walking on cliff path, wind, holding sunglasses"),
    panel("medium", "l_rocks", ["marcus", "lila"], "woman stopping beside man, looking up, smile, man surprised",
          [("lila", "Já chci tebe.")], gap="large"),
    panel("wide", "l_dinner", ["marcus:dinner", "lila:dinner"], "dinner, laughing, string lights, lemon trees", [N("Večeře.")]),
    panel("medium", "l_dinner", ["marcus:dinner", "lila:dinner"], "kiss across table, candlelight", gap="small"),
    panel("medium", "l_villa", ["marcus:dinner", "lila:dinner"], "woman taking off her high heels, man holding her hand, smile",
          [("marcus", "Pomalu…")]),
    panel("medium", "l_villa", ["marcus:dinner", "lila:dinner"], "embrace, kiss, her hands on his shoulders, candlelight"),
    panel("medium", "l_villa", [], "balcony door, curtain in wind, moonlit sea, no humans", [N("Závěs zavane. Dveře se zavřou.")], gap="large"),
    panel("medium", "l_villa", ["marcus", "lila:morning"], "morning, coffee on balcony, hugging, sea view",
          [("marcus", "Cítím se víc než svaly."), ("lila", "Protože jsi.")]),
    panel("wide", "l_rocks", ["marcus", "lila:morning"], "walking hand in hand on cliff path, sunshine", [N("Zůstávají.")], gap="large"),
])

# 7. Norské fjordy — noir mono --------------------------------------------------------------------
STORIES["rh_07_fjordy"] = story(ending(world("w_rh_07_fjordy", "Fjordy – Zastav se",
    "Erik pořád běží, dokud ho na stezce nad fjordem nezastaví Sofia — jen na jednu dovolenou.", "noir_mono", [
    char("erik", "Erik", "1boy", "mature male, athletic, short hair, blonde hair, blue eyes, stubble",
         {"default": "running jacket, running tights, trail shoes", "dinner": "cable-knit sweater, dark trousers"},
         "an athletic Norwegian man aged 35 with short blonde hair"),
    char("sofia", "Sofia", "1girl", "adult, mature female, petite, long hair, dark hair, brown eyes",
         {"default": "puffer jacket, knit hat, hiking boots", "dinner": "black wool dress, ankle boots, silver earrings",
          "leave": "long wool coat, scarf, suitcase"},
         "a petite woman aged 28 with long dark hair"),
], [
    loc("l_trail", "Stezka nad fjordem", "outdoors, norway, fjord, mountain trail, cliffs, clouds, cold"),
    loc("l_cabin", "Chata", "indoors, cabin, fireplace, candles, wooden walls, window, night"),
    loc("l_dock", "Přístaviště", "outdoors, ferry dock, fjord, morning fog, ferry"),
]), "Smutný konec: pro ni to bylo jen dovolenkové, Erik zůstává sám."), [
    panel("establishing", "l_trail", [], "fjord, cliffs, low clouds", [N("Norské fjordy.")]),
    panel("wide", "l_trail", ["erik"], "running on trail, sweat, determined, motion blur",
          [("erik", "Vždycky běžím…", "thought")]),
    panel("medium", "l_trail", ["erik", "sofia"], "woman standing on trail, raising hand, man stopping, breathing hard",
          [("sofia", "Zastav se.")], gap="large"),
    panel("medium", "l_cabin", ["erik:dinner", "sofia:dinner"], "dinner by fireplace, candles, talking", [N("Večer v chatě.")]),
    panel("close-up", "l_cabin", ["sofia:dinner"], "taking off earrings, soft smile, firelight"),
    panel("medium", "l_cabin", ["erik:dinner", "sofia:dinner"], "kiss, embrace, firelight, shadows", [("erik", "Pomalu.")], gap="small"),
    panel("medium", "l_cabin", [], "candle smoke, extinguished candle, window, night, no humans", [N("Svíčka zhasne.")], gap="large"),
    panel("medium", "l_dock", ["sofia:leave"], "standing with suitcase, looking away, fog",
          [("sofia", "Musím domů. Bylo to krásné… ale jen dovolenkové.")]),
    panel("close-up", "l_dock", ["erik"], "silent, hurt, fog, looking down", gap="small"),
    panel("wide", "l_dock", ["erik"], "standing alone on dock, ferry leaving in fog, from behind", [N("Erik zůstává sám.")], gap="large"),
])

# 8. Bali — anime screencap -----------------------------------------------------------------------
STORIES["rh_08_bali"] = story(ending(world("w_rh_08_bali", "Bali – Ring není všechno",
    "Boxer Diego žije jen pro ring, dokud mu Isabella v rýžových polích neřekne ne.", "anime_screencap", [
    char("diego", "Diego", "1boy", "mature male, muscular, beard, short hair, black hair, brown eyes, scar on face",
         {"default": "black t-shirt, cargo shorts, hand wraps", "dinner": "white linen shirt, dark trousers"},
         "a muscular bearded boxer aged 31"),
    char("isabella", "Isabella", "1girl", "adult, tall female, long hair, blonde hair, blue eyes",
         {"default": "yellow silk midi dress, gold necklace, gold earrings, straw hat, sandals",
          "dinner": "gold sequin dress, gold earrings, hair up, high heels",
          "morning": "white linen dress, gold necklace, barefoot"},
         "a tall blonde woman aged 26 in a yellow silk dress with gold jewellery"),
], [
    loc("l_rice", "Rýžová pole", "outdoors, bali, rice terraces, palm trees, green, sunny, mountains"),
    loc("l_villa", "Vila", "outdoors, villa terrace, infinity pool, jungle, lanterns, night, candles"),
    loc("l_room", "Pokoj", "indoors, bamboo villa room, mosquito net, carved wood, lanterns, night"),
]), "Šťastný konec: zůstanou spolu."), [
    panel("establishing", "l_rice", [], "rice terraces, palm trees, morning mist", [N("Bali.")]),
    panel("medium", "l_rice", ["diego"], "shadow boxing on path, sweat, serious",
          [("diego", "Ring je všechno…")]),
    panel("medium", "l_rice", ["diego", "isabella"], "woman standing in path, hands on hips, smile, man stopping",
          [("isabella", "Ne.")], gap="small"),
    panel("close-up", "l_rice", ["isabella"], "playful smile, straw hat, sunlight",
          [("isabella", "Ring je jen místo. Ty jsi víc.")], gap="large"),
    panel("wide", "l_villa", ["diego:dinner", "isabella:dinner"], "dinner by pool, lanterns, laughing", [N("Večeře ve vile.")]),
    panel("medium", "l_villa", ["diego:dinner", "isabella:dinner"], "kiss, lantern light, pool reflections", gap="small"),
    panel("medium", "l_room", ["diego:dinner", "isabella:dinner"], "woman taking off her earrings, man holding her waist, standing",
          [("diego", "Pomalu.")]),
    panel("medium", "l_room", [], "lantern flame dimming, mosquito net, jungle night, no humans", [N("Lucerny dohoří.")], gap="large"),
    panel("medium", "l_villa", ["diego", "isabella:morning"], "morning, sitting by pool, her head on his shoulder",
          [("diego", "Cítím se jako muž."), ("isabella", "Protože jsi.")]),
    panel("wide", "l_rice", ["diego", "isabella:morning"], "walking together through rice terraces, holding hands", [N("Zůstávají.")], gap="large"),
])

# 9. Amalfi — webtoon -----------------------------------------------------------------------------
STORIES["rh_09_amalfi"] = story(ending(world("w_rh_09_amalfi", "Amalfi – Nudný",
    "Adrian si o sobě myslí, že je nudný; Sari tvrdí opak — ale doma ji čeká přítel.", "webtoon_romance", [
    char("adrian", "Adrian", "1boy", "mature male, slender, short hair, brown hair, glasses, grey eyes",
         {"default": "light grey suit, white shirt, glasses, loafers", "dinner": "navy shirt, beige chinos, glasses"},
         "a slender office type aged 37 with glasses and a light grey suit"),
    char("sari", "Sari", "1girl", "adult, mature female, petite, tan skin, long hair, black hair, dark eyes",
         {"default": "orange floral silk dress, high heels, gold earrings, sunglasses",
          "dinner": "deep red satin dress, high heels, gold earrings",
          "morning": "white blouse, linen trousers, sandals, hair tied"},
         "a petite Indonesian woman aged 25 with long black hair and a floral silk dress"),
], [
    loc("l_deck", "Paluba", "outdoors, yacht deck, amalfi coast, colorful cliff houses, sea, sunny"),
    loc("l_cabin", "Kajuta", "indoors, yacht cabin, wood paneling, wine glasses, lamp, night"),
    loc("l_deck_m", "Paluba ráno", "outdoors, yacht deck, morning, amalfi coast, empty deck chairs, calm sea"),
]), "Smutný konec: ona má doma přítele, Adrian zůstane sám."), [
    panel("establishing", "l_deck", [], "amalfi coast, colorful houses on cliffs, yacht", [N("Pobřeží Amalfi.")]),
    panel("medium", "l_deck", ["adrian"], "sitting on deck, reading papers, loosening collar, sigh",
          [("adrian", "Jsem nudný…", "thought")]),
    panel("medium", "l_deck", ["adrian", "sari"], "woman sitting beside him, taking off sunglasses, smile",
          [("sari", "Nejsi.")], gap="large"),
    panel("medium", "l_cabin", ["adrian:dinner", "sari:dinner"], "wine glasses, sitting close, laughing", [N("Večer v kajutě.")]),
    panel("medium", "l_cabin", ["adrian:dinner", "sari:dinner"], "kiss, embrace, lamp light", [("adrian", "Pomalu.")], gap="small"),
    panel("medium", "l_cabin", [], "lamp switching off, porthole, moonlit sea, no humans", [N("Lampa zhasne.")], gap="large"),
    panel("medium", "l_deck_m", ["sari:morning"], "standing at railing, holding phone, guilty, looking away",
          [("sari", "Adriane… doma mám přítele. Tohle byla chyba.")]),
    panel("close-up", "l_deck_m", ["adrian"], "silent, hurt, taking off glasses", gap="small"),
    panel("wide", "l_deck_m", ["adrian"], "sitting alone on deck, empty chair beside him, from behind, sea",
          [N("Adrian zůstává na jachtě sám.")], gap="large"),
])

# 10. Kostarika — fast photoreal ------------------------------------------------------------------
STORIES["rh_10_kostarika"] = story(ending(world("w_rh_10_kostarika", "Kostarika – Doma",
    "Kovboj Cole se považuje jen za venkovana, Amara mu na pláži ukáže, že je víc.", "photo_lightning", [
    char("cole", "Cole", "1boy", "mature male, beard, tan skin, short hair, brown hair, brown eyes, broad shoulders",
         {"default": "denim shirt, jeans, cowboy boots, cowboy hat", "dinner": "white shirt, jeans, cowboy boots"},
         "a bearded cowboy aged 35"),
    char("amara", "Amara", "1girl", "adult, mature female, petite, curvy, dark-skinned female, curly hair, long hair, black hair, brown eyes",
         {"default": "tropical print beach dress, gold bangles, sandals",
          "dinner": "coral silk dress, gold hoop earrings, barefoot",
          "morning": "white cotton sundress, gold bangles, straw hat"},
         "a petite curvy woman aged 27 with long curly black hair"),
], [
    loc("l_beach", "Pláž", "outdoors, costa rica, beach, jungle edge, palm trees, waves, golden hour"),
    loc("l_bungalow", "Bungalov", "outdoors, beach bungalow porch, hammock, lanterns, jungle, night, dinner table"),
    loc("l_porch_m", "Ráno", "outdoors, bungalow porch, morning, jungle, sea view, coffee"),
]), "Šťastný konec: zůstanou spolu."), [
    panel("establishing", "l_beach", [], "beach, jungle, waves, golden hour", [N("Kostarika.")]),
    panel("medium", "l_beach", ["cole"], "sitting on driftwood, holding cowboy hat, looking at sea",
          [("cole", "Jsem jen venkovan…")]),
    panel("medium", "l_beach", ["cole", "amara"], "woman sitting down beside him, smile, man surprised",
          [("amara", "Jsi víc.")], gap="large"),
    panel("wide", "l_bungalow", ["cole:dinner", "amara:dinner"], "dinner on porch, lanterns, laughing", [N("Večeře v bungalovu.")]),
    panel("medium", "l_bungalow", ["cole:dinner", "amara:dinner"], "kiss, lantern light, jungle night", gap="small"),
    panel("medium", "l_bungalow", ["cole:dinner", "amara:dinner"], "woman putting his cowboy hat on her head, laughing, embrace",
          [("cole", "Pomalu.")]),
    panel("medium", "l_bungalow", [], "door closing, lanterns, hammock swaying, jungle night, no humans", [N("Dveře se zavřou.")], gap="large"),
    panel("medium", "l_porch_m", ["cole", "amara:morning"], "morning, coffee, sitting close on porch, his arm around her",
          [("cole", "Cítím se doma."), ("amara", "Protože jsi se mnou.")]),
    panel("wide", "l_beach", ["cole", "amara:morning"], "walking on beach together, holding hands, morning", [N("Zůstávají spolu.")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
