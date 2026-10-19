"""Romance set K — "Módní kolekce sezóny" (5 ona hledá + 5 on hledá), fashion and flirt, SFW.

    python3 m0/romance_k.py        → data/stories/rk_*/{world,storyboard}.json

Same building blocks and rules as stories_romance.py: one medium per story, dialogue near-verbatim (typos fixed),
inner monologue as thought bubbles, never two characters of the same gender in one panel. The season's wardrobe
(over-knee boots with brass buckles, burgundy velvet pumps, gold-black silk slip dress, pearl earrings, cat-eye
glasses, beige trench, tailored trousers, wool coat, denim shirt) is spread over the outfits, no brand names.
Intimacy stops at a kiss and an embrace; the door, lamp or curtain closes the scene.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}


def ending(w, text):
    w["canon"]["constraints"] = [text]
    return w


# 1. Capri — photoreal ---------------------------------------------------------------------------
STORIES["rk_01_capri"] = story(ending(world("w_rk_01_capri", "Capri – Zlato a sůl",
    "Valentina slaví rozvod na Capri a vítr jí zanese šátek do koktejlu architekta Mathiase.", "photo_juggernaut", [
    char("valentina", "Valentina", "1girl", "adult, mature female, dark hair, long hair, wavy hair, green eyes, tan skin",
         {"default": "gold and black silk slip dress, thin straps, silk scarf, gold sandals, gold hoop earrings",
          "sea": "gold and black silk slip dress, barefoot, wind-blown hair, gold bracelet",
          "wedding": "ivory silk slip wedding dress, pearl earrings, flower in hair"},
         "an elegant Italian woman aged 30, long dark wavy hair, green eyes"),
    char("mathias", "Mathias", "1boy", "mature male, tall, slender, short hair, brown hair, stubble, brown eyes",
         {"default": "white linen shirt, rolled sleeves, beige linen trousers, leather loafers, wristwatch",
          "wedding": "light grey linen suit, white shirt, no necktie"},
         "a tall French man aged 35, short brown hair, light stubble"),
], [
    loc("l_marina", "Marina Grande", "outdoors, harbor, capri, yachts, lemon trees, pastel houses, cliffs, sunset, golden light"),
    loc("l_boat", "Faraglioni", "outdoors, small wooden boat, sea, faraglioni rocks, sunset, calm water, mediterranean"),
    loc("l_villa", "Bílá vila", "indoors, white villa, open balcony doors, sea view, night, moonlight, sheer curtains, lamp"),
]), "Dobrý konec – o rok později svatba na stejné lodi."), [
    panel("establishing", "l_marina", [], "yachts, harbor, lemon trees, cliffs, sunset", [N("Capri. Jachty cinkají, citronovníky voní.")]),
    panel("medium", "l_marina", ["valentina"], "walking along harbor, holding scarf, confident smile, wind",
          [("valentina", "Rozvod oslavím tím nejlepším jídlem života.", "thought")]),
    panel("close-up", "l_marina", ["valentina"], "silk scarf flying in wind, surprised, hand reaching", sfx=["FÍÍ!"], gap="small"),
    panel("medium", "l_marina", ["mathias"], "sitting at cafe table, cocktail glass with silk scarf inside, amused, raised eyebrow",
          [("mathias", "Buď je tohle nejlepší seznamka v Evropě, nebo se větru zalíbil můj drink.")]),
    panel("medium", "l_marina", ["valentina", "mathias"], "woman laughing, man handing back scarf, cafe table, sunset",
          [("valentina", "Větru. Ale vám nechám spropitné za inscenaci.")]),
    panel("wide", "l_boat", ["valentina:sea", "mathias"], "sitting on stern of boat, feet in water, sunset, faraglioni rocks",
          [N("Plavba kolem Faraglioni.")]),
    panel("close-up", "l_boat", ["valentina:sea"], "bare foot touching sea water, gold anklet, ripples", gap="small"),
    panel("medium", "l_boat", ["valentina:sea", "mathias"], "kiss, sunset backlight, eyes closed, wind in hair",
          [N("Polibek při západu slunce. Slaný, pomalý.")]),
    panel("medium", "l_villa", ["valentina", "mathias"], "standing in doorway, man embracing woman from behind, chin on her shoulder, moonlight",
          [("valentina", "Dnes žádné spěchání. Dnes si tě vychutnám jako večeři.")]),
    panel("wide", "l_villa", [], "closed door, lamp turned off, sheer curtains moving, moonlight on sea, no humans",
          [N("Dveře se zavřou. Lampa zhasne. Moře doplétá příběh dál.")], gap="large"),
    panel("wide", "l_boat", ["valentina:wedding", "mathias:wedding"], "wedding on boat, holding hands, flowers, smiling, sunset, yachts",
          [N("O rok později se na stejné lodi berou."), ("mathias", "Jachty pořád cinkají.")]),
])

# 2. Kyoto — ukiyo-e ----------------------------------------------------------------------------
STORIES["rk_02_kyoto"] = story(ending(world("w_rk_02_kyoto", "Kjóto – Deštivé duby",
    "Fotografka Hana potká v dešti v bambusovém lese spisovatele Ethana, který jí ráno nechá jen lísteček.", "ukiyoe", [
    char("hana", "Hana", "1girl", "adult, mature female, black hair, short hair, bob cut, black eyes, glasses",
         {"default": "beige trench coat, black turtleneck, camera strap, holding camera, glasses",
          "robe": "silk kimono-style robe, deep blue, obi belt, glasses",
          "dawn": "beige trench coat, silk scarf, holding camera, glasses"},
         "a Japanese-Canadian woman aged 28, black bob haircut, round glasses, beige trench coat, camera"),
    char("ethan", "Ethan", "1boy", "mature male, tall, short hair, brown hair, beard, blue eyes",
         {"default": "dark wool coat, grey scarf, holding umbrella, notebook",
          "evening": "white shirt, dark trousers, rolled sleeves"},
         "a tall American man aged 40, short brown hair, trimmed beard, dark wool coat"),
], [
    loc("l_bamboo", "Arashiyama", "outdoors, bamboo forest, arashiyama, rain, path, mist, tall bamboo"),
    loc("l_ryokan", "Ryokan", "indoors, ryokan, tatami, paper lantern, shoji, low table, sake, evening"),
    loc("l_room", "Pokoj ráno", "indoors, tatami room, morning light, shoji, folded futon, empty room"),
    loc("l_river", "Řeka za úsvitu", "outdoors, kamo river, dawn, mist, wooden bridge, kyoto, sunrise"),
]), "Špatný konec – Ethan odejde bez rozloučení, Hana jde dál silnější."), [
    panel("establishing", "l_bamboo", [], "bamboo forest, rain, mist, empty path", [N("Arašijama. Bambusový les v dešti.")]),
    panel("medium", "l_bamboo", ["hana"], "taking photo, wet hair, raindrops, foggy glasses, focused"),
    panel("medium", "l_bamboo", ["hana", "ethan"], "man holding umbrella over woman, rain, looking at each other",
          [("ethan", "Vypadáš jako báseň, kterou jsem zapomněl napsat.")]),
    panel("close-up", "l_bamboo", ["hana"], "wiping glasses, wry smile, rain",
          [("hana", "Spisovatelé milují ženy, dokud je nemusejí číst do konce.")]),
    panel("wide", "l_ryokan", ["hana:robe", "ethan:evening"], "sitting at low table, sake cups, laughing, paper lantern",
          [N("Ryokan. Víno, smích.")]),
    panel("medium", "l_ryokan", ["hana:robe", "ethan:evening"], "kiss, lantern light, eyes closed", gap="small"),
    panel("wide", "l_ryokan", [], "paper lantern blown out, shoji closed, rain on window, no humans",
          [N("Lucerna zhasne.")], gap="large"),
    panel("medium", "l_room", ["hana:robe"], "sitting alone, holding small paper note, morning light, empty room, sad",
          [N("Ráno je Ethan pryč. Na polštáři lísteček:"), N("„Příběh je silnější bez šťastného konce. Odpusť.“")]),
    panel("close-up", "l_room", ["hana:robe"], "looking at empty room, tears held back, determined",
          [("hana", "Nenapsal jsi příběh, Ethane. Ukradl jsi mi jen kapitolu.")]),
    panel("medium", "l_room", ["hana:dawn"], "tying scarf, picking up camera, standing up"),
    panel("wide", "l_river", ["hana:dawn"], "walking on bridge, taking photo of sunrise, mist, alone, calm",
          [N("Jde fotit východ slunce. Zamyšlená. Silnější.")], gap="large"),
])

# 3. Santorini — clean webtoon (artist tags) ----------------------------------------------------
STORIES["rk_03_santorini"] = story(ending(world("w_rk_03_santorini", "Santorini – Bílé stěny, modrá krev",
    "Chloé píchne kolo nad kalderou a zachrání ji vinař Nikos, který věří na osud.", "clean_webtoon", [
    char("chloe", "Chloé", "1girl", "adult, mature female, red hair, long hair, freckles, blue eyes, fair skin",
         {"default": "white sundress, silk headscarf, cat-eye sunglasses, flat sandals",
          "evening": "white flowing evening dress, gold earrings, hair down"},
         "a French woman aged 26, long red hair, freckles, white sundress, silk headscarf"),
    char("nikos", "Nikos", "1boy", "mature male, tan skin, full beard, black hair, short hair, brown eyes, muscular",
         {"default": "white linen shirt, khaki trousers, rolled sleeves",
          "evening": "navy linen shirt, dark trousers, leather belt"},
         "a Greek man aged 32, tanned, full black beard, white linen shirt"),
], [
    loc("l_road", "Cesta nad kalderou", "outdoors, caldera road, santorini, bicycle, white houses, blue sea, cliffs, sunny"),
    loc("l_winery", "Vinárna ve skále", "indoors, cave winery, wine barrels, wine glasses, warm lanterns, stone walls"),
    loc("l_dome", "Modrá kopule", "outdoors, rooftop, blue dome church, santorini, night, city lights below, stars"),
]), "Dobrý konec – Chloé zůstane na Santorini."), [
    panel("establishing", "l_road", [], "caldera, white houses, blue domes, sea", [N("Santorini. Silnice po hraně kaldery.")]),
    panel("wide", "l_road", ["chloe"], "standing next to bicycle with flat tire, hands on hips, annoyed", sfx=["PSSS!"]),
    panel("medium", "l_road", ["chloe"], "looking around, empty road, sigh",
          [("chloe", "Uprostřed ničeho. Skvělé.", "thought")]),
    panel("medium", "l_road", ["nikos"], "leaning out of old van window, grinning",
          [("nikos", "Turistko, tady nejezdí autobusy. Jen osud. A ten dnes vypadá jako já.")]),
    panel("wide", "l_road", ["chloe", "nikos"], "loading bicycle into van, laughing, sunny"),
    panel("wide", "l_winery", ["chloe:evening", "nikos:evening"], "wine tasting, holding wine glasses, barrels, lanterns",
          [N("Degustace. Z dálky buzuki.")]),
    panel("wide", "l_winery", ["chloe:evening", "nikos:evening"], "dancing between barrels, man spinning woman, dress swirling, laughing",
          sfx=["♪"]),
    panel("medium", "l_dome", ["chloe:evening"], "slowly removing headscarf, hair in wind, city lights, looking back"),
    panel("medium", "l_dome", ["nikos:evening"], "hands in pockets, respectful, soft gaze",
          [("nikos", "Můžu?")]),
    panel("close-up", "l_dome", ["chloe:evening"], "playful smile, night",
          [("chloe", "Můžeš. Ale zítra mě svezeš na kole dolů. Na zadním sedadle.")]),
    panel("wide", "l_dome", ["chloe:evening", "nikos:evening"], "kiss under blue dome, stars, silhouette",
          gap="small"),
    panel("wide", "l_dome", [], "starry sky over santorini, no humans", [N("Zůstala. Vinárna má teď francouzský název a řecké srdce.")], gap="large"),
])

# 4. St. Barthélemy — fashion editorial ---------------------------------------------------------
STORIES["rk_04_stbarth"] = story(ending(world("w_rk_04_stbarth", "St. Barthélemy – Jachta Nedočkavost",
    "Bývalá modelka Isabelle si na jachtě jachtaře Viktora dokazuje, že ještě umí chtít, a odejde s hlavou vzhůru.", "fashion_editorial", [
    char("isabelle", "Isabelle", "1girl", "adult, mature female, tan skin, long hair, black hair, wavy hair, brown eyes, tall",
         {"default": "emerald green silk wrap dress, gold cuff bracelets, gold hoop earrings, wide-brim hat",
          "night": "emerald green silk wrap dress, gold cuff bracelets, hair down",
          "morning": "emerald green silk wrap dress, wrinkled, gold cuff bracelets, sunglasses on head"},
         "a tall Brazilian former model aged 33, long black wavy hair"),
    char("viktor", "Viktor", "1boy", "mature male, tall, broad shoulders, short hair, grey hair, blue eyes, clean-shaven",
         {"default": "white linen shirt, navy blazer, white trousers, luxury wristwatch",
          "morning": "white polo shirt, white trousers, luxury wristwatch, sunglasses"},
         "a tall Russian yachtsman aged 45, short grey hair"),
], [
    loc("l_deck", "Paluba", "outdoors, luxury yacht deck, champagne glasses, caribbean sea, golden hour, sunset"),
    loc("l_salon", "Podpalubí", "indoors, yacht salon, leather sofa, soft lamps, night, porthole"),
    loc("l_break", "Snídaně u jiného ostrova", "outdoors, yacht deck, breakfast table, croissants, morning light, island"),
    loc("l_pier", "Gustavia", "outdoors, pier, gustavia, harbor, red roofs, morning, boats"),
]), "Špatný konec – Viktor má ženu, Isabelle odchází sama a hrdě."), [
    panel("establishing", "l_deck", [], "yacht, champagne, golden hour, sea", [N("St. Barth. Šampaňské, koktejly, ego.")]),
    panel("medium", "l_deck", ["isabelle"], "holding champagne glass, leaning on railing, wind in dress, confident",
          [("isabelle", "Po rozchodu si musím dokázat, že ještě umím chtít.", "thought")]),
    panel("medium", "l_deck", ["viktor"], "arms spread, showing off, smug smile, sunset",
          [("viktor", "Všechno, co vidíš, je moje. Včetně západu slunce – koupil jsem si ho tím směrem.")]),
    panel("close-up", "l_deck", ["isabelle"], "raised eyebrow, sipping champagne",
          [("isabelle", "Západ slunce si nekoupíš. Jen si můžeš pronajmout stín.")]),
    panel("medium", "l_salon", ["isabelle:night", "viktor"], "passionate kiss, lamp light, night", [N("Noc. Rychlá jako bouřka.")]),
    panel("wide", "l_salon", [], "lamp turned off, porthole moonlight, dark salon, no humans", gap="large"),
    panel("wide", "l_break", ["isabelle:morning", "viktor:morning"], "breakfast table, man reading phone, woman holding coffee",
          [N("Ráno jachta kotví u jiného ostrova.")]),
    panel("medium", "l_break", ["viktor:morning"], "not looking up, buttering croissant, casual",
          [("viktor", "Vysadím tě v Gustavii. Letí mi žena.")]),
    panel("close-up", "l_break", ["isabelle:morning"], "calmly removing gold earring, placing it on table, cold stare"),
    panel("medium", "l_break", ["isabelle:morning"], "standing up, composed",
          [("isabelle", "Loď si zaplatím sama. Ty si zaplatíš rozvod. Západ slunce ti nechám.")]),
    panel("wide", "l_pier", ["isabelle:morning"], "walking on pier, head held high, sunglasses, wind, from behind",
          [N("Vystoupí na molo – a jde s hlavou vzhůru.")], gap="large"),
])

# 5. Banff — clean webtoon, no artist tags ------------------------------------------------------
STORIES["rk_05_banff"] = story(ending(world("w_rk_05_banff", "Banff – Ledová řeka, horké koleno",
    "Norka Freya spadne z kola do ledového potoka a skotský průvodce Callum ji vytáhne i s humorem.", "clean_webtoon_noartist", [
    char("freya", "Freya", "1girl", "adult, mature female, blonde hair, long hair, braid, blue eyes, athletic",
         {"default": "cream cable knit sweater, black leggings, tall leather boots, cycling helmet",
          "wet": "wet cable knit sweater, wet hair, oversized brown leather jacket, shivering",
          "cabin": "oversized flannel shirt, thick wool socks, hair loose, blanket"},
         "a tall athletic Norwegian woman aged 29, long blonde braid, cream cable-knit sweater"),
    char("callum", "Callum", "1boy", "mature male, tall, beard, red hair, short hair, green eyes, broad shoulders",
         {"default": "brown leather jacket, plaid flannel shirt, hiking boots",
          "cabin": "plaid flannel shirt, rolled sleeves, jeans"},
         "a tall Scottish mountain guide aged 31, ginger beard, brown leather jacket"),
], [
    loc("l_trail", "Lesní stezka", "outdoors, forest trail, banff, pine trees, mountain stream, rocks, autumn, daytime"),
    loc("l_cabin", "Srub", "indoors, log cabin, fireplace, fire, wooden walls, warm light, tea mugs, evening"),
    loc("l_terrace", "Terasa", "outdoors, cabin terrace, mountains, pink sunrise, eagle in sky, mist, morning"),
]), "Dobrý konec – Freya zůstává."), [
    panel("establishing", "l_trail", [], "forest trail, mountains, stream", [N("Banff. Lesní stezka.")]),
    panel("wide", "l_trail", ["freya"], "falling off bicycle into stream, splash, surprised", sfx=["ŠPLOUCH!"], gap="small"),
    panel("medium", "l_trail", ["freya:wet", "callum"], "man pulling woman out of water by hand, rocks, wet",
          [("callum", "V Norsku vás učí plavat v ledovci?")]),
    panel("close-up", "l_trail", ["freya:wet"], "teeth chattering, wearing his leather jacket, defiant smile",
          [("freya", "Ne. Učí nás vypadat dobře při umírání.")]),
    panel("wide", "l_cabin", [], "socks thrown across room, wet sweater drying by fire, door ajar, no humans",
          [N("Mokré vrstvy za dveřmi. Smích. Létající ponožky.")], sfx=["HA HA!"]),
    panel("medium", "l_cabin", ["freya:cabin", "callum:cabin"], "sitting by fireplace, holding tea mugs, wrapped in blanket, comfortable silence",
          [N("Dlouhé ticho, které není trapné.")]),
    panel("medium", "l_cabin", ["freya:cabin", "callum:cabin"], "forehead touch, firelight, eyes closed", gap="small"),
    panel("wide", "l_cabin", [], "fire glowing embers, dark cabin, night, no humans", gap="large"),
    panel("medium", "l_terrace", ["callum:cabin"], "holding two coffee mugs, pink mountains behind",
          [("callum", "Zůstaň ještě den.")]),
    panel("medium", "l_terrace", ["freya:cabin"], "wrapped in blanket, teasing look", [("freya", "A pak?")]),
    panel("medium", "l_terrace", ["callum:cabin"], "grin, eagle in sky",
          [("callum", "Pak tě naučím, že Skotsko je hezčí než Norsko. Bude to trvat. Roky.")]),
    panel("wide", "l_terrace", ["freya:cabin", "callum:cabin"], "hug at sunrise, hair blowing loose, mountains",
          [("freya", "Dobře. Začni dnes.")], gap="large"),
])

# 6. Rio — webtoon -----------------------------------------------------------------------------
STORIES["rk_06_rio"] = story(ending(world("w_rk_06_rio", "Rio – Karneval mimo sezónu",
    "Tanečník samby Rafael rozbije švédské architektce Ingrid tužku i plán na kontrolovaný život.", "webtoon_romance", [
    char("rafael", "Rafael", "1boy", "mature male, dark-skinned male, curly hair, black hair, brown eyes, athletic, smile",
         {"default": "white linen shirt, buttoned, light trousers, barefoot",
          "night": "dark silk shirt, buttoned, black trousers, gold chain"},
         "a Brazilian samba dancer aged 34, curly black hair, warm smile, white linen shirt"),
    char("ingrid", "Ingrid", "1girl", "adult, mature female, blonde hair, short hair, blue eyes, slim, cat-eye glasses",
         {"default": "tailored beige trousers, white shirt, white sneakers, cat-eye glasses, sketchbook",
          "dance": "red wrap dress, gold earrings, hair tucked behind ear",
          "night": "black silk slip dress, pearl earrings"},
         "a Swedish architect aged 30, short blonde hair, cat-eye glasses, tailored beige trousers"),
], [
    loc("l_beach", "Copacabana", "outdoors, copacabana beach, wave pattern promenade, sand, palm trees, november, daytime"),
    loc("l_school", "Škola samby", "indoors, dance studio, samba school, colorful decorations, mirrors, evening"),
    loc("l_balcony", "Balkon nad pláží", "outdoors, balcony, night, city lights, ocean, curtains blowing"),
]), "Dobrý konec – Ingrid zůstane a kreslí křivky, které nikam nemusí vést."), [
    panel("establishing", "l_beach", [], "copacabana promenade wave pattern, beach", [N("Copacabana. Listopad.")]),
    panel("medium", "l_beach", ["ingrid"], "sitting on bench, drawing wave pattern in sketchbook, concentrated"),
    panel("wide", "l_beach", ["rafael"], "dancing samba on sand, dynamic pose, joyful", sfx=["♪ ♪"]),
    panel("close-up", "l_beach", ["ingrid"], "broken pencil, annoyed, glasses slipping", sfx=["KŘUP!"], gap="small"),
    panel("medium", "l_beach", ["ingrid", "rafael"], "woman frowning, man grinning, dancing around her",
          [("ingrid", "Vůbec nevím, jestli jsi otravný, nebo geniální."), ("rafael", "V Brazílii je to totéž slovo.")]),
    panel("wide", "l_school", ["ingrid:dance"], "learning samba step, stumbling, determined, mirrors",
          [N("Dvaadvacet pokusů.")]),
    panel("wide", "l_school", ["ingrid:dance", "rafael"], "woman dancing samba gracefully, man watching in awe",
          [N("Dvacátý třetí – tančí.")]),
    panel("medium", "l_school", ["rafael"], "soft smile, leaning on mirror",
          [("rafael", "Víš, co je špatné na architektech? Že staví. Měli by tančit. Tebe jsem nikdy neviděl tak živou.")]),
    panel("medium", "l_balcony", ["ingrid:night", "rafael:night"], "standing close on balcony, music, city lights",
          [("ingrid", "Já nerada ztrácím kontrolu."), ("rafael", "Pak ti ji vrátím ráno. S úrokem.")]),
    panel("medium", "l_balcony", ["ingrid:night", "rafael:night"], "kiss, night breeze", gap="small"),
    panel("wide", "l_balcony", [], "balcony curtain blowing toward viewer, night, no humans", gap="large"),
    panel("medium", "l_beach", ["ingrid"], "drawing new curvy promenade line in sketchbook, smiling, morning",
          [N("Ráno kreslí nový chodník – s křivkou, která nikam nemusí vést.")], gap="large"),
])

# 7. Marrakesh — ink wash ----------------------------------------------------------------------
STORIES["rk_07_marrakes"] = story(ending(world("w_rk_07_marrakes", "Marrákeš – Zahrada, která spí",
    "Blogerka Celeste se ztratí v medíně a obchodník s látkami Omar jí ukáže zahradu, kterou si nesmí nechat.", "ink_wash", [
    char("omar", "Omar", "1boy", "mature male, short hair, black hair, grey eyes, stubble, tall, calm",
         {"default": "linen djellaba, cream color, leather sandals",
          "night": "dark blue linen shirt, cream trousers"},
         "a tall Moroccan cloth merchant aged 38, grey eyes, short black hair, cream linen djellaba"),
    char("celeste", "Celeste", "1girl", "adult, mature female, brown hair, long hair, wavy hair, hazel eyes",
         {"default": "wide-brim straw hat, flowing white maxi dress, gold bangles, holding phone",
          "night": "terracotta silk dress, silk scarf over shoulders, gold earrings",
          "airport": "beige trench coat, wide-brim hat, sunglasses, suitcase"},
         "a French lifestyle blogger aged 27, long wavy brown hair, wide-brim hat, white maxi dress"),
], [
    loc("l_medina", "Medína", "outdoors, medina, marrakesh, narrow alley, spice stalls, lanterns, fabric hanging, sunlight"),
    loc("l_riad", "Riad", "indoors, riad courtyard, fountain, orange trees, mosaic tiles, arches"),
    loc("l_roof", "Střecha riadu", "outdoors, rooftop terrace, night, stars, mint tea, lanterns, marrakesh skyline"),
    loc("l_airport", "Letiště", "indoors, airport terminal, departure board, large windows, morning"),
]), "Špatný konec – Omarovi zemře otec, musí vést rodinu a nepřijde."), [
    panel("establishing", "l_medina", [], "medina alley, fabrics, lanterns", [N("Medína. Ráj a bludiště.")]),
    panel("medium", "l_medina", ["celeste"], "lost, looking at phone, confused, crowd blur",
          [("celeste", "Mapa tady nefunguje.", "thought")]),
    panel("medium", "l_medina", ["omar"], "gesturing the way, polite distance, fabric stall"),
    panel("wide", "l_riad", ["celeste", "omar"], "walking into courtyard, fountain, orange trees, woman amazed"),
    panel("medium", "l_riad", ["celeste"], "removing hat, looking at him, serious",
          [("celeste", "Na blogu mám sto tisíc lidí, kteří mě vidí každý den. Ty se na mě díváš, jako bych byla jediná v místnosti. To je nebezpečné.")]),
    panel("close-up", "l_riad", ["omar"], "calm grey eyes, quiet",
          [("omar", "Ne. Nebezpečné je být viděn stokrát a pochopen nikdy.")]),
    panel("wide", "l_roof", ["celeste:night", "omar:night"], "sitting on rooftop, mint tea, stars, lanterns",
          [N("Pomalé večery. Čaj.")]),
    panel("medium", "l_roof", ["celeste:night", "omar:night"], "man kissing woman's hand, gentle, lantern light",
          [N("Políbil jí ruku – dávno předtím, než políbil její rty.")]),
    panel("wide", "l_airport", ["celeste:airport"], "standing alone with suitcase, looking around, departure board"),
    panel("close-up", "l_airport", ["celeste:airport"], "reading phone message, shocked, sad",
          [N("SMS od Omara: „Můj otec umřel. Musím vést rodinu. Nemohu tě vzít do života, který jsem nezvolil. Odpusť, že jsem ti ukázal zahradu.“")]),
    panel("wide", "l_airport", ["celeste:airport"], "looking out window at plane, phone lowered, quiet",
          [N("Ve stories nezveřejní nic. Některé zahrady nepatří na internet.")], gap="large"),
])

# 8. Bora Bora — glossy photo ------------------------------------------------------------------
STORIES["rk_08_borabora"] = story(ending(world("w_rk_08_borabora", "Bora Bora – Voda nad zlatem",
    "Vyčerpaná dermatoložka Margaux najde v laguně průvodce Tevu i klid, o kterém nevěřila, že si ho zaslouží.", "photo_glossy", [
    char("teva", "Teva", "1boy", "mature male, tan skin, long hair, black hair, tied hair, brown eyes, muscular, tribal tattoo on arm",
         {"default": "white linen shirt, open collar, rolled sleeves, linen shorts, shell necklace",
          "night": "white linen shirt, flower behind ear, shell necklace"},
         "a Polynesian lagoon guide aged 36, long black hair tied back, traditional tattoo on his forearm"),
    char("margaux", "Margaux", "1girl", "adult, mature female, brown hair, shoulder-length hair, brown eyes, fair skin, tired eyes",
         {"default": "white linen dress, wide-brim hat, gold bracelet",
          "night": "white silk maxi dress, pearl earrings, hat in hand",
          "morning": "linen shirt dress, glasses, laptop"},
         "a Belgian dermatologist aged 32, shoulder-length brown hair"),
], [
    loc("l_bungalow", "Bungalov nad vodou", "outdoors, overwater bungalow, turquoise lagoon, wooden deck, mount otemanu, sunny"),
    loc("l_kayak", "Laguna za soumraku", "outdoors, kayak, lagoon, dusk, bioluminescence, glowing blue water, stars"),
    loc("l_terrace", "Terasa nad lagunou", "outdoors, terrace, night, moon reflection on lagoon, lanterns"),
]), "Dobrý konec – Margaux dá výpověď a zůstane na Bora Bora."), [
    panel("establishing", "l_bungalow", [], "overwater bungalows, turquoise lagoon", [N("Bora Bora.")]),
    panel("medium", "l_bungalow", ["margaux"], "sitting on deck edge, hat, tired, looking at water",
          [("margaux", "Přijela jsem zaplatit dluh sama sobě.", "thought")]),
    panel("medium", "l_bungalow", ["teva"], "pointing at sharks in clear water, smiling, standing on deck"),
    panel("medium", "l_bungalow", ["margaux", "teva"], "woman laughing for the first time, man smiling",
          [("margaux", "Zachraňuji kůži lidí. Na vlastní jsem zapomněla."), ("teva", "Tady nikdo nespěchá. Voda si vzpomene na všechno za tebe.")]),
    panel("wide", "l_kayak", ["margaux", "teva"], "sitting in kayak, dusk, glowing water", [N("Kajak za soumraku. Hvězdy v moři.")]),
    panel("medium", "l_kayak", ["margaux", "teva"], "hands in glowing blue water, palms on palms, bioluminescence",
          [("teva", "U nás se říká: kdo se dotkne světla moře společně, nesmí lhát.")]),
    panel("medium", "l_kayak", ["margaux"], "honest, tears in eyes, blue glow on face",
          [("margaux", "Pak řeknu pravdu. Přestala jsem věřit, že si zasloužím klid.")]),
    panel("medium", "l_kayak", ["teva"], "calm, gentle", [("teva", "Klid není odměna. Je to moře. Přijde, když přestaneš bojovat proti proudu.")]),
    panel("medium", "l_terrace", ["margaux:night", "teva:night"], "woman slowly taking off hat, eye contact, moonlight"),
    panel("medium", "l_terrace", ["margaux:night", "teva:night"], "kiss, moonlight", gap="small"),
    panel("wide", "l_terrace", [], "moon reflection on lagoon, lanterns, no humans", gap="large"),
    panel("medium", "l_bungalow", ["margaux:morning"], "typing on laptop, smiling, sunny morning",
          [N("Ráno píše výpověď do nemocnice v Bruselu. Adresa pro odpověď: Bora Bora.")], gap="large"),
])

# 9. Edinburgh — ligne claire ------------------------------------------------------------------
STORIES["rk_09_edinburgh"] = story(ending(world("w_rk_09_edinburgh", "Edinburgh – Město, které pamatuje",
    "Spisovatelka detektivek June hledá atmosféru vraždy a najde majitele antikvariátu Alistaira, který se bojí odejít.", "ligne_claire", [
    char("alistair", "Alistair", "1boy", "mature male, short hair, brown hair, grey hair, blue eyes, stubble, walking cane",
         {"default": "tweed jacket, wool waistcoat, white shirt, corduroy trousers, walking cane",
          "coat": "long dark wool coat, tartan scarf, walking cane"},
         "a Scottish antiquarian bookseller aged 40, greying brown hair, tweed jacket, walking cane"),
    char("june", "June", "1girl", "adult, mature female, black hair, long hair, straight hair, brown eyes, red lipstick",
         {"default": "camel wool coat, black turtleneck, red over-knee boots with brass buckles, leather bag",
          "evening": "black turtleneck dress, red over-knee boots, gold earrings"},
         "an American crime novelist aged 34, long black hair, camel wool coat, red over-knee boots"),
], [
    loc("l_shop", "Antikvariát", "indoors, antique bookshop, shelves of old books, wooden counter, lamp, royal mile, rain on window"),
    loc("l_kirk", "Greyfriars", "outdoors, greyfriars kirkyard, old gravestones, rain, edinburgh, overcast"),
    loc("l_pub", "Pub", "indoors, old pub, whisky glasses, fireplace, wooden booth"),
    loc("l_airport", "Letiště", "indoors, airport, departure gate, large windows, plane, grey sky"),
]), "Špatný konec – Alistair zůstane, June odletí."), [
    panel("establishing", "l_shop", [], "royal mile, rain, bookshop window", [N("Royal Mile. Antikvariát.")]),
    panel("medium", "l_shop", ["june"], "browsing old books, curious, red boots",
          [("june", "Hledám atmosféru vraždy.")]),
    panel("medium", "l_shop", ["alistair"], "handing old book across counter, dry smile",
          [N("Kniha z roku 1890. Věnování od zamilovaného lupiče.")]),
    panel("medium", "l_shop", ["june", "alistair"], "leaning on counter, flirting",
          [("june", "Píšu o lidech, kteří se namlouvají přes zločin. Vy jste ten typ, co loupí srdce?"),
           ("alistair", "Já jsem typ, co prodává cizí dopisy a nikdy nenapsal vlastní.")]),
    panel("wide", "l_kirk", ["june", "alistair:coat"], "walking among gravestones, sharing umbrella, rain", [N("Týden spolu.")]),
    panel("medium", "l_kirk", ["june", "alistair:coat"], "his hand holding hers inside her coat pocket", gap="small"),
    panel("medium", "l_pub", ["june:evening", "alistair"], "reading manuscript aloud, whisky, man correcting, laughing",
          [("alistair", "Skotsko takhle nefunguje. Ne jako v amerických knihách.")]),
    panel("medium", "l_airport", ["june", "alistair:coat"], "standing at gate, facing each other",
          [("june", "Zůstaň se mnou o týden déle."), ("alistair", "Nemůžu. Mám obchod. Mám… zvyky. Jsem město, June. A ty jsi román. Romány končí.")]),
    panel("close-up", "l_airport", ["june"], "sharp look, tears held back",
          [("june", "Detektivky končí odhalením. Ty ses právě odhalil: bojíš se, že když půjdeš za mnou, přestaneš být obětí vlastního příběhu.")]),
    panel("wide", "l_airport", [], "plane taking off, grey sky, window, no humans", gap="small"),
    panel("medium", "l_shop", ["alistair"], "alone behind counter, holding book, reading dedication, rain",
          [N("Věnování od ní: „Lupičům, kteří nekradou.“ Nekradl. A to byla ta největší krádež.")], gap="large"),
])

# 10. Tuscany — analog film --------------------------------------------------------------------
STORIES["rk_10_toskansko"] = story(ending(world("w_rk_10_toskansko", "Toskánsko – Úroda",
    "Realitní makléřka Petra přijede prodat usedlost vinaře Lorenza a zůstane déle, než by měla.", "photo_realvis_film", [
    char("lorenzo", "Lorenzo", "1boy", "mature male, short hair, grey hair, salt and pepper beard, brown eyes, tan skin, strong hands",
         {"default": "denim shirt, rolled sleeves, work trousers, leather boots",
          "evening": "white linen shirt, dark waistcoat, dark trousers"},
         "an Italian widower winemaker aged 42, salt-and-pepper beard, sun-worn face"),
    char("petra", "Petra", "1girl", "adult, mature female, brown hair, long hair, blue eyes",
         {"default": "tailored pencil skirt, cream silk blouse, burgundy velvet pumps, leather folder",
          "harvest": "denim shirt, rolled sleeves, jeans, rubber boots, hair in ponytail, grape stains",
          "night": "ivory silk shirt, high-waisted trousers, hair down, pearl earrings"},
         "a Czech real-estate agent aged 37, long brown hair, blue eyes"),
], [
    loc("l_vineyard", "Vinice v Chianti", "outdoors, vineyard, chianti, rows of grapevines, cypress trees, stone farmhouse, october, golden light"),
    loc("l_yard", "Dvůr pod fíkovníkem", "outdoors, farmhouse courtyard, fig tree, string lights, wine crates, evening"),
    loc("l_cellar", "Sklep se sudy", "indoors, wine cellar, oak barrels, lantern, stone vault, night"),
]), "Dobrý konec – usedlost stažena z prodeje."), [
    panel("establishing", "l_vineyard", [], "vineyard, cypress trees, farmhouse", [N("Chianti. Říjen.")]),
    panel("wide", "l_vineyard", ["petra"], "stumbling between vine rows in heels, holding folder, surprised", sfx=["AU!"], gap="small"),
    panel("medium", "l_vineyard", ["petra", "lorenzo"], "man catching woman by the arm, steady, close",
          [("petra", "Já jsem tu pracovně. Usedlost se prodává.")]),
    panel("close-up", "l_vineyard", ["lorenzo"], "dry humor, slight smile",
          [("lorenzo", "Usedlost ne. Já ano. Ale jen s pozemkem, kočkou a špatným humorem.")]),
    panel("wide", "l_vineyard", ["petra:harvest"], "picking grapes, basket, laughing, sunlight", [N("Sklizeň. Týdny.")]),
    panel("medium", "l_yard", ["petra:harvest", "lorenzo"], "dancing under fig tree, string lights, laughing"),
    panel("medium", "l_cellar", ["lorenzo:evening"], "handing wine glass, lantern light",
          [N("Noc svatého Martina.")]),
    panel("medium", "l_cellar", ["lorenzo:evening"], "speaking softly, holding glass",
          [("lorenzo", "V Toskánsku se říká: dobré víno potřebuje trpělivost. Já čekal tři roky. Ty jsi přišla v říjnu.")]),
    panel("medium", "l_cellar", ["petra:night"], "setting glass down on barrel, taking his hand, smile",
          [("petra", "Pak se napij pomalu.")]),
    panel("medium", "l_cellar", ["petra:night", "lorenzo:evening"], "kiss, lantern light, barrels", gap="small"),
    panel("wide", "l_cellar", [], "lantern blown out by the barrel, dark cellar, wisp of smoke, no humans", gap="large"),
    panel("medium", "l_yard", ["petra:night"], "on phone, morning light, smiling, fig tree",
          [("petra", "Usedlost stahuju z prodeje. Důvod? Osobní. Velmi osobní.")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
