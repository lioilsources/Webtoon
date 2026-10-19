"""Romance set G — ten fashion-and-flirt stories ("Zde je kolekce 10 příběhů… žena hledá / muž hledá").

    python3 m0/romance_g.py        → data/stories/rg_*/{world,storyboard}.json

Same building blocks and rules as stories_romance.py: one medium per story, dialogue near-verbatim (typos fixed),
inner monologue as thought bubbles, never two characters of the same gender in one panel. The source was explicit;
every intimate scene is rewritten SFW: a kiss or an embrace, then a fade-to-black panel (closed door, lamp going
out, curtain in the wind) and a narration line. Mornings after show both fully dressed. No brand names, no lingerie.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}


def ending(w, constraint, tone=None):
    w["canon"]["constraints"] = [constraint]
    if tone:
        w["tone"] = tone
    return w


# 1. Santorini — analogue film ---------------------------------------------------------------------
STORIES["rg_01_santorini"] = story(ending(world("w_rg_01_santorini", "Ztracený luxus na jachtě u Santorini",
    "Elena si mezi modelkami na jachtách připadá nepatřičně, dokud jí Marcus nepodá sklenku šampaňského.", "photo_realvis_film", [
    char("elena", "Elena Rosetti", "1girl", "adult, mature female, petite, curvy, wide hips, long hair, wavy hair, side-swept hair, dark brown hair, brown eyes, olive skin",
         {"default": "white silk blouse, short white skirt, wedge heels, large gold hoop earrings, sunglasses",
          "nosun": "white silk blouse, short white skirt, wedge heels, large gold hoop earrings, holding sunglasses",
          "evening": "red silk evening dress, thin straps, gold hoop earrings, gold bracelet, strappy heels"},
         "a petite curvy Italian woman aged 26, long dark wavy hair swept to one side, olive skin"),
    char("marcus", "Marcus Vane", "1boy", "mature male, tall, athletic, short hair, neat haircut, brown hair, grey eyes, clean-shaven",
         {"default": "white linen shirt, navy tailored shorts, silver diver watch, boat shoes",
          "evening": "light blue linen shirt, white linen trousers, leather loafers, silver diver watch"},
         "a tall athletic British man aged 34, neat short brown hair, clean-shaven, relaxed office worker on holiday"),
], [
    loc("l_deck", "Paluba jachty", "outdoors, luxury yacht, deck, railing, santorini cliffs, white houses on cliff, dark blue sea, sunset, orange and purple sky"),
    loc("l_dinner", "Večeře na palubě", "outdoors, yacht deck, dinner table, candles, champagne glasses, night, santorini lights in distance"),
    loc("l_cabin", "Kajuta", "indoors, yacht cabin, wooden interior, dim warm light, porthole, waves outside"),
]), "Dobrý konec."), [
    panel("establishing", "l_deck", [], "yacht anchored below cliffs, other yachts, sunset", [N("Santorini. Jachta kotví pod útesy.")]),
    panel("wide", "l_deck", ["elena"], "standing at railing, looking at other yachts, from side, sunset, wind in hair"),
    panel("medium", "l_deck", ["elena:nosun"], "taking off sunglasses, sigh, insecure, looking down",
          [("elena", "Všechny ženy tady vypadají jako z mola v Miláně... Já v těchhle šatech jen zkouším zapadnout.")]),
    panel("medium", "l_deck", ["elena:nosun", "marcus"], "man offering champagne glass, woman turning, surprised, sunset",
          [("marcus", "Modelky jsou jen věšáky na šaty.")], gap="small"),
    panel("close-up", "l_deck", ["marcus"], "warm smile, looking at viewer, sunset light",
          [("marcus", "Vy máte v sobě ženskost, ze které se mi tají dech.")]),
    panel("close-up", "l_deck", ["elena:nosun"], "blush, shy smile, holding champagne glass", gap="large"),
    panel("wide", "l_dinner", ["elena:evening", "marcus:evening"], "sitting at candlelit table, laughing, champagne, night",
          [N("Večeře na palubě. Šampaňské a smích.")]),
    panel("medium", "l_cabin", ["elena:evening", "marcus:evening"], "standing at cabin door, embrace, faces close, warm light",
          [("marcus", "Jsi dokonalá. Taková, jaká jsi."), ("elena", "Zůstaň se mnou, Marcusi. Až do rána.")], gap="small"),
    panel("medium", "l_cabin", ["elena:evening", "marcus:evening"], "kiss, closed eyes, hand on cheek, dim light"),
    panel("wide", "l_cabin", [], "closed cabin door, porthole, moonlight on waves, night, empty corridor",
          [N("Dveře kajuty se zavřou. Za okénkem šumí moře.")], gap="large"),
    panel("medium", "l_deck", ["elena", "marcus"], "morning, sitting together on deck, coffee cups, her head on his shoulder, soft sunlight",
          [("elena", "Poprvé se tu necítím navíc."), ("marcus", "Protože jsi přesně tam, kam patříš.")], gap="large"),
])

# 2. Tokio — mono manga ------------------------------------------------------------------------------
STORIES["rg_02_tokio"] = story(ending(world("w_rg_02_tokio", "Podzimní vystřízlivění v Tokiu",
    "Sophia hledá v uspěchaném Tokiu někoho, s kým by zpomalila, a Kenji jí nabídne jedinou noc.", "manga_mono", [
    char("sophia", "Sophia van der Bilt", "1girl", "adult, tall female, very slender, blonde hair, long hair, high ponytail, sleek hair, blue eyes",
         {"default": "black oversized turtleneck, black leather pencil skirt, black thigh-high boots, stiletto heels, high ponytail",
          "morning": "black oversized turtleneck, black leather pencil skirt, hair down, barefoot, wrapped in blanket"},
         "a tall very slender Dutch woman aged 23, sleek blonde high ponytail, black turtleneck"),
    char("kenji", "Kenji Sato", "1boy", "mature male, tall, muscular, black hair, short hair, dark eyes, sharp jawline",
         {"default": "black leather jacket, white t-shirt, dark jeans, boots",
          "morning": "black leather jacket, white t-shirt, dark jeans, fastening wristwatch"},
         "a tall muscular Japanese man aged 29, short black hair, sharp jawline, black leather jacket"),
], [
    loc("l_shibuya", "Šibuja", "outdoors, shibuya, tokyo, night, rain, wet pavement, giant neon signs, crowd with umbrellas, reflections"),
    loc("l_gallery", "Před galerií", "outdoors, art gallery entrance, glass door, rain, neon light, tokyo, night"),
    loc("l_apartment", "Apartmán v Roppongi", "indoors, high-rise apartment, floor-to-ceiling window, tokyo night skyline, minimalist interior, city lights"),
]), "Smutný konec.", "romantický, melancholický"), [
    panel("establishing", "l_shibuya", [], "neon signs, rain, crowd, scramble crossing", [N("Tokio. Šibuja v dešti.")]),
    panel("wide", "l_shibuya", ["sophia"], "walking alone on wet pavement, stiletto boots, neon reflections, umbrella"),
    panel("close-up", "l_shibuya", ["sophia"], "looking around, lonely, rain, neon light on face",
          [("sophia", "Můj život je jen shon. Hledám někoho, s kým bych mohla prostě zpomalit...", "thought")], gap="large"),
    panel("medium", "l_gallery", ["sophia", "kenji"], "man speaking to woman under gallery awning, rain, confident smile",
          [("kenji", "Taky utíkáte před deštěm? Bydlím kousek odsud. Výhled na město vám ten déšť vynahradí.")]),
    panel("close-up", "l_gallery", ["sophia"], "hesitant, small smile, rain drops",
          [("sophia", "Jen na chvíli.")], gap="large"),
    panel("wide", "l_apartment", ["sophia", "kenji"], "standing at window, city lights, night, looking at skyline together",
          [N("Roppongi. Město pod nimi svítí do noci.")]),
    panel("medium", "l_apartment", ["sophia", "kenji"], "kiss by the window, city lights behind, night", gap="small"),
    panel("wide", "l_apartment", [], "city lights through window, lamp switched off, dark room, night",
          [N("Lampa zhasne. Tokio svítí dál.")], gap="large"),
    panel("medium", "l_apartment", ["kenji:morning"], "morning, standing, fastening wristwatch, not looking, cold expression"),
    panel("medium", "l_apartment", ["sophia:morning", "kenji:morning"], "woman standing by window holding coffee cup, man fastening wristwatch by the door, fully clothed, morning light",
          [("sophia", "A... co bude teď, Kenji? Uvidíme se zítra?"),
           ("kenji", "Byla to hezká noc, Sophio. Ale já zítra odlétám do Londýna. Nehledej v tom nic víc.")]),
    panel("close-up", "l_apartment", ["sophia:morning"], "alone, face in hands, single tear, morning light, empty room", gap="large"),
])

# 3. Zermatt — soft pastels --------------------------------------------------------------------------
STORIES["rg_03_zermatt"] = story(ending(world("w_rg_03_zermatt", "Ztraceni ve švýcarských Alpách",
    "Sněhová bouře zavře Claru s horským průvodcem Lukasem v chatě nad Zermattem.", "hassaku_soft", [
    char("clara", "Clara Zimmer", "1girl", "adult, red hair, long hair, freckles, green eyes, pale skin, curvy",
         {"default": "white puffer ski jacket, fur-trimmed hood, black ski pants, fur-lined leather boots, knit cap",
          "sweater": "cream turtleneck sweater, black ski pants, fur-lined boots, hair down"},
         "a curvy German woman aged 28 with long vivid red hair and freckles, white ski jacket"),
    char("lukas", "Lukas Weber", "1boy", "mature male, broad shoulders, muscular, stubble, short hair, brown hair, brown eyes",
         {"default": "red plaid flannel shirt, worn brown leather jacket, work boots",
          "flannel": "red plaid flannel shirt, rolled-up sleeves, work boots"},
         "a broad-shouldered Swiss mountain guide aged 32 with stubble, plaid flannel shirt"),
], [
    loc("l_storm", "Chata v bouři", "outdoors, mountain hut, swiss alps, snowstorm, heavy snow, wooden chalet, warm window light, matterhorn silhouette"),
    loc("l_hut", "U krbu", "indoors, wooden mountain hut, fireplace, crackling fire, sheepskin rug, warm light, snow on window"),
    loc("l_morning", "Ráno nad Zermattem", "outdoors, chalet terrace, swiss alps, fresh snow, clear blue sky, morning sun, matterhorn"),
]), "Dobrý konec."), [
    panel("establishing", "l_storm", [], "snowstorm, lonely chalet, glowing window", [N("Zermatt. Venku zuří sněhová bouře.")]),
    panel("medium", "l_hut", ["clara"], "taking off ski jacket, snow on shoulders, cheeks red from cold", gap="small"),
    panel("medium", "l_hut", ["lukas:flannel"], "adding logs to fireplace, kneeling, looking over shoulder, fire light"),
    panel("close-up", "l_hut", ["clara:sweater"], "pulling off knit cap, blush, looking away, firelight",
          [("clara", "Vždycky jsem se styděla za to, jak moc jsem nápadná. Muži se mi většinou dívají jen na postavu.")]),
    panel("medium", "l_hut", ["clara:sweater", "lukas:flannel"], "man holding her face in his hands, gentle, looking into eyes, firelight",
          [("lukas", "Já se dívám do tvých očí, Claro. Jsi ta nejkrásnější žena, jakou tyhle hory kdy spatřily.")], gap="large"),
    panel("wide", "l_hut", ["clara:sweater", "lukas:flannel"], "sitting together on sheepskin rug by fireplace, wrapped in blanket, mugs of tea",
          [N("Bouře nepolevuje. Nikdo z nich to nelituje.")]),
    panel("medium", "l_hut", ["clara:sweater", "lukas:flannel"], "kiss, his hand in her red hair, firelight, eyes closed",
          [("lukas", "Zůstaň se mnou... Dneska i navždy.")], gap="small"),
    panel("wide", "l_hut", [], "fireplace embers glowing, dark room, snow falling outside window, night",
          [N("Oheň dohasíná. Sníh padá až do rána.")], gap="large"),
    panel("wide", "l_morning", ["clara", "lukas"], "standing on terrace, holding hands, fresh snow, morning sun, smiling",
          [("clara", "Bouře skončila."), ("lukas", "Tak zůstaň kvůli výhledu. A kvůli mně.")], gap="large"),
])

# 4. Bali — city pop ---------------------------------------------------------------------------------
STORIES["rg_04_bali"] = story(ending(world("w_rg_04_bali", "Toulky po plážích Bali",
    "Mei-Ling naskočí za Danielem na motorku k vodopádům a ráno najde jen vzkaz.", "retro_citypop", [
    char("meiling", "Mei-Ling Zhang", "1girl", "adult, mature female, petite, curvy, black hair, long hair, straight hair, brown eyes",
         {"default": "tropical print silk sundress, platform sandals, white sunglasses",
          "evening": "white silk slip dress, jasmine flower in hair, thin gold anklet, barefoot"},
         "a petite curvy Chinese woman aged 25, long straight black hair, tropical silk sundress"),
    char("daniel", "Daniel Cross", "1boy", "mature male, athletic, tan, long hair, blonde hair, hair bun, blue eyes, stubble",
         "short-sleeved hawaiian shirt, buttoned shirt, khaki shorts, leather sandals",
         "an athletic Australian man aged 30, long blond hair tied in a bun, tanned, hawaiian shirt"),
], [
    loc("l_cliff", "Útes Uluwatu", "outdoors, uluwatu, cliff, rough ocean, waves crashing, sunset, beach path"),
    loc("l_road", "Cesta k vodopádům", "outdoors, bali, jungle road, motor scooter, palm trees, golden light"),
    loc("l_waterfall", "Vodopád", "outdoors, jungle waterfall, lush green, mist, sunlight rays"),
    loc("l_villa", "Bambusová vila", "indoors, open bamboo villa, jungle, many candles, warm light, night, sheer curtains"),
    loc("l_terrace", "Terasa za rozbřesku", "outdoors, villa terrace, dawn, jungle mist, wooden table, note on table"),
]), "Smutný konec.", "romantický, hořký"), [
    panel("establishing", "l_cliff", [], "sunset over ocean, cliffs, waves", [N("Uluwatu. Slunce zapadá nad útesem.")]),
    panel("wide", "l_cliff", ["meiling"], "walking along beach path, sundress blowing in wind, sunset"),
    panel("medium", "l_road", ["daniel"], "sitting on motor scooter, grinning, offering spare helmet",
          [("daniel", "Chceš vidět nejhezčí vodopád na ostrově? Naskoč.")]),
    panel("medium", "l_road", ["meiling", "daniel"], "riding motor scooter together, woman holding his waist, laughing, wind", gap="small"),
    panel("wide", "l_waterfall", ["meiling", "daniel"], "standing at waterfall, mist, holding hands, sunlight",
          [("meiling", "Tohle je jako sen."), ("daniel", "Sny jsou na Bali zadarmo.")], gap="large"),
    panel("medium", "l_villa", ["meiling:evening", "daniel"], "candlelit villa, standing close, faces close, warm light, night"),
    panel("medium", "l_villa", ["meiling:evening", "daniel"], "kiss, candlelight, eyes closed", gap="small"),
    panel("wide", "l_villa", [], "candles burning down, sheer curtain blowing in wind, jungle night",
          [N("Závěs se vlní v nočním větru. Svíčky dohořívají.")], gap="large"),
    panel("wide", "l_terrace", ["meiling"], "dawn, standing alone on terrace, finding note and crumpled banknote on table"),
    panel("close-up", "l_terrace", ["meiling"], "reading note, tears in eyes, holding paper, dawn light",
          [N("„Bylo to skvělé, ale já nehledám závazky. Šťastnou cestu, D.“"),
           ("meiling", "Myslela jsem, že to znamenalo něco víc.")], gap="large"),
])

# 5. Chianti — watercolour ----------------------------------------------------------------------------
STORIES["rg_05_chianti"] = story(ending(world("w_rg_05_chianti", "Cyklovýlet po vinicích Toskánska",
    "Isabelle uprostřed vinic praskne řetěz a architekt Gabriele zastaví na starém kole.", "watercolor_paris", [
    char("isabella", "Isabella Conte", "1girl", "adult, tall female, athletic, short hair, curly hair, brown hair, brown eyes, tan skin",
         {"default": "white cycling jersey, black cycling pants, sport sunglasses, cycling helmet",
          "evening": "emerald green silk midi dress, high neckline, (modest clothing:1.2), strappy heels, small gold earrings"},
         "a tall athletic Italian woman aged 27, short curly brown hair, white cycling jersey"),
    char("gabriele", "Gabriele Rossi", "1boy", "mature male, slender, grey temples, short hair, black hair, brown eyes",
         {"default": "light blue linen shirt, beige chino trousers, leather loafers",
          "evening": "white shirt, navy blazer, beige trousers, leather loafers"},
         "a slender Italian architect aged 35 with greying temples, light blue linen shirt"),
], [
    loc("l_vines", "Vinice v Chianti", "outdoors, tuscany, rolling hills, vineyard rows, cypress trees, gravel road, sunny"),
    loc("l_cellar", "Vinný sklípek", "indoors, stone wine cellar, wine barrels, wine tasting, candles, arched ceiling"),
    loc("l_pergola", "Pergola u vily", "outdoors, tuscan villa, pergola, grape vines, string lights, evening, hills at dusk"),
]), "Dobrý konec."), [
    panel("establishing", "l_vines", [], "rolling hills, vineyards, cypress", [N("Chianti. Kopce, víno a cypřiše.")]),
    panel("wide", "l_vines", ["isabella"], "standing next to bicycle, broken chain, frustrated, hands on hips", sfx=["CVAK!"]),
    panel("medium", "l_vines", ["gabriele"], "riding vintage bicycle, stopping, smiling",
          [("gabriele", "Řetěz? To se spraví. Toskánsko vás jen chce zdržet.")]),
    panel("medium", "l_vines", ["isabella", "gabriele"], "man kneeling, fixing bicycle chain, woman watching, smile",
          [("isabella", "Vy opravujete kola i v košili?"), ("gabriele", "Jsem architekt. Opravuju všechno, co drží pohromadě.")], gap="large"),
    panel("wide", "l_cellar", ["isabella:evening", "gabriele:evening"], "wine tasting, raising glasses, candlelight, laughing",
          [N("Večer. Degustace ve starém sklípku.")]),
    panel("medium", "l_cellar", ["isabella:evening"], "slipping off heels, sitting on bench, relaxed smile",
          [("isabella", "Celý den v sedle a teď ještě podpatky...")], gap="small"),
    panel("medium", "l_pergola", ["isabella:evening", "gabriele:evening"], "standing under pergola, string lights, holding hands, dusk",
          [("gabriele", "Našel jsem v tobě čistotu, kterou jsem v městském shonu dlouho hledal.")]),
    panel("medium", "l_pergola", ["isabella:evening", "gabriele:evening"], "kiss, string lights, warm glow", gap="small"),
    panel("wide", "l_pergola", [], "villa window light turning off, string lights, starry night over hills",
          [N("Světla vily zhasnou. Nad kopci se rozsvítí hvězdy.")], gap="large"),
    panel("wide", "l_vines", ["isabella", "gabriele"], "morning, riding bicycles side by side, vineyard road, sunlight, smiling",
          [("isabella", "Pojedeš se mnou až do Sieny?"), ("gabriele", "Pojedu s tebou kamkoli.")], gap="large"),
])

# 6. Las Vegas — 1950s poster ---------------------------------------------------------------------------
STORIES["rg_06_vegas"] = story(ending(world("w_rg_06_vegas", "Noc v kasinu v Las Vegas",
    "Texaský rančer Jack uvěří zářivému úsměvu Veroniky a ráno přijde o hodinky i iluze.", "vintage_poster", [
    char("jack", "Jack „Jackson“ Reed", "1boy", "mature male, muscular, broad shoulders, buzz cut, grey hair, stubble, blue eyes",
         {"default": "charcoal tailored suit, white shirt, crocodile leather cowboy boots, gold wristwatch",
          "morning": "white dress shirt, suit trousers, bare wrist, rumpled"},
         "a broad-shouldered Texan rancher aged 39 with a greying buzz cut, charcoal tailored suit"),
    char("veronica", "Veronica Vance", "1girl", "adult, tall female, long legs, blonde hair, long hair, wavy hair, blue eyes, red lips",
         "gold sequin dress, short dress, stiletto heels, diamond necklace",
         "a tall blonde American woman aged 25, long wavy hair, gold sequin dress, diamond necklace"),
], [
    loc("l_bar", "Bar v kasinu", "indoors, luxury casino bar, gold decor, crystal chandeliers, bourbon glass, warm light"),
    loc("l_casino", "Herna", "indoors, casino floor, roulette table, slot machines, glittering lights"),
    loc("l_suite", "Apartmá", "indoors, luxury hotel suite, marble, large window, las vegas fountains at night, city lights"),
]), "Smutný konec.", "romantický, hořce ironický"), [
    panel("establishing", "l_casino", [], "glittering casino, roulette, lights", [N("Las Vegas. Zlato, křišťál a štěstí na prodej.")]),
    panel("medium", "l_bar", ["jack"], "sitting at bar, ordering bourbon, adjusting suit jacket, alone"),
    panel("medium", "l_bar", ["jack", "veronica"], "woman sitting down next to him, dazzling smile, crystal chandeliers",
          [("jack", "Co hledá taková mladá dáma u starého chlapíka z ranče?")]),
    panel("close-up", "l_bar", ["veronica"], "hand on his shoulder, seductive smile, red lips",
          [("veronica", "Hledám opravdového muže, ne kluky z Instagramu.")], gap="large"),
    panel("wide", "l_casino", ["jack", "veronica"], "roulette table, woman cheering, man placing chips, laughing",
          [N("Kolo rulety se točí. Jack vyhrává a ona tleská.")]),
    panel("medium", "l_suite", ["jack", "veronica"], "standing at window, fountains show outside, embrace, night"),
    panel("medium", "l_suite", ["jack", "veronica"], "kiss, city lights, night", gap="small"),
    panel("wide", "l_suite", [], "closed suite door, do not disturb sign, hotel corridor, night",
          [N("Dveře apartmá se zavřou.")], gap="large"),
    panel("wide", "l_suite", ["jack:morning"], "morning light through curtains, empty nightstand, sitting in armchair, alone"),
    panel("close-up", "l_suite", ["jack:morning"], "bitter smile, looking at bare wrist, morning light",
          [N("Hodinky i peněženka jsou pryč. Veronica taky."),
           ("jack", "Starý naivní blázen... Nalítl jsi na lesk Vegas.")], gap="large"),
])

# 7. Rio — western comic --------------------------------------------------------------------------------
STORIES["rg_07_rio"] = story(ending(world("w_rg_07_rio", "Tajemná noc na Copacabaně",
    "Boxer Carlos zastane Beatrice před dotěrou a ona v něm uvidí víc než rváče.", "western_comic", [
    char("carlos", "Carlos Mendoza", "1boy", "mature male, muscular, athletic, scar on face, scar on eyebrow, short hair, black hair, brown eyes, tan skin",
         {"default": "white linen shirt, dark shorts, leather sandals",
          "training": "grey tank top, black shorts, boxing hand wraps"},
         "a muscular Brazilian boxer aged 28 with scars on his face, white linen shirt"),
    char("beatrice", "Beatrice Leclerc", "1girl", "adult, mature female, petite, curvy, curly hair, dark brown hair, long hair, brown eyes",
         {"default": "flowy floral summer dress, leather sandals, oversized sunglasses",
          "evening": "blush pink silk dress, gold sandals, small gold hoops"},
         "a petite curvy French woman aged 26, dark curly hair, floral summer dress"),
    char("pest", "Dotěra", "1boy", "young man, adult, smug, tank top, cap, sunglasses", "tank top, baseball cap, sunglasses",
         "a pushy young man with a cap and sunglasses"),
], [
    loc("l_beach", "Copacabana", "outdoors, copacabana beach, wave pattern mosaic promenade, palm trees, evening, warm wind, outdoor gym"),
    loc("l_terrace", "Terasa v Santa Teresa", "outdoors, rooftop terrace, small pool, candles, night, rio de janeiro lights, stars"),
]), "Dobrý konec."), [
    panel("establishing", "l_beach", [], "mosaic promenade, beach, palm trees, sunset", [N("Rio de Janeiro. Copacabana.")]),
    panel("wide", "l_beach", ["carlos:training"], "training at outdoor gym, pull-ups, sweat, focused"),
    panel("medium", "l_beach", ["beatrice", "pest"], "pushy man blocking woman's way, woman annoyed, stepping back",
          [("pest", "Kam tak spěcháš, krásko?")], gap="small"),
    panel("medium", "l_beach", ["beatrice", "carlos:training"], "man stepping between, calm, protective, woman behind him",
          [("carlos", "Dáma už odchází. A ty taky.")]),
    panel("close-up", "l_beach", ["beatrice"], "relieved sigh, looking up, smile",
          [("beatrice", "Děkuji vám... Vypadáte jako někdo, kdo se nebojí vůbec ničeho.")]),
    panel("close-up", "l_beach", ["carlos:training"], "looking down, shy, scars",
          [("carlos", "Lidé se mě spíš bojí. Myslí si, že umím jen bojovat.")], gap="large"),
    panel("wide", "l_terrace", ["beatrice:evening", "carlos"], "candlelit rooftop terrace, samba music from street, sitting by pool, night",
          [N("Santa Teresa. Z dálky zní samba.")]),
    panel("medium", "l_terrace", ["beatrice:evening", "carlos"], "woman gently touching scar on his eyebrow, tender, candlelight",
          [("carlos", "S tebou se cítím v bezpečí... poprvé v životě.")], gap="small"),
    panel("medium", "l_terrace", ["beatrice:evening", "carlos"], "kiss on her shoulder, embrace, stars"),
    panel("wide", "l_terrace", [], "empty terrace, candles, pool reflecting stars, rio lights",
          [N("Nad Riem svítí hvězdy.")], gap="large"),
    panel("medium", "l_beach", ["beatrice", "carlos"], "morning, walking on beach holding hands, sunrise, smile",
          [("beatrice", "Tak co, rváči? Půjdeme zítra zase na pláž?"), ("carlos", "Každé ráno.")], gap="large"),
])

# 8. Lake Como — semi-real 2.5D ---------------------------------------------------------------------------
STORIES["rg_08_como"] = story(ending(world("w_rg_08_como", "Romantika u jezera Como",
    "Analytik Max se na galavečeru zamiluje do Aurelie, jejíž život patří dohodnutému sňatku.", "semireal_25d", [
    char("max", "Maximilian „Max“ Vane", "1boy", "mature male, slender, elegant, short hair, slicked back hair, dark brown hair, grey eyes",
         {"default": "black tailored suit, white shirt, silk tie, luxury wristwatch",
          "morning": "white shirt, loosened tie, suit trousers, rolled-up sleeves"},
         "a slender elegant German banker aged 42, slicked-back dark hair, black tailored suit"),
    char("aurelia", "Aurelia Valenti", "1girl", "adult, red hair, medium hair, wavy hair, green eyes, pale skin",
         {"default": "emerald green evening gown, off-shoulder gown, high heels, pearl earrings",
          "morning": "cream silk blouse, wide-leg trousers, pearl earrings, hair tied back"},
         "an Italian woman aged 24 with shoulder-length red hair, emerald evening gown"),
    char("fiance", "Snoubenec", "1boy", "old man, grey hair, stern, wrinkles", "dark three-piece suit, gold cufflinks",
         "an influential stern man in his sixties, grey hair, dark three-piece suit"),
], [
    loc("l_gala", "Terasa vily", "outdoors, lake como, villa terrace garden, cypress trees, moonlight on lake, gala, lanterns, night"),
    loc("l_suite", "Suita nad jezerem", "indoors, luxury suite, balcony doors open, view of lake como at night, moonlight"),
    loc("l_breakfast", "Ranní terasa", "outdoors, villa terrace, breakfast table, coffee, lake como, morning mist"),
]), "Smutný konec.", "romantický, tragický"), [
    panel("establishing", "l_gala", [], "villa garden, lanterns, moonlight on lake", [N("Jezero Como. Dobročinný galavečer.")]),
    panel("medium", "l_gala", ["max"], "standing alone holding champagne glass, bored, looking at watch"),
    panel("medium", "l_gala", ["max", "aurelia"], "woman approaching, smiling, lanterns, man turning",
          [("aurelia", "Vypadáte, že počítáte minuty do konce."),
           ("max", "Počítal. Teď počítám, kolik jich zbývá s vámi.")]),
    panel("close-up", "l_gala", ["aurelia"], "laughing, green eyes, pearl earrings, lantern light",
          [("aurelia", "Tak je nepočítejte, Maxi.")], gap="large"),
    panel("wide", "l_gala", ["max", "aurelia"], "walking along terrace by the lake, moonlight, talking, close",
          [N("Mluví o knihách, o hvězdách, o všem kromě zítřka.")]),
    panel("medium", "l_suite", ["max", "aurelia"], "standing on balcony, embrace, moonlight on lake",
          [("max", "Miluju tě, Aurelie.")], gap="small"),
    panel("medium", "l_suite", ["max", "aurelia"], "kiss, moonlight, eyes closed"),
    panel("wide", "l_suite", [], "balcony curtains moving in the wind, moonlight on lake, night",
          [N("Záclony se vlní. Jezero mlčí.")], gap="large"),
    panel("medium", "l_breakfast", ["aurelia:morning", "fiance"], "older man entering terrace, stern, woman standing up, shocked"),
    panel("close-up", "l_breakfast", ["aurelia:morning"], "tears in eyes, looking back, whisper",
          [("aurelia", "Odpusť mi, Maxe... Tahle noc byla můj sen. Ale můj život patří mé rodině.")]),
    panel("wide", "l_breakfast", ["max:morning"], "alone, leaning on railing, looking at cold lake, from behind, morning mist", gap="large"),
])

# 9. Costa Rica — 3D animation ------------------------------------------------------------------------------
STORIES["rg_09_kostarika"] = story(ending(world("w_rg_09_kostarika", "Ztraceni v deštném pralese na Kostarice",
    "Mechanik Leo opravuje Sophiin džíp u sopky Arenal a ona v něm najde, co doma nikdy nepotkala.", "photo_lightning", [
    char("leo", "Leo Baker", "1boy", "mature male, muscular, short hair, black hair, brown eyes, stubble",
         {"default": "grey outdoor shirt, rolled-up sleeves, cargo pants, work boots, oil stains",
          "clean": "olive green button-up shirt, cargo pants, hiking boots"},
         "a muscular American mechanic aged 26 with short dark hair"),
    char("sophie", "Sophie Laurent", "1girl", "adult, tall female, slender, blonde hair, long hair, blue eyes",
         {"default": "floral midi dress, wide-brim straw hat, flat sandals",
          "evening": "white linen dress, light rain jacket, hair loose"},
         "a tall slender French woman aged 23, long blonde hair"),
], [
    loc("l_bungalow", "Bungalov u Arenalu", "outdoors, wooden bungalow, rainforest, arenal volcano in background, rain, old jeep with open hood"),
    loc("l_spring", "Termální jezírko", "outdoors, natural hot spring pool, stone edge, steam, palm trees, rain, evening, lanterns"),
    loc("l_road", "Lesní cesta", "outdoors, jungle road, rainforest, morning sun, jeep, puddles"),
]), "Dobrý konec."), [
    panel("establishing", "l_bungalow", [], "rainforest, volcano, rain", [N("Kostarika. Pod sopkou Arenal prší.")]),
    panel("wide", "l_bungalow", ["leo"], "leaning into jeep engine, open hood, oil stains, rain"),
    panel("medium", "l_bungalow", ["sophie", "leo"], "woman holding drink, offering towel, man wiping hands, smile",
          [("sophie", "Jsi neuvěřitelně zručný... Ve světě, ze kterého pocházím, muži neumí zatlouct ani hřebík.")]),
    panel("close-up", "l_bungalow", ["leo"], "grin, smudge of oil on cheek",
          [("leo", "Já zase neumím mluvit na večírcích. Ale vím, jak dát věci do pořádku.")], gap="large"),
    panel("medium", "l_bungalow", ["sophie", "leo"], "engine running, smoke, cheering, high five", sfx=["BRRUM!"]),
    panel("wide", "l_spring", ["sophie:evening", "leo:clean"], "sitting on stone edge of hot spring, feet in warm water, steam, lanterns, rain on palms",
          [N("Večer u termálního jezírka. Na palmy bubnuje déšť.")]),
    panel("medium", "l_spring", ["sophie:evening", "leo:clean"], "her head on his shoulder, steam, lanterns",
          [("sophie", "Nikdy jsem nechtěla, aby déšť přestal."), ("leo", "Tak ať prší celou noc.")], gap="small"),
    panel("medium", "l_spring", ["sophie:evening", "leo:clean"], "kiss, rain drops, lantern glow"),
    panel("wide", "l_bungalow", [], "bungalow window light switching off, rain, rainforest night",
          [N("Světlo v bungalovu zhasne. Prší až do rána.")], gap="large"),
    panel("wide", "l_road", ["sophie", "leo:clean"], "driving jeep together, morning sun, laughing, rainforest road",
          [("sophie", "Kam teď?"), ("leo", "Kamkoli. Džíp i já jsme opravení.")], gap="large"),
])

# 10. Bergen — flat minimalism --------------------------------------------------------------------------------
STORIES["rg_10_bergen"] = story(ending(world("w_rg_10_bergen", "Zimní samota v norských fjordech",
    "Elena hledá úkryt před vichřicí ve skleněném domě bývalého boxera Neda.", "minimal_flat", [
    char("ned", "Edward „Ned“ Thorne", "1boy", "mature male, large build, broad shoulders, beard, grey beard, wrinkles, short hair, grey hair",
         "heavy knit sweater, dark leather trousers, boots",
         "a large former boxer aged 45 with a grey beard and deep wrinkles, heavy knit sweater"),
    char("elena", "Elena Vasylyk", "1girl", "adult, red hair, long hair, wavy hair, green eyes, pale skin",
         {"default": "camel wool coat, plaid scarf, leather boots, snow on coat",
          "indoor": "cream knit sweater, dark trousers, hair down",
          "coat": "camel wool coat, plaid scarf, leather boots"},
         "a Ukrainian woman aged 27 with long wavy red hair, camel wool coat and plaid scarf"),
], [
    loc("l_glass", "Skleněný dům nad fjordem", "indoors, modern glass house, wood stove, fjord view, snowy mountains, night, warm light"),
    loc("l_aurora", "Pod skleněnou střechou", "indoors, glass roof, green aurora borealis, northern lights, night sky, sofa, blankets"),
    loc("l_port", "Přístav v Bergenu", "outdoors, bergen harbor, ferry, pier, snow, grey morning, colorful wooden houses"),
]), "Smutný konec.", "romantický, melancholický"), [
    panel("establishing", "l_glass", [], "glass house on cliff above fjord, snowstorm, glowing windows", [N("Bergen. Nad fjordem zuří vichřice.")]),
    panel("medium", "l_glass", ["ned"], "sitting by wood stove, whittling wood with knife, calm"),
    panel("wide", "l_glass", ["elena"], "standing in doorway, snow on coat, shivering, wind",
          [("elena", "Promiňte... Můžu se tu schovat, než vichřice přejde?")], gap="small"),
    panel("medium", "l_glass", ["elena", "ned"], "man taking her snowy coat, warm stove light",
          [("ned", "Pojďte dál, než vás vítr odnese. Kamna hřejí pro dva.")], gap="large"),
    panel("wide", "l_aurora", ["elena:indoor", "ned"], "sitting together on sofa under glass roof, wrapped in blanket, green aurora above",
          [N("Bouře utichne a nebe se rozsvítí zeleně.")]),
    panel("close-up", "l_aurora", ["elena:indoor"], "looking up at aurora, red hair glowing in green light, wonder"),
    panel("medium", "l_aurora", ["elena:indoor", "ned"], "kiss, aurora light, eyes closed", gap="small"),
    panel("wide", "l_aurora", [], "aurora borealis over glass roof, dark room, stove embers",
          [N("Polární záře tančí až do rána.")], gap="large"),
    panel("wide", "l_port", ["elena:coat", "ned"], "standing at ferry gangway, holding both his hands, snow, ferry horn",
          [("elena", "Můj život je v Kyjevě, Nede... Ty patříš těmhle horám. Ta noc byla zázrak, ale naše světy jsou moc daleko.")],
          sfx=["HÚÚÚ"]),
    panel("medium", "l_port", ["elena:coat", "ned"], "kiss on her forehead, letting go of her hands, snow",
          [("ned", "Budeš moje polární záře, na kterou budu vzpomínat každou zimu. Šťastnou cestu, Eleno.")]),
    panel("wide", "l_port", ["ned"], "standing alone on pier, ferry sailing away into fjord, snow, from behind", gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
