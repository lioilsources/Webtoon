"""Romance set F — fashion & flirt, stories 11–20 ("Pokračuji jako 10 dospělých romantických scénářů…").

    python3 m0/romance_f.py        → data/stories/rf_*/{world,storyboard}.json

Same building blocks and rules as stories_romance.py: one medium per story, dialogue near-verbatim (typos fixed),
inner monologue as thought bubbles, never two characters of the same gender in one panel. Fashion carries the
set: every character has named outfits. Intimate scenes end on a kiss and a fade-to-black panel; mornings are
fully dressed. No brand names, no swimwear, men keep their shirts on.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}


def ending(w, text):
    w["canon"]["constraints"] = [text]
    return w


# 11. Saint-Tropez — fashion editorial -------------------------------------------------------------
STORIES["rf_01_sainttropez"] = story(ending(world("w_rf_01_sainttropez", "Saint-Tropez – Léto, které mělo trvat navždy",
    "Valérie přijede do Saint-Tropez sama, Nicolas jí chytí klobouk a jedno léto změní všechno.", "fashion_editorial", [
    char("valerie", "Valérie", "1girl", "adult, mature female, mature female, curvy, long hair, chestnut hair, wavy hair, brown eyes",
         {"default": "white sundress, wide-brim straw hat, oversized sunglasses, white leather knee boots, thin gold necklace",
          "day": "crisp white button-up shirt, tailored beige shorts, oversized sunglasses, gold hoop earrings, leather sandals",
          "evening": "emerald silk slip dress, delicate gold jewelry, gold drop earrings, strappy high heels, hair down",
          "beach": "flowing ivory linen maxi dress, loose hair, bare feet, thin gold bracelet"},
         "a petite curvy French woman aged 32 with long wavy chestnut hair and warm brown eyes, elegant and feminine"),
    char("nicolas", "Nicolas", "1boy", "mature male, tall, athletic, tan, short hair, dark hair, brown eyes, light stubble",
         {"default": "white linen shirt, buttoned shirt, navy chino trousers, leather loafers, steel wristwatch",
          "evening": "navy linen blazer, white shirt, buttoned shirt, beige trousers, wristwatch",
          "travel": "light grey cashmere sweater, dark trousers, leather weekender bag"},
         "a tall tanned athletic French man aged 37 with short dark hair and light stubble, simple but expensive clothes"),
], [
    loc("l_port", "Přístav", "outdoors, harbor, saint-tropez, yachts, pastel houses, palm trees, sunny, blue sky, summer"),
    loc("l_yacht", "Jachta", "outdoors, yacht deck, bow of yacht, sea, sunset, champagne glasses, orange sky"),
    loc("l_hotel", "Hotel", "indoors, luxury hotel room, night, city lights through window, warm lamp, vanity table"),
    loc("l_beach", "Pláž", "outdoors, beach, autumn, overcast, empty beach, waves, wet sand"),
]), "Hořkosladký konec."), [
    panel("establishing", "l_port", [], "convertible car, yachts, sunny harbor", [N("Saint-Tropez. Léto.")]),
    panel("full body", "l_port", ["valerie"], "stepping out of convertible, holding hat, sunglasses, confident",
          [("valerie", "Tentokrát nikoho hledat nebudu.")]),
    panel("medium", "l_port", ["valerie"], "wind, hat flying away, reaching out, surprised, hair blowing", sfx=["FÍÍ!"], gap="small"),
    panel("medium", "l_port", ["nicolas"], "catching straw hat, holding hat, smile, looking at viewer",
          [("nicolas", "Možná vás hledá on.")]),
    panel("medium", "l_yacht", ["valerie:evening", "nicolas:evening"], "standing at bow, sunset, champagne glasses, wind in hair",
          [("nicolas", "Jste šťastná?"), ("valerie", "Právě teď ano.")]),
    panel("medium", "l_yacht", ["valerie:evening", "nicolas:evening"], "hands touching, holding hands on railing, sunset", gap="large"),
    panel("medium", "l_hotel", ["valerie:evening"], "taking off earrings, vanity table, mirror, soft smile",
          [N("Odloží náušnice. Pak hodinky.")]),
    panel("medium", "l_hotel", ["valerie:evening", "nicolas:evening"], "standing by door, looking at each other, tension",
          [("valerie", "Neměl bys zůstat."), ("nicolas", "Vím.")], gap="small"),
    panel("medium", "l_hotel", ["valerie:evening", "nicolas:evening"], "kiss, embrace, eyes closed"),
    panel("wide", "l_hotel", [], "closed curtains, city lights outside window, lamp off, dark room",
          [N("Světla města zůstanou za oknem.")], gap="large"),
    panel("medium", "l_hotel", ["valerie:day", "nicolas:travel"], "morning light, plane ticket on table, serious",
          [("nicolas", "Musím odjet."), ("valerie", "Na jak dlouho?"), ("nicolas", "Nevím.")]),
    panel("close-up", "l_hotel", ["valerie:day"], "looking away, sad smile",
          [("nicolas", "Vrátím se."), ("valerie", "To říkají všichni.")], gap="large"),
    panel("wide", "l_beach", ["valerie:beach"], "walking along shoreline, from behind, tears, smile",
          [N("O tři měsíce později. Nicolas nepřijel."), ("valerie", "Aspoň jsem jednou opravdu milovala.")], gap="large"),
])

# 12. Kyoto — ink wash ---------------------------------------------------------------------------------
STORIES["rf_02_kyoto"] = story(ending(world("w_rf_02_kyoto", "Kjóto – Déšť mezi sakurami",
    "Maya jede na kole Kjótem a britský fotograf Adrian kvůli ní narazí do stojanu.", "ink_wash", [
    char("maya", "Maya", "1girl", "adult, mature female, petite, slender, short hair, black hair, bob cut, glasses, dark eyes",
         {"default": "long camel coat, black turtleneck, wide trousers, ankle boots",
          "rain": "long grey coat, wet hair, black turtleneck, ankle boots",
          "silk": "simple ivory silk dress, long sleeves, hair tucked behind ear"},
         "a petite slender Japanese woman aged 28 with a short black bob and glasses, minimalist style"),
    char("adrian", "Adrian", "1boy", "mature male, tall, muscular, light brown hair, short hair, blue eyes",
         {"default": "olive field jacket, grey henley shirt, dark jeans, camera strap, camera",
          "rain": "dark rain jacket, wet hair, camera bag",
          "travel": "navy wool coat, grey sweater, suitcase"},
         "a tall muscular British photographer aged 35 with light brown hair, field jacket and a camera"),
], [
    loc("l_street", "Ulička", "outdoors, narrow street, kyoto, wooden houses, cherry blossoms, bicycle, spring"),
    loc("l_forest", "Hory", "outdoors, mountain forest, rain, small wooden shelter, mist, cedar trees"),
    loc("l_ryokan", "Ryokan", "indoors, ryokan, tatami, shoji, paper lamp, evening, traditional room"),
    loc("l_station", "Nádraží", "indoors, train station platform, morning, shinkansen, departing train"),
]), "Otevřený konec."), [
    panel("establishing", "l_street", [], "cherry blossoms, narrow street, petals falling", [N("Kjóto. Jaro.")]),
    panel("wide", "l_street", ["maya"], "riding bicycle, coat flowing, petals"),
    panel("medium", "l_street", ["adrian"], "crashing bicycle into bike rack, falling, surprised", sfx=["BÁC!"], gap="small"),
    panel("medium", "l_street", ["maya", "adrian"], "woman bending over man, concerned, man smiling sheepishly",
          [("maya", "Jste v pořádku?"), ("adrian", "Ano. Jen jsem se snažil sledovat vás.")]),
    panel("close-up", "l_street", ["maya"], "blush, looking away, adjusting glasses", gap="large"),
    panel("wide", "l_forest", ["maya:rain", "adrian:rain"], "hiking, rain, running to shelter", [N("Výlet do hor. Déšť.")]),
    panel("medium", "l_forest", ["maya:rain", "adrian:rain"], "under shelter, man handing towel, woman holding wet coat",
          [("adrian", "Jsi nádherná."), ("maya", "To říkáš jen proto, že prší."), ("adrian", "Právě proto.")]),
    panel("medium", "l_forest", ["maya:rain", "adrian:rain"], "kiss, rain, eyes closed", gap="large"),
    panel("medium", "l_ryokan", ["maya:silk", "adrian"], "sitting side by side on tatami, embrace, paper lamp",
          [("maya", "Zítra odjíždíš."), ("adrian", "Ano."), ("maya", "Tak na zítřek nemysleme.")]),
    panel("wide", "l_ryokan", [], "paper lamp turned off, shoji screen, two silhouettes embracing behind shoji, dark",
          [N("Zhasnou lampu.")], gap="large"),
    panel("medium", "l_station", ["maya", "adrian:travel"], "platform, man holding suitcase, facing each other",
          [("adrian", "Počkej na mě."), ("maya", "Jak dlouho?"), ("adrian", "Nevím.")]),
    panel("wide", "l_station", ["maya"], "standing alone on platform, train leaving, from behind",
          [N("Vlak odjíždí. Maya zůstane stát.")], gap="large"),
])

# 13. Maledivy — glossy photo --------------------------------------------------------------------------
STORIES["rf_03_maledivy"] = story(ending(world("w_rf_03_maledivy", "Maledivy – Žena, která nevěřila na krásu",
    "Módní návrhářka Sofia o sobě pochybuje, dokud ji Leon nezačne potkávat náhodou každý den.", "photo_glossy", [
    char("sofia", "Sofia", "1girl", "adult, mature female, curvy, plus size, long hair, curly hair, dark brown hair, tan skin, brown eyes",
         {"default": "elegant black evening gown, statement earrings, high heels, curly hair down",
          "day": "white linen wrap dress, straw sun hat, gold bracelets, sandals",
          "dance": "flowing coral chiffon dress, statement earrings, barefoot, hair loose"},
         "a curvy Brazilian woman aged 34 with long dark curly hair and warm brown eyes, fashion designer"),
    char("leon", "Leon", "1boy", "mature male, tall, athletic, blonde hair, short hair, blue eyes, clean-shaven",
         {"default": "tailored cream dinner jacket, white shirt, buttoned shirt, black trousers",
          "day": "light blue linen shirt, buttoned shirt, white chinos, sunglasses"},
         "a tall athletic German businessman aged 39 with short blonde hair, always perfectly groomed"),
], [
    loc("l_resort", "Resort", "outdoors, luxury resort, maldives, overwater villas, evening, lanterns, palm trees"),
    loc("l_beach", "Pláž", "outdoors, white sand beach, turquoise water, morning, palm trees, sunny"),
    loc("l_night", "Pláž v noci", "outdoors, beach, night, torches, string lights, sea, stars"),
    loc("l_terrace", "Terasa", "outdoors, villa terrace, night, candle, ocean view, moonlight"),
]), "Šťastný konec."), [
    panel("establishing", "l_resort", [], "overwater villas, lanterns, sunset", [N("Maledivy. Luxusní resort.")]),
    panel("full body", "l_resort", ["sofia"], "walking, evening gown, looking down, insecure",
          [("sofia", "Navrhuju šaty pro krásné ženy. Sama mezi ně nepatřím.", "thought")]),
    panel("medium", "l_resort", ["sofia", "leon"], "man approaching, slight bow, woman turning",
          [("leon", "Promiňte."), ("sofia", "Ano?"), ("leon", "Jen jsem chtěl říct, že vám ty šaty sluší.")]),
    panel("medium", "l_resort", ["sofia", "leon"], "woman raising eyebrow, man embarrassed smile",
          [("sofia", "To je všechno?"), ("leon", "Ne. Ale první větu jsem už pokazil.")], gap="large"),
    panel("medium", "l_beach", ["sofia:day", "leon:day"], "meeting on beach, woman laughing, sun hat",
          [("sofia", "Vy mě sledujete?"), ("leon", "Ne. Doufám, že se mi to podaří náhodou každý den.")]),
    panel("wide", "l_night", ["sofia:dance", "leon"], "dancing on beach, barefoot, holding shoes, torches",
          [("leon", "Můžu tě obejmout?"), ("sofia", "Už to děláš.")]),
    panel("medium", "l_night", ["sofia:dance", "leon"], "kiss, embrace, torchlight", gap="large"),
    panel("medium", "l_terrace", ["sofia:dance"], "sitting, taking off earrings, placing earrings on table, soft smile"),
    panel("medium", "l_terrace", ["sofia:dance", "leon"], "man kissing woman on forehead, eyes closed, candlelight", gap="large"),
    panel("medium", "l_beach", ["sofia:day"], "reading phone, shocked, worried", [N("Ráno přijde zpráva. Její firma zkrachovala.")]),
    panel("medium", "l_beach", ["sofia:day", "leon:day"], "man holding woman's hands, serious, determined",
          [("leon", "Co se stalo?"), ("sofia", "Musím domů."), ("leon", "Pojedu s tebou."), ("sofia", "Proč?")]),
    panel("close-up", "l_beach", ["leon:day"], "gentle smile, looking at viewer",
          [("leon", "Protože nechci, aby náš příběh skončil tam, kde začal.")], gap="large"),
])

# 14. New Orleans — noir mono --------------------------------------------------------------------------
STORIES["rf_04_neworleans"] = story(ending(world("w_rf_04_neworleans", "New Orleans – Zrzka a jazzový klub",
    "Irka Emma vejde do jazzového klubu, kde boxer James hraje na piano jen pro ni.", "noir_mono", [
    char("emma", "Emma", "1girl", "adult, tall female, curvy, long hair, wavy hair, red hair, freckles, green eyes",
         {"default": "sequined cocktail dress, knee-high heeled boots, vintage pearl earrings, red lipstick",
          "street": "sequined cocktail dress, bare feet, holding boots, vintage pearl earrings",
          "travel": "belted trench coat, silk scarf, ankle boots, suitcase"},
         "a tall curvy Irish woman aged 30 with long copper-red wavy hair and freckles"),
    char("james", "James", "1boy", "mature male, dark-skinned male, very dark skin, tall, muscular, short hair, black hair, brown eyes",
         {"default": "white dress shirt, buttoned shirt, black waistcoat, rolled sleeves, black trousers",
          "night": "black suit, white shirt, buttoned shirt, loose necktie"},
         "a tall muscular African American man aged 36, former boxer who owns a small jazz club"),
], [
    loc("l_club", "Jazzový klub", "indoors, jazz club, grand piano, stage, smoke, dim spotlight, night, small tables"),
    loc("l_street", "French Quarter", "outdoors, french quarter, night, wrought iron balconies, gas lamps, wet street"),
    loc("l_backstage", "Zákulisí", "indoors, backstage, dressing room, mirror with lights, night"),
    loc("l_door", "Dveře klubu", "outdoors, club entrance, morning, door, street, overcast"),
]), "Smutný konec."), [
    panel("establishing", "l_club", [], "piano on stage, smoke, spotlight", [N("New Orleans. Klub, kde hraje jazz.")]),
    panel("full body", "l_club", ["emma"], "entering club, standing in doorway, looking around"),
    panel("medium", "l_club", ["james"], "playing piano, spotlight, looking up, eyes meeting", sfx=["♪"]),
    panel("medium", "l_club", ["emma", "james"], "man standing by woman's table, offering hand",
          [("james", "Tančíte?"), ("emma", "Jen když se mi líbí hudba."), ("james", "Tak dnes máte štěstí.")], gap="large"),
    panel("wide", "l_street", ["emma", "james"], "dancing in street, laughing, gas lamps"),
    panel("medium", "l_street", ["emma:street", "james"], "woman holding boots, barefoot, man laughing",
          [("james", "Bolí?"), ("emma", "Krása něco stojí."), ("james", "Tak příště přijďte v teniskách.")]),
    panel("medium", "l_street", ["emma:street", "james"], "woman smiling, man shy smile",
          [("emma", "Příště?"), ("james", "Doufal jsem.")], gap="large"),
    panel("medium", "l_backstage", ["emma", "james:night"], "man tucking strand of hair behind her ear, mirror lights",
          [("emma", "Proč se na mě tak díváš?"), ("james", "Protože se bojím, že když mrknu, zmizíš.")]),
    panel("medium", "l_backstage", ["emma", "james:night"], "kiss, eyes closed", gap="large"),
    panel("medium", "l_door", ["emma:travel", "james"], "woman with suitcase, man in doorway, serious",
          [("james", "Takže odjíždíš."), ("emma", "Ano."), ("james", "A vrátíš se?")]),
    panel("medium", "l_door", ["emma:travel", "james"], "hug, woman's sad face over his shoulder",
          [("emma", "Nevím.")]),
    panel("wide", "l_door", ["james"], "standing alone in doorway, empty street, sad", [N("James zůstane stát ve dveřích.")], gap="large"),
])

# 15. Vancouver — thin paint ---------------------------------------------------------------------------
STORIES["rf_05_vancouver"] = story(ending(world("w_rf_05_vancouver", "Vancouver – Muž, který našel lásku v horách",
    "Horský průvodce Marcus pomůže na stezce Mexičance Eleně, která přijela začít znovu.", "thin_paint", [
    char("marcus", "Marcus", "1boy", "mature male, very tall, muscular, dark hair, short hair, short beard, brown eyes",
         {"default": "red plaid flannel shirt, buttoned shirt, dark green outdoor vest, hiking boots, backpack",
          "cabin": "grey henley shirt, buttoned shirt, dark jeans, wool socks",
          "wedding": "charcoal suit, white shirt, buttoned shirt, boutonniere"},
         "a very tall muscular Canadian mountain guide aged 40 with short dark hair and a short beard"),
    char("elena", "Elena", "1girl", "adult, mature female, mature female, curvy, long hair, black hair, brown eyes",
         {"default": "fitted burgundy outdoor jacket, black leggings, hiking boots, hair in ponytail",
          "cabin": "oversized cream knit sweater, wool socks, hair down",
          "wedding": "simple white lace dress, flower crown, long hair down"},
         "a petite elegant Mexican woman aged 35 with long black hair and brown eyes"),
], [
    loc("l_trail", "Horská stezka", "outdoors, mountain trail, rocky path, pine trees, mountains, clear sky"),
    loc("l_forest", "Les", "outdoors, dense forest, tall cedars, moss, sunbeams"),
    loc("l_cabin", "Chata", "indoors, log cabin, fireplace, fire, night, warm light, mugs"),
    loc("l_valley", "Údolí", "outdoors, valley, morning, mist, lake, mountains"),
    loc("l_lake", "Jezero", "outdoors, lakeside, small wedding arch, flowers, summer, mountains, sunny"),
]), "Šťastný konec."), [
    panel("establishing", "l_trail", [], "mountains, hiking group in distance", [N("Hory nad Vancouverem.")]),
    panel("wide", "l_trail", ["elena"], "tripping on rock, falling, surprised", sfx=["UPS!"], gap="small"),
    panel("medium", "l_trail", ["elena", "marcus"], "man offering hand, woman sitting on ground, embarrassed laugh",
          [("marcus", "V pořádku?"), ("elena", "Moje důstojnost je mrtvá."), ("marcus", "Tu můžeme pohřbít nahoře.")], gap="large"),
    panel("medium", "l_forest", ["elena", "marcus"], "walking side by side, sunbeams, talking",
          [("elena", "Proč ses nikdy neoženil?"), ("marcus", "Čekal jsem."), ("elena", "Na co?")]),
    panel("close-up", "l_forest", ["marcus"], "gentle smile, looking at viewer",
          [("marcus", "Na ženu, která se mě zeptá na něco jiného než na počasí.")], gap="large"),
    panel("medium", "l_cabin", ["elena:cabin", "marcus:cabin"], "man handing mug, fireplace, woman wrapped in sweater",
          [("marcus", "Je ti zima?"), ("elena", "Trochu.")]),
    panel("medium", "l_cabin", ["elena:cabin", "marcus:cabin"], "man pulling her close, sitting by fire, embrace",
          [("elena", "Teď už ne.")], gap="small"),
    panel("medium", "l_cabin", ["elena:cabin", "marcus:cabin"], "kiss, firelight, eyes closed", gap="large"),
    panel("medium", "l_valley", ["elena", "marcus"], "woman holding phone, crying, man concerned",
          [N("Ráno zavolají z Mexico City. Nabízejí jí práci."), ("marcus", "To je skvělá zpráva."), ("marcus", "Tak proč pláčeš?")]),
    panel("medium", "l_valley", ["elena", "marcus"], "hug, tears",
          [("elena", "Protože jsem právě našla něco, co nechci opustit.")], gap="large"),
    panel("wide", "l_lake", ["elena:wedding"], "arriving on bicycle, white dress, lakeside", [N("O rok později.")]),
    panel("medium", "l_lake", ["elena:wedding", "marcus:wedding"], "wedding arch, smiling, holding hands",
          [("elena", "Přišla jsem pozdě?"), ("marcus", "O rok.")]),
    panel("medium", "l_lake", ["elena:wedding", "marcus:wedding"], "kiss, flowers, sunny", gap="large"),
])

# 16. Monte Carlo — night neon photo -------------------------------------------------------------------
STORIES["rf_06_montecarlo"] = story(ending(world("w_rf_06_montecarlo", "Monte Carlo – Muž, který si vybral špatně",
    "Investor Victor si na své jachtě vybere okouzlující Claire a přehlédne fotografku Sofii.", "photo_cyberreal_night", [
    char("victor", "Victor", "1boy", "mature male, tall, slender, grey hair, short hair, brown eyes",
         {"default": "black tuxedo, white shirt, buttoned shirt, black bow tie",
          "day": "light grey linen suit, white shirt, buttoned shirt, no necktie"},
         "an elegant tall slender Spanish investor aged 42 with greying short hair, black tuxedo"),
    char("claire", "Claire", "1girl", "adult, mature female, slender, blonde hair, long hair, updo, blue eyes",
         {"default": "shimmering silver sequin evening gown, diamond earrings, long gloves, high heels, elegant updo"},
         "a slender glamorous French woman aged 38 with blonde hair in an elegant updo"),
    char("sofia", "Sofia", "1girl", "adult, mature female, slender, long hair, dark brown hair, brown eyes, natural makeup",
         {"default": "simple black jumpsuit, camera strap, holding camera, flat shoes, hair in low ponytail",
          "travel": "beige trench coat, black jumpsuit, small leather bag, hair down"},
         "a slender Italian woman aged 34 with long dark brown hair in a low ponytail, natural look, a professional camera"),
], [
    loc("l_deck", "Jachta", "outdoors, yacht deck, night, party, string lights, monaco harbor, city lights, champagne"),
    loc("l_cabin", "Salon jachty", "indoors, yacht salon, night, desk, photographs on table, lamp"),
    loc("l_port", "Přístav", "outdoors, harbor, monaco, early morning, parked car, yachts, blue hour"),
]), "Ztracená láska."), [
    panel("establishing", "l_deck", [], "yacht party, lights, harbor at night", [N("Monte Carlo. Victor pořádá večírek.")]),
    panel("full body", "l_deck", ["claire"], "arriving, walking, gown shimmering, guests looking"),
    panel("medium", "l_deck", ["sofia"], "holding camera, photographing, from side, looking at someone in distance",
          [N("Sofia na palubě fotografuje.")]),
    panel("medium", "l_deck", ["victor", "claire"], "dancing, close, string lights",
          [("claire", "Díváš se na mě jako na ženu svého života."), ("victor", "Možná jsi.")]),
    panel("close-up", "l_deck", ["sofia"], "lowering camera, sad, looking away", gap="large"),
    panel("medium", "l_cabin", ["victor:day"], "reading documents, realization, frowning",
          [N("Později Victor zjistí, že Claire chce hlavně jeho peníze a postavení.")]),
    panel("close-up", "l_cabin", ["victor:day"], "holding photograph, reading back of photograph",
          [N("„Některé věci člověk pozná, až když je ztratí.“")], gap="large"),
    panel("wide", "l_port", ["victor:day", "sofia:travel"], "running toward car, woman by car door",
          [("victor", "Počkej."), ("sofia", "Proč?")]),
    panel("medium", "l_port", ["victor:day", "sofia:travel"], "facing each other, woman calm, man desperate",
          [("victor", "Protože jsem udělal chybu."), ("sofia", "A já nechci být tvoje druhá volba.")]),
    panel("wide", "l_port", ["victor:day"], "standing alone, car driving away, blue hour", [N("Odjede. Victor zůstane stát.")], gap="large"),
])

# 17. Bali — fantasy colour lines ----------------------------------------------------------------------
STORIES["rf_07_bali"] = story(ending(world("w_rf_07_bali", "Bali – Cyklista a žena z džungle",
    "Australan Ethan sjíždí na kole balijské hory a průvodkyně Sari ho učí zpomalit.", "fantasy_colorlines", [
    char("ethan", "Ethan", "1boy", "mature male, athletic, tan, light brown hair, short hair, blue eyes",
         {"default": "fitted cycling jersey, cycling shorts, bike helmet, sunglasses",
          "rain": "wet cycling jersey, wet hair, holding towel",
          "travel": "white linen shirt, buttoned shirt, khaki trousers, backpack"},
         "an athletic tanned Australian man aged 31 with light brown hair"),
    char("sari", "Sari", "1girl", "adult, slender, athletic, long hair, black hair, brown eyes, tan skin",
         {"default": "fitted olive cycling top, black cycling leggings, bike helmet, long braid",
          "rain": "wet olive top, black leggings, wet hair, braid",
          "waterfall": "flowing batik sarong dress, frangipani flower in hair, long hair down"},
         "a slender athletic Indonesian woman aged 29 with long black hair, a local guide"),
], [
    loc("l_road", "Horská cesta", "outdoors, mountain road, bali, rice terraces, jungle, bicycles, sunny"),
    loc("l_hut", "Chatka v džungli", "indoors, small wooden hut, jungle, storm outside, rain, dim light"),
    loc("l_falls", "Vodopád", "outdoors, waterfall, jungle, lush, mist, morning light"),
    loc("l_airport", "Rozloučení", "outdoors, road, scooter, evening, palm trees"),
]), "Šťastný konec."), [
    panel("establishing", "l_road", [], "rice terraces, mountain road, jungle", [N("Bali. Horská cesta dolů.")]),
    panel("wide", "l_road", ["ethan", "sari"], "riding bicycles downhill side by side, speed lines",
          [("sari", "Pomaleji!"), ("ethan", "Bojíš se?"), ("sari", "O tebe.")]),
    panel("close-up", "l_road", ["ethan"], "grinning, wind", gap="large"),
    panel("wide", "l_hut", [], "storm, lightning, rain on jungle, small hut", sfx=["BUM!"], gap="small"),
    panel("medium", "l_hut", ["ethan:rain", "sari:rain"], "woman handing towel, man taking off wet jacket, rain outside",
          [("sari", "Jsi pořád přesvědčený, že rychleji je lepší?"), ("ethan", "Ne.")]),
    panel("close-up", "l_hut", ["ethan:rain"], "looking at viewer, soft expression",
          [("ethan", "Teď chci, aby tenhle okamžik trval co nejdéle.")], gap="large"),
    panel("wide", "l_falls", ["ethan", "sari:waterfall"], "standing at waterfall, mist, rainbow"),
    panel("medium", "l_falls", ["ethan", "sari:waterfall"], "kiss, waterfall mist",
          [("ethan", "Tohle bylo za co?"), ("sari", "Za to, že jsi konečně zpomalil.")], gap="large"),
    panel("medium", "l_airport", ["ethan:travel", "sari:waterfall"], "holding hands, sad, evening",
          [("sari", "Vrátíš se?"), ("ethan", "Ano."), ("sari", "Slibuješ?"), ("ethan", "Slibuju.")], gap="large"),
    panel("wide", "l_road", ["ethan"], "riding bicycle on same road, smile", [N("O rok později jede Ethan stejnou cestou.")]),
    panel("wide", "l_falls", ["sari:waterfall"], "waiting at waterfall, smiling, turning around", [N("Sari čeká u vodopádu.")], gap="large"),
])

# 18. Budapešť — art nouveau ---------------------------------------------------------------------------
STORIES["rf_08_budapest"] = story(ending(world("w_rf_08_budapest", "Budapešť – Lázně a druhá šance",
    "Peter přijede do Budapešti sám a v lázních potká architektku Annu.", "art_nouveau_mucha", [
    char("peter", "Peter", "1boy", "mature male, tall, athletic, grey hair, short hair, blue eyes",
         {"default": "white bathrobe, white towel over shoulder",
          "city": "navy wool overcoat, grey turtleneck, dark trousers",
          "evening": "dark blazer, white shirt, buttoned shirt"},
         "a tall mature British manager aged 45 with greying hair, still athletic"),
    char("anna", "Anna", "1girl", "adult, mature female, curvy, long hair, wavy hair, brown hair, brown eyes",
         {"default": "white bathrobe, hair in bun",
          "city": "burgundy wool coat, cream silk scarf, leather gloves, ankle boots",
          "evening": "deep green velvet dress, pearl earrings, hair down"},
         "an elegant curvy Hungarian woman aged 39 with wavy brown hair, an architect"),
], [
    loc("l_baths", "Lázně", "indoors, art nouveau thermal bath, ornate columns, mosaic, steam, pool, glass ceiling"),
    loc("l_city", "Večerní Budapešť", "outdoors, budapest, chain bridge, danube, parliament lit up, evening, street lamps"),
    loc("l_balcony", "Balkon hotelu", "outdoors, hotel balcony, night, danube view, city lights"),
    loc("l_lobby", "Hotelová hala", "indoors, hotel lobby, art nouveau, morning, suitcase"),
]), "Šťastný konec."), [
    panel("establishing", "l_baths", [], "ornate thermal bath, steam, columns", [N("Budapešť. Lázně.")]),
    panel("medium", "l_baths", ["peter"], "sitting on bench by pool, alone, thoughtful"),
    panel("medium", "l_baths", ["peter", "anna"], "woman placing towel on bench next to him, man pointing at towel",
          [("peter", "Myslím, že tohle je moje."), ("anna", "Tak si ho vezměte.")]),
    panel("medium", "l_baths", ["peter", "anna"], "man smiling, woman smiling",
          [("peter", "A co když si raději nechám společnost?")], gap="large"),
    panel("wide", "l_city", ["peter:city", "anna:city"], "walking along danube, chain bridge, evening lights",
          [("anna", "Proč jste přijel sám?")]),
    panel("medium", "l_city", ["peter:city", "anna:city"], "stopping on bridge, looking at each other",
          [("peter", "Potřeboval jsem zjistit, jestli ještě dokážu něco cítit."), ("anna", "A?"), ("peter", "Ano.")], gap="large"),
    panel("medium", "l_balcony", ["peter:evening", "anna:evening"], "sitting on balcony, man taking her hand",
          [("peter", "Mohu tě políbit?"), ("anna", "Ano.")]),
    panel("medium", "l_balcony", ["peter:evening", "anna:evening"], "kiss, city lights", gap="small"),
    panel("medium", "l_balcony", ["peter:evening", "anna:evening"], "woman leaning head on his shoulder, night", gap="large"),
    panel("medium", "l_lobby", ["peter:city", "anna:city"], "woman handing small photograph, man with suitcase",
          [("anna", "Aby ses nezapomněl vrátit."), ("peter", "Vrátím.")]),
    panel("wide", "l_city", ["peter:city"], "walking toward bridge with flowers", [N("Tentokrát svůj slib dodrží.")], gap="large"),
])

# 19. Queenstown — anime screencap ---------------------------------------------------------------------
STORIES["rf_09_queenstown"] = story(ending(world("w_rf_09_queenstown", "Queenstown – Poslední sjezd",
    "Švédka Nora přijede na hory sama a instruktor Liam jí řekne, že lže, když tvrdí, že se nebojí.", "anime_screencap", [
    char("liam", "Liam", "1boy", "mature male, tall, muscular, dark hair, short hair, brown eyes",
         {"default": "red ski jacket, black ski pants, ski goggles on head",
          "cabin": "charcoal knit sweater, dark jeans",
          "home": "white t-shirt, open flannel overshirt over t-shirt, jeans"},
         "a tall muscular New Zealand ski instructor aged 36 with dark hair"),
    char("nora", "Nora", "1girl", "adult, tall female, athletic, blonde hair, long hair, blue eyes",
         {"default": "white ski jacket, white ski pants, knit beanie, ski goggles",
          "cabin": "red cable knit sweater, black leggings, hair down",
          "coat": "camel wool coat, grey scarf, ankle boots, small suitcase"},
         "a tall athletic Swedish woman aged 33 with long blonde hair"),
], [
    loc("l_slope", "Svah", "outdoors, ski slope, snow, mountains, queenstown, sunny, blue sky"),
    loc("l_cabin", "Chata", "indoors, ski lodge, fireplace, night, warm light, wooden walls"),
    loc("l_house", "Liamův dům", "outdoors, house doorway, porch, autumn, evening"),
]), "Šťastný konec."), [
    panel("establishing", "l_slope", [], "snowy mountains, ski slope, lake below", [N("Queenstown. Hory.")]),
    panel("medium", "l_slope", ["nora", "liam"], "standing at top of slope, man smirking",
          [("liam", "Nebojíš se?"), ("nora", "Ne."), ("liam", "Lžeš.")]),
    panel("close-up", "l_slope", ["nora"], "laughing, snow", gap="large"),
    panel("medium", "l_cabin", ["nora:cabin", "liam:cabin"], "sitting by fireplace, mugs, warm light",
          [("liam", "Proč jsi přijela sama?"), ("nora", "Protože jsem potřebovala začít znovu.")]),
    panel("medium", "l_cabin", ["nora:cabin", "liam:cabin"], "kiss, firelight",
          [("liam", "Tak začni.")], gap="large"),
    panel("medium", "l_cabin", ["nora:coat"], "holding phone, worried, shocked",
          [N("Poslední den zavolají z domova. Otec je nemocný.")]),
    panel("medium", "l_cabin", ["nora:coat", "liam:cabin"], "facing each other, man stepping forward",
          [("liam", "Pojedu s tebou."), ("nora", "Nemůžeš."), ("liam", "Proč?")]),
    panel("medium", "l_cabin", ["nora:coat", "liam:cabin"], "hug, sad",
          [("nora", "Protože jsme se znali jen týden.")], gap="large"),
    panel("medium", "l_house", ["liam:home"], "opening door, surprised", [N("O několik měsíců později.")], gap="small"),
    panel("medium", "l_house", ["nora:coat", "liam:home"], "woman standing on porch with suitcase, smiling",
          [("liam", "Říkal jsem si, jestli přijdeš."), ("nora", "Já taky.")]),
    panel("medium", "l_house", ["nora:coat", "liam:home"], "embrace, smiling, eyes closed", gap="large"),
])

# 20. Capri — oil painting -----------------------------------------------------------------------------
STORIES["rf_10_capri"] = story(ending(world("w_rf_10_capri", "Capri – Láska, která přišla příliš pozdě",
    "Elena přijede na Capri po letech práce a majitel restaurace Antonio jí přinese dezert, který si neobjednala.", "painterly_oil", [
    char("antonio", "Antonio", "1boy", "mature male, middle-aged, tall, slender, grey hair, short hair, brown eyes",
         {"default": "white linen shirt, buttoned shirt, black apron, dark trousers",
          "evening": "cream linen jacket, light blue shirt, buttoned shirt"},
         "a charismatic tall slender Italian man aged 50 with grey hair, owner of a small restaurant"),
    char("elena", "Elena", "1girl", "adult, mature female, slender, curly hair, black hair, long hair, brown eyes",
         {"default": "navy silk midi dress, gold earrings, leather sandals, curly hair down",
          "evening": "red silk wrap dress, gold bangles, curly hair pinned up",
          "travel": "white linen trouser suit, sunglasses, silk headscarf"},
         "an elegant Spanish woman aged 44 with long dark curly hair, gold earrings"),
], [
    loc("l_rest", "Restaurace", "outdoors, restaurant terrace, capri, lemon trees, sea view, evening, candles, white tablecloth"),
    loc("l_beach", "Pobřeží", "outdoors, rocky coast, capri, faraglioni, sunset, sea"),
    loc("l_street", "Ulička", "outdoors, narrow street, capri, morning, white houses, bougainvillea, taxi"),
]), "Hořkosladký konec."), [
    panel("establishing", "l_rest", [], "lemon trees, sea view, terrace", [N("Capri.")]),
    panel("medium", "l_rest", ["elena", "antonio"], "man leading woman to table, terrace",
          [("antonio", "Jste sama?"), ("elena", "Ano."), ("antonio", "Já také.")]),
    panel("close-up", "l_rest", ["elena"], "small smile", gap="large"),
    panel("medium", "l_rest", ["elena", "antonio"], "man placing dessert plate, woman surprised",
          [("elena", "To jsem si neobjednala."), ("antonio", "Já vím."), ("elena", "Tak proč?")]),
    panel("close-up", "l_rest", ["antonio"], "warm smile, looking at viewer",
          [("antonio", "Protože jste se dnes poprvé usmála.")], gap="large"),
    panel("wide", "l_beach", ["elena:evening", "antonio:evening"], "walking along coast, sunset, faraglioni",
          [("elena", "Kdybych tě potkala před dvaceti lety…"), ("antonio", "Byli bychom jiní lidé.")]),
    panel("medium", "l_beach", ["elena:evening", "antonio:evening"], "stopping, looking at each other, sunset",
          [("elena", "Možná bych tě milovala."), ("antonio", "Možná bych tě neuměl milovat správně.")], gap="large"),
    panel("medium", "l_rest", ["elena:evening", "antonio:evening"], "sitting on terrace, woman's head on his shoulder, candles, night"),
    panel("medium", "l_rest", ["elena:evening", "antonio:evening"], "kiss, candlelight",
          [N("Oba vědí, že ráno odjíždějí každý jinam.")]),
    panel("medium", "l_rest", ["elena:evening", "antonio:evening"], "sitting close, looking at sea, night",
          [("elena", "Proč některé krásné věci trvají tak krátce?"), ("antonio", "Abychom si je pamatovali.")], gap="large"),
    panel("wide", "l_street", ["antonio"], "standing in front of restaurant, watching taxi drive away, morning",
          [N("Ráno Elena odjíždí.")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
