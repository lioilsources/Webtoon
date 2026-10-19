"""Romance set J — "Romantické příběhy pro dospělé — druhá série" (ten film scripts, fade to black).

    python3 m0/romance_j.py        → data/stories/rj_*/{world,storyboard}.json

Same building blocks and rules as stories_romance.py: one medium per story, dialogue near-verbatim (typos fixed,
Portuguese translated), inner monologue as thought bubbles, never two characters of the same gender in one panel.
SFW: swimwear became resort fashion, undressing stops at hats, jackets and shoes; intimacy is a kiss, then the door
closes. Fashion is the theme, so every character has several named outfits.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}


def ending(w, text):
    w["canon"]["constraints"] = [text]
    return w


# 1. Saint-Tropez — analogue film ------------------------------------------------------------------
STORIES["rj_01_sainttropez"] = story(ending(world("w_rj_01_sainttropez", "Jachta u Saint-Tropez",
    "Valentina si po pěti letech bez dovolené nechá od majitele jachty Lucy ukrást večer na moři.", "photo_realvis_film", [
    char("valentina", "Valentina Rossi", "1girl", "adult, curvy, red hair, long hair, wavy hair, freckles, green eyes",
         {"default": "white linen kaftan dress with gold trim, wide-brimmed sun hat, gold bangles, sunglasses on head",
          "evening": "sheer white silk kimono over white maxi dress, gold bangles, hair down",
          "morning": "oversized white shirt dress, gold bangles, barefoot"},
         "an Italian woman aged 29 from Milan, wavy red hair, freckles, curvy figure"),
    char("luca", "Luca Ferri", "1boy", "mature male, olive skin, messy hair, brown hair, brown eyes, stubble, athletic",
         {"default": "white polo shirt, white sailing trousers, boat shoes", "evening": "light blue linen shirt, white sailing trousers, rolled sleeves"},
         "a French-Italian yacht owner aged 35, olive skin, tousled brown hair"),
], [
    loc("l_port", "Přístav", "outdoors, harbor, marina, white yachts, saint-tropez, afternoon, sunlight, pier, lavender"),
    loc("l_deck", "Paluba", "outdoors, yacht deck, night, open sea, harbor lights in distance, wine glasses, table, lantern"),
    loc("l_bow", "Příď", "outdoors, yacht bow, night, moonlight, moonlight reflection on sea, railing, starry sky"),
    loc("l_cabin", "Kajuta", "indoors, yacht cabin door, wooden door, dim light, night, porthole"),
]), "Šťastný konec: zůstanou spolu na lodi."), [
    panel("establishing", "l_port", [], "yachts, sparkling sea, sunny", [N("Saint-Tropez. Pozdní léto.")]),
    panel("medium", "l_port", ["valentina"], "standing on pier, holding martini glass, looking at sea, wind",
          [("valentina", "Pět let bez dovolené. Tohle martini si zasloužím.", "thought")]),
    panel("medium", "l_port", ["luca"], "standing on yacht deck, calling out, waving, smile",
          [("luca", "Madame! Jste jediná v přístavu, kdo se dívá na moře. Ostatní koukají na jachty.")]),
    panel("close-up", "l_port", ["valentina"], "amused smile, raised eyebrow, looking up",
          [("valentina", "A vy se díváte na mě. Tak kdo z nás dvou se tu nepředvádí?")], gap="small"),
    panel("medium", "l_port", ["valentina", "luca"], "man leaning over railing, woman on pier, looking at each other",
          [("luca", "Já. Ale jen abych vás pozval na večerní plavbu. Žádný přístav, žádní lidé. Jen vítr a víno."),
           ("valentina", "Pozvání na útěk je nejlepší lichotka. V osm?")], gap="large"),
    panel("wide", "l_deck", ["valentina:evening", "luca:evening"], "sitting at table, facing each other, pouring wine, candlelight",
          [("valentina", "Pět let jsem dělala PR pro cizí sny. Zapomněla jsem, jaké jsou moje.")]),
    panel("close-up", "l_deck", ["luca:evening"], "gentle smile, reaching across table",
          [("luca", "Tuhle loď jsem koupil po rozchodu. Myslel jsem, že kupuju útěk. Kupoval jsem čekání.")], gap="small"),
    panel("close-up", "l_deck", ["valentina:evening"], "soft smile, looking at viewer, candlelight",
          [("valentina", "Na co?"), ("luca", "Na někoho, kdo se zeptá, na co se dívám, a nechá mi čas na odpověď.")], gap="large"),
    panel("medium", "l_bow", ["valentina:evening", "luca:evening"], "standing at railing side by side, moonlight, woman holding his collar",
          [("valentina", "Luco. Já se nechci vrátit do přístavu. Ani zítra, ani pozítří."), ("luca", "Tak zůstaň. Loď má místo pro dva.")]),
    panel("medium", "l_bow", ["valentina:evening", "luca:evening"], "kiss, kissing, embrace, moonlight, wind in hair", gap="small"),
    panel("wide", "l_cabin", [], "closed cabin door, warm light under door, moonlight on water through porthole",
          [N("Dveře kajuty se zavřou. Zůstane jen měsíc na vodě.")], gap="large"),
    panel("medium", "l_deck", ["valentina:morning", "luca"], "morning, sunrise, sharing coffee on deck, smiling, leaning on shoulder",
          [N("Ráno nikdo nemíří do přístavu.")]),
])

# 2. Cortina — mono manga ----------------------------------------------------------------------------
STORIES["rj_02_cortina"] = story(ending(world("w_rj_02_cortina", "Hory nad Cortinou",
    "Klára se rok učila lyžovat kvůli instruktorovi Matteovi a teď se vrací pro odpověď.", "manga_mono", [
    char("klara", "Klára Dvořáková", "1girl", "adult, tall female, slender, black hair, long hair, dark eyes, red lips",
         {"default": "red ski jacket, black ski pants, ski goggles on head, gloves",
          "chalet": "fitted turtleneck sweater, slim jeans, hair down, red lips",
          "coat": "long red wool coat, turtleneck sweater, ski goggles in hand"},
         "a tall slender Czech woman aged 27, long black hair, red lipstick, red ski jacket"),
    char("matteo", "Matteo Bellini", "1boy", "mature male, tanned skin, blonde hair, short hair, blue eyes, athletic, bright smile",
         {"default": "ski instructor jacket, ski pants, beanie", "chalet": "cream cable knit sweater, dark trousers"},
         "an Italian ski instructor aged 33, tanned, short blond hair, ski instructor jacket"),
], [
    loc("l_lift", "Lanovka", "outdoors, ski resort, chairlift queue, snow, dolomites, mountains, sunny, morning"),
    loc("l_chalet", "Chalet", "indoors, wooden chalet, fireplace, window, night, cable car lights outside, grappa glasses"),
    loc("l_terrace", "Terasa", "outdoors, chalet terrace, night, snow falling, valley lights, starry sky, breath mist"),
]), "Hořký konec: Klára odjede sama a silnější."), [
    panel("establishing", "l_lift", [], "snowy peaks, skiers, chairlift", [N("Cortina d'Ampezzo. Lyžařská sezóna.")]),
    panel("medium", "l_lift", ["klara"], "standing in queue, goggles on head, determined, looking ahead",
          [("klara", "Rok jsem se učila lyžovat. Kvůli jednomu úsměvu.", "thought")]),
    panel("medium", "l_lift", ["klara", "matteo"], "man approaching, bright smile, woman lifting goggles",
          [("matteo", "Signora. Jste tu poprvé? Ten postoj na lyžích je na vás vidět."),
           ("klara", "Druhý rok. Lyžuju kvůli instruktorovi, který mě loni naučil první oblouk a pak se neozval.")]),
    panel("close-up", "l_lift", ["matteo"], "awkward smile, surprised", [("matteo", "To musel být hlupák.")], gap="small"),
    panel("close-up", "l_lift", ["klara"], "cool smile, red lips", [("klara", "Byl. Ale měl krásný úsměv. Ten si pamatuju přesně.")], gap="large"),
    panel("wide", "l_chalet", ["klara:chalet", "matteo:chalet"], "sitting by fireplace, holding small glasses, firelight",
          [("matteo", "Chtěl jsem zavolat. Ale já nejsem člověk pro telefonáty. Jsem člověk pro hory."),
           ("klara", "A co jsi za člověka, Matteo, když nejsi na hoře?")]),
    panel("close-up", "l_chalet", ["matteo:chalet"], "looking down, silent, firelight, shadow",
          [("matteo", "Bojím se, že když z hory sestoupím, nic ze mě nezbude.")], gap="large"),
    panel("medium", "l_terrace", ["klara:chalet", "matteo:chalet"], "kiss, kissing, embrace, snow falling, night", gap="small"),
    panel("medium", "l_terrace", ["klara:chalet", "matteo:chalet"], "man pulling away, hands on her shoulders, pained expression",
          [("matteo", "Kláro, nemůžu. Ty nejsi jen jedna ze sezón. A já neumím slíbit, že budu existovat, až sníh roztaje.")]),
    panel("close-up", "l_terrace", ["klara:coat"], "putting on coat, small smile, calm, snow",
          [("klara", "Před rokem bych plakala. Dneska si vezmu kabát a pojedu domů."),
           ("klara", "Byls můj krásný mýtus, Matteo. Mýty patří do hor. Já patřím dolů.")]),
    panel("wide", "l_terrace", ["matteo:chalet"], "standing alone on terrace, snow on shoulders, from behind, valley lights",
          [N("Sníh mu padá na ramena. Poprvé si ho nevšímá.")], gap="large"),
])

# 3. Bali — pastel shoujo ---------------------------------------------------------------------------
STORIES["rj_03_bali"] = story(ending(world("w_rj_03_bali", "Tanec na Bali",
    "Surfař Noah uvidí Ayu tančit pro hosty resortu a poprvé za rok nemá kam spěchat.", "clean_webtoon_noartist", [
    char("ayu", "Ayu Lestari", "1girl", "adult, slender, tan skin, black hair, very long hair, brown eyes, flower in hair",
         {"default": "(long sleeves:1.3), (modest clothing:1.2), gold embroidered kebaya blouse, gold embroidered sash, long batik sarong skirt, flower crown, gold bracelets",
          "surf": "long sleeve rash guard, board shorts over leggings, wet hair",
          "evening": "white lace kebaya blouse, long batik sarong skirt, frangipani in hair"},
         "an Indonesian dancer aged 26, very long black hair with a flower behind the ear"),
    char("noah", "Noah Bennett", "1boy", "mature male, broad shoulders, messy hair, sandy blonde hair, blue eyes, tan skin, stubble",
         {"default": "faded loose t-shirt, board shorts, shell necklace", "surf": "long sleeve rash guard, board shorts",
          "evening": "white linen shirt, rolled sleeves, khaki shorts"},
         "an Australian surfer aged 31, salty sandy blond hair, broad shoulders, faded t-shirt"),
], [
    loc("l_stage", "Pláž resortu", "outdoors, beach resort, sunset, frangipani, torches, guests seated, ocean"),
    loc("l_waves", "Vlny", "outdoors, ocean, surfboards, morning, low tide, waves, sunlight, sitting on surfboard"),
    loc("l_hut", "Chýše", "outdoors, beach hut, night, oil lamp, lanterns, blanket on sand, coconuts, starry sky"),
]), "Šťastný konec: Noah zůstává."), [
    panel("establishing", "l_stage", [], "sunset over ocean, torches", [N("Bali, Uluwatu. Soumrak.")]),
    panel("wide", "l_stage", ["ayu"], "dancing, traditional dance, graceful hands, elegant pose"),
    panel("medium", "l_stage", ["noah"], "sitting in back row, surfboard beside, captivated, hand on chest",
          [("noah", "Poprvé za rok nekoukám do telefonu.", "thought")], gap="large"),
    panel("medium", "l_stage", ["ayu", "noah"], "man approaching after dance, woman smiling, torchlight",
          [("noah", "Nevím, co ten tanec znamenal. Ale cítil jsem ho tady."),
           ("ayu", "Jste první host, který neříká „krásné“. Všichni říkají „krásné“.")]),
    panel("close-up", "l_stage", ["noah"], "grin, embarrassed",
          [("noah", "Jsem Australan. „Krásné“ nám trvá dvě hodiny. „Cítil jsem“ jde rychle.")], gap="small"),
    panel("close-up", "l_stage", ["ayu"], "laughing, flower in hair",
          [("ayu", "Zítra v šest je odliv. Půjčím vám prkno."), ("noah", "A co tanec pro vás?")], gap="large"),
    panel("wide", "l_waves", ["ayu:surf", "noah:surf"], "sitting on surfboards side by side, wet, laughing, morning sun",
          [("ayu", "Máte dobrou rovnováhu. Na Australana.")]),
    panel("medium", "l_waves", ["ayu:surf", "noah:surf"], "looking at each other, serious, water sparkles",
          [("ayu", "Já tady žiju, Noahu. A hosté odjíždějí."), ("noah", "Nemám zpáteční letenku. Měl jsem. Propadla.")]),
    panel("medium", "l_hut", ["ayu:evening", "noah:evening"], "sitting on blanket, oil lamp, holding hands",
          [("ayu", "Bojím se. Tady se hosté zamilují do západu slunce, ne do ženy."),
           ("noah", "Nezapisuju si do paměti jednu noc. Zapisuju roky.")]),
    panel("medium", "l_hut", ["ayu:evening", "noah:evening"], "kiss, kissing, embrace, lantern light",
          [("ayu", "Zůstaň. Ne jako host. Jako můj."), ("noah", "Ano.")], gap="small"),
    panel("wide", "l_hut", [], "lanterns glowing, hut in darkness, stars, two pairs of footprints in sand",
          [N("Lampiony nechali hořet až do rána.")], gap="large"),
])

# 4. Istanbul — art nouveau -------------------------------------------------------------------------
STORIES["rj_04_istanbul"] = story(ending(world("w_rj_04_istanbul", "Koberce v Istanbulu",
    "Průvodkyně Selma uvěří obchodníkovi s koberci Canovi, dokud nepřečte vzor jeho dárku.", "art_nouveau_mucha", [
    char("selma", "Selma Aydın", "1girl", "adult, curly hair, brown hair, long hair, almond-shaped eyes, red lips",
         {"default": "long camel coat, silk blouse, gold earrings, red lipstick",
          "evening": "deep green silk midi dress, long camel coat over shoulders, gold earrings, hair down"},
         "a Turkish art historian aged 30, curly brown hair, almond eyes, long coat and gold earrings"),
    char("can", "Can Demir", "1boy", "mature male, black hair, slicked back hair, dark eyes, long eyelashes, trimmed beard",
         {"default": "tailored burgundy vest, white shirt, dark trousers, pocket square",
          "evening": "dark wool overcoat, white shirt, dark trousers"},
         "a Turkish carpet merchant aged 36, slicked black hair, trimmed beard, perfectly tailored vest"),
], [
    loc("l_bazaar", "Velký bazar", "indoors, grand bazaar, istanbul, lanterns, carpets hanging, gold jewelry shop, spices, crowd, arches"),
    loc("l_bosphorus", "Bospor", "outdoors, boat deck, bosphorus, night, bridge lights, city lights on both shores, tea glasses"),
    loc("l_shop", "Krám s koberci", "indoors, carpet shop, carpets hanging like curtains, single lamp, night, ornate patterns"),
]), "Hořký konec: Selma odchází, Can zůstane sám."), [
    panel("establishing", "l_bazaar", [], "labyrinth of shops, lanterns, gold", [N("Istanbul. Velký bazar.")]),
    panel("medium", "l_bazaar", ["selma"], "leading tourists, raised hand, confident, walking"),
    panel("medium", "l_bazaar", ["can"], "standing before carpet shop, calm, arms crossed, looking at viewer",
          [("can", "Madam. Průvodkyně tu mívají v očích únavu. Vy máte v očích moře.")]),
    panel("close-up", "l_bazaar", ["selma"], "surprised, slight smile", [("selma", "Moře?")], gap="small"),
    panel("medium", "l_bazaar", ["selma", "can"], "facing each other, carpets behind, lantern light",
          [("can", "Hluboké. S ostrovem, ke kterému se nikomu nechce plavat."), ("selma", "Vy byste se odvážil?"),
           ("can", "Přijďte večer. Ukážu vám koberec, který se nedá koupit penězi. Bospor.")], gap="large"),
    panel("wide", "l_bosphorus", ["selma:evening", "can:evening"], "sitting on deck, tea glasses, bridge lights",
          [("selma", "Čtu pravdu ve vzorech. I v očích. Je to moje pracovní deformace."), ("can", "Tak si ve mně přečtěte pravdu.")]),
    panel("medium", "l_bosphorus", ["selma:evening", "can:evening"], "kiss, kissing, city lights, night wind", gap="large"),
    panel("medium", "l_shop", ["selma:evening", "can:evening"], "man giving small jewelry box, woman opening it, lamp light",
          [("selma", "Canu… tohle je z obchodní kolekce?"), ("can", "Dárek pro dobrou zákaznici.")]),
    panel("close-up", "l_shop", ["selma:evening"], "pained smile, holding necklace box, eyes glistening",
          [("selma", "Ta krabička má razítko vašeho zboží. A tohle zboží dáváte každé, která vám uvěří o Bosporu.")], gap="small"),
    panel("medium", "l_shop", ["selma"], "putting on coat, straightening earrings, cold expression, walking between carpets",
          [("selma", "Vy nechcete ostrov, Canu. Vy chcete prodej.")]),
    panel("wide", "l_shop", ["can:evening"], "sitting alone among carpets, head down, single lamp",
          [N("Bohatý na všechno. Kromě jedné věci.")], gap="large"),
])

# 5. Šumava — soft pastel ---------------------------------------------------------------------------
STORIES["rj_05_sumava"] = story(ending(world("w_rj_05_sumava", "Mlha na Šumavě",
    "Trenérka z města Vendula zabloudí v podzimním lese a najde ji tichý Jáchym z horské služby.", "hassaku_soft", [
    char("vendula", "Vendula Pospíšilová", "1girl", "adult, curvy, brown hair, braids, twin braids, rosy cheeks, brown eyes, smile",
         {"default": "brand new hiking boots, mustard puffer vest, plaid flannel shirt, beanie",
          "cabin": "oversized red plaid flannel shirt, thick wool socks, leggings, hair loose",
          "night": "oversized red plaid flannel shirt, wool blanket around shoulders"},
         "a Czech fitness trainer aged 28, curvy, brown twin braids, rosy cheeks"),
    char("jachym", "Jáchym Král", "1boy", "mature male, full beard, brown hair, brown eyes, calm, broad shoulders",
         {"default": "mountain rescue softshell jacket, cargo trousers, hiking boots, backpack", "cabin": "knit wool sweater, cargo trousers"},
         "a Czech mountain rescuer aged 34, full beard, softshell jacket"),
], [
    loc("l_forest", "Les", "outdoors, autumn forest, fog, golden leaves, signpost, moss, mushrooms, path"),
    loc("l_cabin", "Chata", "indoors, wooden cabin, fireplace, kettle, tea mugs, warm light, evening"),
    loc("l_bench", "Lavička před chatou", "outdoors, wooden bench, cabin porch, night, starry sky, thin fog, mugs"),
]), "Šťastný konec: výlet, který nekončí."), [
    panel("establishing", "l_forest", [], "fog between trees, golden leaves", [N("Šumava. Podzim.")]),
    panel("medium", "l_forest", ["vendula"], "holding map, looking at phone, confused, cold, standing at signpost",
          [("vendula", "Žádný signál. A boty jsou až moc nové.", "thought")]),
    panel("medium", "l_forest", ["jachym"], "walking out of fog, backpack, calm", [("jachym", "Ztracená?")], gap="small"),
    panel("medium", "l_forest", ["vendula", "jachym"], "facing each other, woman nervous smile, man faint smile",
          [("vendula", "Ne. Jen nevím, kde jsem. To je rozdíl."),
           ("jachym", "Jedna varianta končí v chatě s čajem. Druhá v záchraně."),
           ("vendula", "Tak tu s čajem.")]),
    panel("close-up", "l_forest", ["jachym"], "first smile, slight smile",
          [("jachym", "Medvědi tu nejsou. Jen ztracené fitness trenérky.")], gap="large"),
    panel("wide", "l_cabin", ["vendula:cabin", "jachym:cabin"], "woman sitting by fireplace, man making tea, back turned",
          [("vendula", "Celou hodinu mlčíte. Jako byste mlčel s někým.")]),
    panel("medium", "l_cabin", ["vendula:cabin", "jachym:cabin"], "handing mug of tea, fingers touching, warm light",
          [("jachym", "Večer tady mlčení znamená: jsem tady, mám čas a nechci být nikde jinde.")]),
    panel("close-up", "l_cabin", ["vendula:cabin"], "holding mug, soft expression, firelight",
          [("vendula", "Přijela jsem utéct. Od práce, od lidí, od jednoho muže."), ("jachym", "Já utéct nechci. Jen se nevracet sám.")], gap="large"),
    panel("medium", "l_bench", ["vendula:night", "jachym:cabin"], "sitting on bench under one blanket, stars",
          [("vendula", "Co když zjistím, že les byl jen krásný výlet, a ne začátek?"),
           ("jachym", "Tak výlet prodloužíme. Do pondělí. A pak celý život, jestli na mě najdeš čas.")]),
    panel("medium", "l_bench", ["vendula:night", "jachym:cabin"], "kiss, kissing, under blanket, starry night", gap="small"),
    panel("wide", "l_bench", [], "cabin door closed, warm window, two pairs of boots by the door, folded map, morning light",
          [N("Ráno u dveří stojí dvoje boty. A mapa, do které už nikdo nemusí koukat.")], gap="large"),
])

# 6. Maledivy — fast photoreal ----------------------------------------------------------------------
STORIES["rj_06_maledivy"] = story(ending(world("w_rj_06_maledivy", "Ostrov na Maledivách",
    "Vyhořelý investor Dominik se od potápěčské instruktorky Naii učí nebát se hloubky.", "photo_lightning", [
    char("dominik", "Dominik Vávrů", "1boy", "mature male, athletic, short hair, grey temples, brown hair, grey eyes, tired eyes",
         {"default": "white linen suit, open collar shirt, barefoot, sunglasses",
          "dive": "full black wetsuit zipped up, diving mask on forehead",
          "night": "white linen shirt open at collar, linen trousers, barefoot"},
         "a Czech investor aged 37, athletic, greying temples"),
    char("naia", "Naia Rahmani", "1girl", "adult, mature female, petite, tan skin, black hair, long hair, single braid, dark eyes, calm",
         {"default": "fully zipped long sleeve wetsuit, diving mask on forehead",
          "night": "flowing turquoise silk maxi dress, shell necklace, hair down"},
         "a Maldivian dive instructor aged 32, tanned, long black braid, fully zipped wetsuit"),
], [
    loc("l_jetty", "Molo", "outdoors, wooden jetty, turquoise water, palm trees, noon, white sand, private island"),
    loc("l_reef", "Útes", "outdoors, ocean surface, reef below, clear turquoise water, sunlight, heads above water"),
    loc("l_beach", "Pláž", "outdoors, beach, night, moonlight path on sea, resort lights in distance, sand"),
    loc("l_villa", "Vila", "outdoors, water villa, night, open door, sea breeze, curtains, lanterns"),
]), "Šťastný konec: Dominik zůstává na ostrově."), [
    panel("establishing", "l_jetty", [], "turquoise lagoon, palms, seaplane", [N("Maledivy. Soukromý ostrov.")]),
    panel("medium", "l_jetty", ["dominik"], "walking on jetty, barefoot, suit, sunglasses, tired face",
          [N("Uspěl ve všem. A ztratil všechno.")]),
    panel("medium", "l_jetty", ["dominik", "naia"], "woman greeting, mask on forehead, man taking off sunglasses",
          [("naia", "Vítejte. Jsem Naia. Potápění je jen plavání s důvěrou. Tu vám tady dáme."),
           ("naia", "Ale máte na sobě oblek. Tak spíš za dva dny.")]),
    panel("close-up", "l_jetty", ["naia"], "calm, serious, looking at viewer",
          [("naia", "Útěk před vlastním životem se na ostrově neschová. Voda vám ho ukáže.")], gap="large"),
    panel("medium", "l_reef", ["dominik:dive", "naia"], "floating at surface, masks pushed up, talking, sunlight",
          [("dominik", "Dvacet let jsem stavěl firmy. Nikdy jsem neviděl nic tak klidného."),
           ("naia", "Pod vodou se nedá lhát. Všechno je vidět. I to, před čím člověk utekl.")]),
    panel("close-up", "l_reef", ["dominik:dive"], "sad, wet hair, looking down",
          [("dominik", "Žena odešla před rokem. Utekl jsem do práce. Práce neodejde."), ("naia", "Ale ani neumí zůstat.")], gap="large"),
    panel("medium", "l_beach", ["dominik:night", "naia:night"], "sitting on sand, moonlight, facing each other",
          [("naia", "Za tři dny odjíždíte."), ("dominik", "Odjíždím. Ale ne z ostrova. Z života, který jsem měl.")]),
    panel("medium", "l_beach", ["dominik:night", "naia:night"], "holding hands, smile, moonlight",
          [("naia", "Investor, který se učí potápět. A když se to nenaučí?"),
           ("dominik", "Tak zůstane s průvodkyní, která ho drží nad vodou.")], gap="small"),
    panel("medium", "l_beach", ["dominik:night", "naia:night"], "kiss, kissing, embrace, moonlight, sea",
          [("naia", "Uč se. Celý život.")]),
    panel("wide", "l_villa", [], "villa door open to sea breeze, curtains moving, lanterns, moon",
          [N("Dveře zůstanou otevřené. Pro mořský vítr, jediného svědka.")], gap="small"),
    panel("medium", "l_jetty", ["dominik", "naia"], "morning, sitting on jetty edge, signed contract on lap, smiling, sunrise",
          [N("Ráno na molu leží smlouva podepsaná na poslední stránce.")], gap="large"),
])

# 7. Rio — webtoon with artist tags -------------------------------------------------------------------
STORIES["rj_07_rio"] = story(ending(world("w_rj_07_rio", "Copacabana",
    "Prodavač kokosů Thiago se ptá modelky Beatriz, proč je smutná, a ona neví, jak odpovědět.", "webtoon_romance_artist", [
    char("thiago", "Thiago Alves", "1boy", "mature male, athletic, curly hair, black hair, brown eyes, tan skin, bright smile",
         {"default": "yellow tank top over white t-shirt, denim shorts, sandals", "night": "white t-shirt, denim shorts, shell bracelet"},
         "a Brazilian coconut seller aged 29, curly black hair, white t-shirt and denim shorts"),
    char("beatriz", "Beatriz Lima", "1girl", "adult, tall female, long legs, very long hair, straight hair, black hair, brown eyes",
         {"default": "flowing coral maxi dress with high slit, oversized sunglasses, gold hoop earrings",
          "night": "flowing ivory chiffon maxi dress, gold hoop earrings, hair down"},
         "a tall Brazilian model aged 27, waist-length straight black hair, flowing coral maxi dress"),
], [
    loc("l_stand", "Stánek", "outdoors, copacabana beach, coconut stand, wave pattern promenade, afternoon, sea, palm trees"),
    loc("l_bar", "Bar na pláži", "outdoors, beach bar, night, string lights, caipirinha glasses, coconuts, samba"),
    loc("l_sand", "Prázdná pláž", "outdoors, empty beach, night, moonlight, city lights in distance, waves"),
]), "Hořký konec: Beatriz odletí, bar nikdy nevznikne."), [
    panel("establishing", "l_stand", [], "beach, football players, music", [N("Rio de Janeiro. Copacabana.")]),
    panel("medium", "l_stand", ["thiago"], "holding coconut, grin, calling out", [("thiago", "Kokosovou vodu pro anděla?")]),
    panel("medium", "l_stand", ["beatriz"], "walking, wind in dress, lowering sunglasses, small smile",
          [("beatriz", "To říkáte každé."), ("thiago", "Každé. Ale vám zadarmo.")], gap="small"),
    panel("medium", "l_stand", ["beatriz", "thiago"], "man handing two coconuts, woman taking them, looking at each other",
          [("beatriz", "Dejte mi dva. Jeden pro mě a jeden pro to, co mi chcete říct."),
           ("thiago", "Dva kokosy. A jedna otázka: proč jste smutná?")]),
    panel("close-up", "l_stand", ["beatriz"], "silent, looking at sea, sad eyes, wind",
          [N("Na módním týdnu se jí na to nikdo nezeptal.")], gap="large"),
    panel("wide", "l_bar", ["beatriz:night", "thiago:night"], "sitting at table, caipirinhas, string lights",
          [("beatriz", "Za tři dny São Paulo. Pak Milán. Pak New York. Móda je kolotoč a já se bojím vystoupit."),
           ("thiago", "A co byste dělala, kdybyste vystoupila?")]),
    panel("close-up", "l_bar", ["thiago:night"], "warm smile, string lights",
          [("thiago", "Prodávám kokosy. Ale sním o baru. A dneska i o ženě se smutnýma očima.")], gap="large"),
    panel("medium", "l_sand", ["beatriz:night", "thiago:night"], "kiss, kissing, moonlight, wind in hair", gap="small"),
    panel("medium", "l_sand", ["beatriz:night", "thiago:night"], "woman stepping back, hand on his chest, sad",
          [("beatriz", "Ve čtyři ráno letím. Mám smlouvu. Smlouvy jsou jako řetězy."), ("thiago", "Zůstaň.")]),
    panel("close-up", "l_sand", ["beatriz:night"], "tears, looking up, moonlight",
          [("beatriz", "Poprvé jsem se necítila jako modelka, ale jako žena. To mě děsí víc než celý Milán."),
           ("beatriz", "Nemůžu. Je mi to líto.")]),
    panel("wide", "l_sand", ["thiago:night"], "standing alone, holding two coconuts, empty beach, from behind",
          [N("Na písku zůstane jeden kokos, který nikdo nedopil.")], gap="large"),
])

# 8. Karlovy Vary — vintage poster ------------------------------------------------------------------
STORIES["rj_08_karlovyvary"] = story(ending(world("w_rj_08_karlovyvary", "Lázně v Karlových Varech",
    "Lékař Viktor přijel do lázní za klidem a švédská fyzioterapeutka Greta mu ho rozbije za pět minut.", "vintage_poster", [
    char("viktor", "Viktor Malý", "1boy", "mature male, tall, greying hair, short hair, thin-framed glasses, serious, clean shaven",
         {"default": "worn grey knit sweater, collared shirt, wool trousers, thin glasses",
          "coat": "camel wool overcoat, grey knit sweater, scarf"},
         "a Czech doctor aged 41, tall, greying hair, thin-framed glasses, worn grey sweater"),
    char("greta", "Greta Lindqvist", "1girl", "adult, curvy, sandy blonde hair, ponytail, blue eyes, confident smile",
         {"default": "fitted navy knit dress, open white trench coat, ankle boots",
          "spa": "white spa robe tied at waist, hair in high ponytail",
          "evening": "fitted burgundy knit dress, long cream coat, hair down"},
         "a Swedish physiotherapist aged 38, sandy blonde ponytail, fitted knit dress under an open trench coat"),
], [
    loc("l_colonnade", "Kolonáda", "outdoors, colonnade, spa town, karlovy vary, mist over river, morning, columns, hot spring fountain"),
    loc("l_spa", "Lázeňský dům", "indoors, spa hall, marble, steam, mineral pool, columns, warm light"),
    loc("l_river", "Pod vřídly", "outdoors, riverside promenade, night, lanterns, steam from hot spring, autumn leaves"),
]), "Šťastný konec: Viktor pojede do Stockholmu."), [
    panel("establishing", "l_colonnade", [], "colonnade, mist, steam", [N("Karlovy Vary. Kolonáda.")]),
    panel("medium", "l_colonnade", ["viktor"], "walking slowly, hands in pockets, looking at fountain, serious"),
    panel("medium", "l_colonnade", ["greta", "viktor"], "woman walking fast toward man, pointing, smile",
          [("greta", "Vy jste ten lékař, co kouká na fontánu, jako by ji chtěl operovat."),
           ("viktor", "A vy ta fyzioterapeutka, co běhá kolonádou, jako by ji honilo vlastní volno.")]),
    panel("close-up", "l_colonnade", ["greta"], "laughing, ponytail",
          [("greta", "Volno nesnáším. Volno znamená, že nejsem potřeba.")], gap="large"),
    panel("medium", "l_spa", ["viktor", "greta:spa"], "man sitting at pool edge, woman in robe sitting next to him, steam",
          [("viktor", "Nebojím se vody. Bojím se klidu. V klidu se ozvou věci, které odkládám.")]),
    panel("close-up", "l_spa", ["viktor"], "looking down, glasses fogged, sad",
          [("viktor", "Manželství, které skončilo. Syn, který píše jednou za tři měsíce. A kdo jsem, když nejsem doktor?")], gap="small"),
    panel("close-up", "l_spa", ["greta:spa"], "gentle, attentive, steam",
          [("greta", "Tělo nelže. Tak mi řekněte: co cítíte?"), ("viktor", "Že poprvé za deset let nechci být večer sám.")], gap="large"),
    panel("wide", "l_river", ["viktor:coat", "greta:evening"], "walking hand in hand, lanterns, steam",
          [("greta", "Za týden odjíždím do Stockholmu. Mám život naplánovaný na dva roky dopředu.")]),
    panel("medium", "l_river", ["viktor:coat", "greta:evening"], "man turning her to face him, lantern light",
          [("viktor", "Nechci slyšet „můžeme si psát“. Chci slyšet pravdu."),
           ("greta", "Do toho plánu se právě vešel jeden doktor z Karlových Varů. A nevím, co s tím.")]),
    panel("medium", "l_river", ["viktor:coat", "greta:evening"], "kiss, kissing, steam, lanterns, then both laughing",
          [("viktor", "Nepředepisujte léčbu. Nechte to hojení na čase.")], gap="small"),
    panel("wide", "l_colonnade", [], "morning, porch of spa house, two cups on table, train timetable with underlined line",
          [N("Ráno na zápraží dva hrnky. A jízdní řád s podtrženým vlakem do Stockholmu.")], gap="large"),
])

# 9. Toskánsko — flat anime ------------------------------------------------------------------------
STORIES["rj_09_toskansko"] = story(ending(world("w_rj_09_toskansko", "Kola v Toskánsku",
    "Hana přijela s předsevzetím zamilovat se jen do sebe a cykloprůvodce Marco ho zkouší rozbít.", "flat_anime_mema", [
    char("marco", "Marco Gianelli", "1boy", "mature male, tan skin, black hair, ponytail, long hair, brown eyes, white teeth, bright smile, athletic",
         {"default": "white cycling jersey, black cycling shorts, cycling gloves, sunglasses on head",
          "lunch": "white linen shirt, rolled sleeves, khaki shorts"},
         "an Italian cycling guide aged 34, tanned, black hair in a ponytail, white cycling jersey"),
    char("hana", "Hana Kolářová", "1girl", "adult, athletic, brown hair, braid, single braid, hazel eyes, serious",
         {"default": "teal cycling jacket, cycling helmet, black leggings, sneakers",
          "lunch": "white sleeveless linen top, olive wide-leg trousers, sunglasses, braid"},
         "a Czech athlete aged 30, brown braid, sporty, teal cycling jacket"),
], [
    loc("l_vineyard", "Vinice", "outdoors, tuscany, vineyard, rolling hills, cypress trees, morning mist, bicycles, golden light"),
    loc("l_lunch", "Oběd pod dubem", "outdoors, long table under old oak tree, wine glasses, pasta, vineyard, noon, sunlight"),
    loc("l_hill", "Kopec", "outdoors, hilltop, sunset, long shadows, vineyard below, orange sky, bicycles"),
]), "Hořký konec: Hana odjede, Marco čeká další skupina."), [
    panel("establishing", "l_vineyard", [], "golden hills, mist, cypresses", [N("Toskánsko.")]),
    panel("medium", "l_vineyard", ["marco"], "standing by bicycles, arms open, bright smile",
          [("marco", "Signora Hana! Dvacet kilometrů, tři kopce a oběd, na který se nezapomíná.")]),
    panel("medium", "l_vineyard", ["hana"], "putting on helmet, skeptical, raised eyebrow",
          [("hana", "A průvodce, na kterého se nezapomíná? Slyšela jsem. Každá skupina má jednu, co vám na týden uvěří.")]),
    panel("close-up", "l_vineyard", ["marco"], "grin, playful",
          [("marco", "A každá skupina má jednu, co se mi snaží nesmát. Ta je vždycky nejzajímavější.")], gap="large"),
    panel("wide", "l_lunch", ["hana:lunch", "marco:lunch"], "sitting at long table alone, wine, cicadas",
          [("hana", "Mám jeden slib: zamiluju se jen do sebe. Žádné „ciao bella“, žádné loučení na letišti.")]),
    panel("close-up", "l_lunch", ["marco:lunch"], "serious, no smile",
          [("marco", "Poznám, kdy se žena směje doopravdy. Vy jste se smála třikrát. Naposledy teď, když jste řekla, že se nezamilujete.")]),
    panel("close-up", "l_lunch", ["hana:lunch"], "blush, wine glass trembling, flustered", [("hana", "To není fér.")], gap="large"),
    panel("medium", "l_hill", ["hana", "marco"], "kiss, kissing, sunset, bicycles", gap="small"),
    panel("medium", "l_hill", ["hana", "marco"], "woman pulling away, breathing hard, hand raised",
          [("hana", "Loni jsem tady podlehla jinému průvodci. V listopadu napsal, že má přítelkyni. Řekla jsem si: už nikdy.")]),
    panel("medium", "l_hill", ["hana", "marco"], "woman zipping up jacket, man pained",
          [("marco", "To není matematika. To je strach, kterému říkáte rozum."),
           ("hana", "Možná. Ale rozum je jediné, co mě drží na kole.")]),
    panel("wide", "l_hill", ["marco"], "standing alone beside bicycle, sunset, woman cycling away in distance",
          [N("V každé další skupině bude jedna, která se mu pokusí nesmát.")], gap="large"),
])

# 10. Seychely — 3D cinematic ---------------------------------------------------------------------
STORIES["rj_10_seychely"] = story(ending(world("w_rj_10_seychely", "Kuchař a architektka",
    "Architektka Freja přijela navrhnout kuchyň resortu a šéfkuchař Elias jí ukáže, co se navrhnout nedá.", "anime_screencap", [
    char("elias", "Elias Mwangi", "1boy", "mature male, dark-skinned male, dark skin, muscular, short hair, black hair, brown eyes, warm smile",
         {"default": "crisp white chef jacket, black trousers, chef apron", "evening": "white linen shirt, beige trousers"},
         "a Kenyan head chef aged 33, muscular, short hair, crisp white chef jacket"),
    char("freja", "Freja Sørensen", "1girl", "adult, tall female, slender, very short hair, platinum blonde hair, pixie cut, blue eyes",
         {"default": "black sleeveless jumpsuit, minimalist silver jewelry, tablet in hand",
          "evening": "white silk slip dress over white t-shirt, silver cuff, barefoot",
          "night": "long white linen shirt dress, silver cuff, chef jacket over shoulders"},
         "a tall slender Danish architect aged 29, platinum pixie cut, icy blue eyes, black jumpsuit"),
], [
    loc("l_kitchen", "Kuchyně resortu", "indoors, open kitchen, resort, spices, pots, window, ocean view, afternoon"),
    loc("l_rocks", "Pláž s balvany", "outdoors, la digue, granite boulders, turquoise sea, beach, sunset, blanket, plates of food"),
    loc("l_terrace", "Terasa", "outdoors, terrace, granite boulders, night, moon over ocean, waves, lantern"),
]), "Šťastný konec: Freja zůstane a v plánu přibude okno na moře."), [
    panel("establishing", "l_kitchen", [], "open kitchen, steam, ocean beyond window", [N("Seychely, La Digue.")]),
    panel("medium", "l_kitchen", ["freja"], "holding tablet, professional, cool expression",
          [("freja", "Vy jste šéfkuchař. Mám tu tři problémy s projektem vaší nové kuchyně.")]),
    panel("medium", "l_kitchen", ["elias"], "cooking at stove, not turning, smiling",
          [("elias", "A já tři s tím vaším. Všechno krásné, ale není tam místo pro lidi. Kuchyň má mít okno na moře.")], gap="small"),
    panel("medium", "l_kitchen", ["freja", "elias"], "man offering spoon with sauce, woman tasting, surprised",
          [("elias", "Ochutnejte. Tohle je chutná kritika."), ("freja", "To je nejlepší věc, co jsem tady měla.")]),
    panel("close-up", "l_kitchen", ["elias"], "grin", [("elias", "Pak máte o tři problémy méně.")], gap="large"),
    panel("wide", "l_rocks", ["freja:evening", "elias:evening"], "sitting on blanket among boulders, plates of fish and mango, sunset",
          [("freja", "Umím navrhnout dokonalý pokoj. Ale nedokázala bych říct, co dělá místo domovem."),
           ("elias", "Chutě. Vůně. Lidi, co tam vaří. Bez nich je to jen krabice.")]),
    panel("close-up", "l_rocks", ["freja:evening"], "warm eyes, soft smile, sunset light",
          [("elias", "Já lidi krmím, vy jim stavíte střechu. Stejná práce. Já chutí, vy betonem.")], gap="large"),
    panel("medium", "l_terrace", ["freja:night", "elias:evening"], "facing each other, foreheads touching, moonlight",
          [("freja", "Bojím se, že si to budu pamatovat jako návrh. Ne jako život."),
           ("elias", "Tak nech navrhnout život. Já přidám chuť, ty linku.")]),
    panel("medium", "l_terrace", ["freja:night", "elias:evening"], "kiss, kissing, moonlight, ocean", gap="small"),
    panel("wide", "l_terrace", [], "lantern going out, house door closed, moon over ocean, waves on granite",
          [N("Oceán dýchá dál. Nic neprozradí.")], gap="small"),
    panel("medium", "l_terrace", ["freja", "elias"], "morning, two coffee cups, tablet with pencil line drawn across plan, smiling",
          [N("Ráno je v plánu nová čára tužkou: okno na moře.")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
