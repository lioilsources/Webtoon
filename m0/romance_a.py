"""Romance set A — ten harlequin stories ("Zde je kolekce 10 romantických příběhů v harlequinském stylu…").

    python3 m0/romance_a.py        → data/stories/ra_*/{world,storyboard}.json

Same building blocks and rules as stories_romance.py: one medium per story, dialogue verbatim (typos fixed),
inner monologue as thought bubbles, never two characters of the same gender in one panel.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}

# 1. New York — fast photoreal -------------------------------------------------------------------
STORIES["ra_01_ny"] = story(world("w_ra_01_ny", "Nečekaná inspirace v Manhattanu",
    "Nina si v New Yorku připadá neviditelná, dokud ji v kavárně v SoHo nezachytí Julian.", "photo_lightning", [
    char("nina", "Nina Sanchez", "1girl", "adult, short stature, curvy, wide hips, tan skin, long hair, wavy hair, dark brown hair, brown eyes",
         "oversized sweater, knit sweater, skinny jeans, sneakers",
         "a petite curvy Puerto Rican woman aged 25, long dark wavy hair, warm brown eyes"),
    char("julian", "Julian Vane", "1boy", "mature male, tall, athletic, slender, sharp jawline, short hair, light brown hair, blue eyes",
         "navy suit, tailored suit, white shirt, no necktie, wristwatch",
         "a tall athletic American man aged 32, sharp-featured face, short light brown hair, tailored navy suit"),
], [
    loc("l_fifth", "Pátá Avenue", "outdoors, fifth avenue, new york, rain, umbrellas, yellow taxi, crowd, boutique, shop window, mannequins, overcast"),
    loc("l_cafe", "Kavárna v SoHo", "indoors, cafe, soho, coffee, raindrops on window, warm light, wooden table, laptop"),
]), [
    panel("establishing", "l_fifth", [], "rain, crowd with umbrellas, yellow taxi, traffic", [N("Pátá Avenue. Prší.")]),
    panel("wide", "l_fifth", ["nina"], "standing in front of shop window, looking at mannequins, from side, rain, sad"),
    panel("medium", "l_fifth", ["nina"], "adjusting sweater, sigh, looking down, reflection in window",
          [("nina", "Městské dívky z obálek časopisů...", "thought"),
           ("nina", "Já v tomhle městě plném modelek splývám s šedivým chodníkem.", "thought")], gap="large"),
    panel("wide", "l_cafe", ["nina"], "carrying paper cup, tripping, stumbling, falling forward, surprised",
          [N("Útulná kavárnička v SoHo.")], gap="small"),
    panel("medium", "l_cafe", ["nina", "julian"], "man catching woman, hand on waist, faces close, looking at each other, blush",
          [("julian", "Opatrně... Měl bych obrovskou škodu, kdyby se tak krásné dámě něco stalo.")]),
    panel("close-up", "l_cafe", ["nina"], "blush, flustered, embarrassed, looking away",
          [("nina", "Krásné? Já... já jsem spíš jen nešikovná.")], gap="small"),
    panel("close-up", "l_cafe", ["julian"], "gentle smile, looking at viewer",
          [("julian", "Někdy ten nejhezčí moment dne přichází bez varování.")]),
    panel("medium", "l_cafe", ["nina", "julian"], "man still holding her, smile, warm light, rain on window",
          [("julian", "Dovolíte mi koupit vám novou kávu a sednout si k vám?")], gap="small"),
    panel("medium", "l_cafe", ["nina", "julian"], "sitting at table, two coffee cups, smiling at each other, blush", gap="large"),
])

# 2. Paříž — art nouveau ---------------------------------------------------------------------------
STORIES["ra_02_pariz"] = story(world("w_ra_02_pariz", "Pod pařížskými lucernami",
    "Klára hledá v Paříži múzu, vítr jí odnese baret k botám mechanika Jean-Luca.", "art_nouveau_mucha", [
    char("klara", "Klára Dvořáková", "1girl", "adult, tall female, very slender, small breasts, blonde hair, long hair, blue eyes, delicate features",
         {"default": "beret, cream trench coat, red scarf", "nobaret": "cream trench coat, red scarf"},
         "a tall very slender Czech woman aged 22, long blonde hair, delicate features, beret and cream trench coat"),
    char("jeanluc", "Jean-Luc Moreau", "1boy", "mature male, dark-skinned male, dark skin, muscular, curly hair, messy hair, black hair, brown eyes",
         "black leather jacket, dark t-shirt, boots, oil stains",
         "a muscular French mechanic aged 28 with dark skin and wild black curly hair, leather jacket"),
], [
    loc("l_seine", "Nábřeží Seiny", "outdoors, seine, riverbank, street lamps, lamppost, eiffel tower, evening, bookstalls, paintings, city lights"),
    loc("l_square", "Montmartre", "outdoors, montmartre, small square, cobblestone, vintage car, open hood, cafe, evening, warm light"),
]), [
    panel("establishing", "l_seine", [], "street lamps, eiffel tower, evening, couples in distance", [N("Večerní nábřeží Seiny.")]),
    panel("wide", "l_seine", ["klara"], "walking, hugging own arms, looking at couples, painting stall"),
    panel("close-up", "l_seine", ["klara"], "sigh, sad, looking away",
          [("klara", "Všichni tu vypadají jako z romantického filmu. A já si připadám jako přerostlý věšák na kabáty...", "thought")]),
    panel("medium", "l_seine", ["klara"], "looking up at sky, wistful", [("klara", "Kde je moje múza?", "thought")], gap="large"),
    panel("wide", "l_square", ["jeanluc"], "emerging from under car hood, vintage car, wiping hand, oil stains", [N("Montmartre.")]),
    panel("medium", "l_square", ["klara:nobaret"], "wind, hair blowing, reaching out, surprised, beret flying away", gap="small"),
    panel("medium", "l_square", ["jeanluc"], "holding beret, smile, charmed",
          [("jeanluc", "Pardon, mademoiselle... Myslím, že vám vítr seslal z nebe něco, co patří nejvznešenější dámě v Paříži.")]),
    panel("medium", "l_square", ["klara:nobaret", "jeanluc"], "man handing beret, woman looking down, blush",
          [("klara", "Děkuji... Ale nemusíte přehánět. Jsem jen obyčejná vysoká holka.")]),
    panel("close-up", "l_square", ["klara:nobaret", "jeanluc"], "holding hands, man gently holding her hand, looking at each other",
          [("jeanluc", "Obyčejná? Vaše elegance bere dech.")], gap="small"),
    panel("medium", "l_square", ["klara", "jeanluc"], "walking together, smile, bistro sign, warm light",
          [("jeanluc", "Pojďte, nedaleko je malé bistro. Dlužíte mi rozečtený rozhovor za záchranu vašeho klobouku.")], gap="large"),
])

# 3. Havana — analogue film --------------------------------------------------------------------------
STORIES["ra_03_havana"] = story(world("w_ra_03_havana", "Karibské rytmy",
    "Bea by chtěla být v Havaně neviditelná, tanečník Manny ji vytáhne doprostřed náměstí.", "photo_realvis_film", [
    char("bea", "Beatrice „Bea“ Sullivan", "1girl", "adult, red hair, long hair, wavy hair, freckles, green eyes, pale skin, large breasts",
         "floral dress, summer dress, straw hat",
         "an Irish woman aged 27 with vivid long red hair, freckles, pale skin, curvy figure"),
    char("manny", "Manuel „Manny“ Cruz", "1boy", "mature male, tall, lean, athletic, tan skin, very short hair, black hair, brown eyes, bright smile",
         "white linen shirt, partially unbuttoned shirt, linen pants, sandals",
         "a tall lean athletic Cuban dancer aged 30, tanned skin, close-cropped black hair, radiant smile"),
    char("baptista", "Baptišta", "1boy", "old man, dark skin, grey hair, grey beard, wrinkles", "guayabera, straw fedora, acoustic guitar",
         "an old Cuban street guitarist with a grey beard and straw fedora"),
], [
    loc("l_street", "Stará Havana", "outdoors, old havana, narrow street, colorful buildings, peeling paint, vintage car, sunlight, laundry"),
    loc("l_plaza", "Náměstí u katedrály", "outdoors, small plaza, old cathedral, live band, crowd, dancing, evening, warm light, string lights"),
]), [
    panel("establishing", "l_street", [], "colorful buildings, vintage car, music", [N("Stará Havana. Odevšad zní rumba a salsa.")]),
    panel("wide", "l_street", ["bea"], "walking, people turning heads, embarrassed, hand on chest, holding hat"),
    panel("close-up", "l_street", ["bea"], "sigh, embarrassed, looking down",
          [("bea", "Proč musím všude tak svítit? Zrzavé vlasy, postava, kterou nepřehlédneš...", "thought")], gap="small"),
    panel("medium", "l_street", ["bea"], "looking up, wistful, sad smile",
          [("bea", "Přála bych si být pro jednou neviditelná.", "thought")], gap="large"),
    panel("medium", "l_plaza", ["baptista"], "playing guitar, smile, closed eyes", [N("Náměstíčko před starou katedrálou.")], gap="small"),
    panel("wide", "l_plaza", ["manny"], "dancing, salsa, crowd, dynamic pose, smile"),
    panel("medium", "l_plaza", ["bea", "manny"], "man bowing, offering hand, woman standing aside, surprised",
          [("manny", "Krásná seňorita tu stojí sama? V Havaně se na hudbu nesmutní. Smím prosit?")]),
    panel("medium", "l_plaza", ["bea"], "stepping back, nervous, hand on chest, blush",
          [("bea", "Já... já neumím tancovat. A všichni se budou dívat.")]),
    panel("medium", "l_plaza", ["bea", "manny"], "man holding her hand, pulling her close, faces close, looking at each other",
          [("manny", "Ať se dívají. Bude to tím, že v celém městě není nikdo tak nádherný jako vy.")], gap="small"),
    panel("wide", "l_plaza", ["bea", "manny"], "dancing together, salsa, twirling, laughing, dress flowing",
          [("manny", "Věřte mi, chytím vás.")], gap="large"),
])

# 4. Londýn — pastel shoujo --------------------------------------------------------------------------
STORIES["ra_04_londyn"] = story(world("w_ra_04_londyn", "Londýnský déšť a horký čaj",
    "Drobná Mayumi a obří texaský kovboj Jack v londýnské čajovně.", "pastel_shoujo", [
    char("mayumi", "Mayumi Tanaka", "1girl", "adult, japanese, petite, short stature, slender, wide hips, long hair, straight hair, black hair, blunt bangs, brown eyes",
         "dark green coat, thick scarf, ankle boots",
         "a very petite Japanese woman aged 24, straight black hair with blunt bangs, slim with curvy hips"),
    char("jack", "Jack „Jackson“ Reed", "1boy", "mature male, very tall, broad shoulders, thick beard, sandy blonde hair, blue eyes",
         {"default": "denim jacket, sherpa collar, cowboy hat, leather boots", "hatless": "denim jacket, sherpa collar, holding cowboy hat"},
         "a very tall broad-shouldered Texan cowboy aged 35, thick beard, sandy blond hair, denim jacket with sherpa collar"),
], [
    loc("l_station", "St. Pancras", "indoors, st pancras station, train station, victorian architecture, glass roof, iron arches, rain, crowd"),
    loc("l_tea", "Čajovna", "indoors, tea room, wooden furniture, fireplace, teapot, teacup, flower vase, raindrops on window, warm light"),
]), [
    panel("establishing", "l_station", [], "glass roof, iron arches, rain", [N("Nádraží St. Pancras. Venku leje jako z konve.")]),
    panel("wide", "l_station", ["mayumi"], "pulling huge suitcase, oversized suitcase, struggling, tired"),
    panel("medium", "l_station", ["mayumi"], "out of breath, sweatdrop, holding suitcase handle",
          [("mayumi", "Proč jsem si nabalila tolik věcí?", "thought")], gap="small"),
    panel("close-up", "l_station", ["mayumi"], "sad, lonely, looking down",
          [("mayumi", "Jsem tu tak ztracená... Malá holka ve velkém městě.", "thought")], gap="large"),
    panel("medium", "l_tea", ["mayumi"], "sitting at table, stirring tea, teacup, quiet", [N("Tradiční londýnská čajovna.")]),
    panel("medium", "l_tea", ["jack"], "sitting down, cowboy hat bumping flower vase, vase tipping, surprised", gap="small"),
    panel("medium", "l_tea", ["jack:hatless"], "taking off hat, apologizing, embarrassed",
          [("jack", "Proboha, ma'am, moc se omlouvám! Jsem v tomhle městě velký jako slon v porcelánu.")]),
    panel("close-up", "l_tea", ["mayumi"], "small smile, shy, looking up",
          [("mayumi", "To nic není... Já si tu zase připadám tak malá, že mě lidé přehlížejí.")]),
    panel("medium", "l_tea", ["mayumi", "jack:hatless"], "sitting at same table, height difference, gentle gaze, teacups, fireplace",
          [("jack", "Přehlédnout někoho s tak kouzelným úsměvem? To by musel být člověk slepý.")], gap="small"),
    panel("medium", "l_tea", ["mayumi", "jack:hatless"], "smiling at each other, blush, rain on window, warm light",
          [("jack", "Mohu vám nabídnout společnost, než venku přestane pršet?")], gap="large"),
])

# 5. Nairobi — oil painting ----------------------------------------------------------------------------
STORIES["ra_05_nairobi"] = story(world("w_ra_05_nairobi", "Safari srdce",
    "Amara si připadá málo ženská, boxer Marcus ji vidí jako gazelu na obzoru.", "painterly_oil", [
    char("amara", "Amara Diop", "1girl", "adult, dark-skinned female, very dark skin, tall female, athletic, small breasts, very short hair, curly hair, black hair, brown eyes",
         "khaki safari shorts, white tank top, sun hat",
         "a tall athletic Afro-French woman aged 26, very dark skin, short cropped black curls, safari shorts"),
    char("marcus", "Marcus Vance", "1boy", "mature male, dark-skinned male, dark skin, very muscular, huge, scar, scars on arms, buzz cut, black hair, brown eyes",
         "olive t-shirt, cargo pants",
         "a huge heavyweight American boxer aged 31, brown skin, buzz cut, scarred forearms, gentle eyes"),
], [
    loc("l_savanna", "Savana", "outdoors, savanna, nairobi national park, safari jeep, elephants in distance, sunset, orange sky, purple sky"),
    loc("l_camp", "Kemp pod akácií", "outdoors, campsite, acacia tree, campfire, tent, dusk, savanna, sunset"),
]), [
    panel("establishing", "l_savanna", [], "elephants, sunset, acacia tree", [N("Národní park u Nairobi. Západ slunce.")]),
    panel("wide", "l_savanna", ["amara"], "standing by jeep, looking through binoculars, elephants"),
    panel("medium", "l_savanna", ["amara"], "stretching, looking down at self, sigh, sad",
          [("amara", "Vypadám spíš jako atletický chlapec než jako žena, která by někoho okouzlila...", "thought")], gap="small"),
    panel("close-up", "l_savanna", ["amara"], "melancholy, looking at sunset", [("amara", "Láska je pro jiné.", "thought")], gap="large"),
    panel("wide", "l_camp", ["amara", "marcus"], "man walking toward woman, holding two mugs, campfire", [N("Kemp pod akácií.")]),
    panel("close-up", "l_camp", ["amara", "marcus"], "handing mug, hands touching, big hand, small hand, steam", gap="small"),
    panel("medium", "l_camp", ["marcus"], "gentle look, soft smile, holding mug",
          [("marcus", "Sleduji tě celý den. Máš v sobě takovou sílu a vznešenost... Připomínáš mi gazelu na obzoru.")]),
    panel("close-up", "l_camp", ["amara"], "surprised, blinking, holding mug, blush",
          [("amara", "Já? Myslela jsem, že boxerskému šampionovi se líbí úplně jiné typy žen.")]),
    panel("medium", "l_camp", ["amara", "marcus"], "hand on her shoulder, standing close, looking at each other, sunset",
          [("marcus", "Když strávíš život v ringu, naučíš se poznat pravou krásu a ryzost.")], gap="small"),
    panel("close-up", "l_camp", ["amara", "marcus"], "faces close, smile, blush, sunset glow",
          [("marcus", "A ty jsi ta nejkrásnější žena, jakou jsem kdy potkal.")], gap="large"),
])

# 6. Praha — film noir mono ---------------------------------------------------------------------------
STORIES["ra_06_praha"] = story(world("w_ra_06_praha", "Pražské zrcadlení",
    "Moravský kovboj Viktor zachrání na Karlově mostě skicák Rumunky Eleny.", "noir_mono", [
    char("viktor", "Viktor Kraus", "1boy", "mature male, tall, muscular, grey hair, short hair, stubble, wrinkles",
         "leather coat, long coat, cowboy boots",
         "a tall muscular Moravian ranch cowboy aged 42, greying hair, wrinkles around the eyes, long leather coat"),
    char("elena", "Elena Popescu", "1girl", "adult, short stature, curvy, wide hips, black hair, thick hair, hair bun, brown eyes",
         "knit turtleneck, long skirt, tote bag",
         "a petite curvy Romanian woman aged 29, thick dark hair in a bun, knit turtleneck and long skirt"),
], [
    loc("l_bridge", "Karlův most", "outdoors, charles bridge, prague, morning, fog, mist, statues, prague castle, stone railing"),
    loc("l_statue", "U sochy", "outdoors, charles bridge, baroque statue, cobblestone, fog, papers on ground, wind"),
]), [
    panel("establishing", "l_bridge", [], "fog, statues, prague castle silhouette", [N("Karlův most zahalený do ranní mlhy.")]),
    panel("wide", "l_bridge", ["viktor"], "walking, holding coffee cup, alone, fog"),
    panel("medium", "l_bridge", ["viktor"], "leaning on stone railing, holding coffee cup, looking at river, melancholy",
          [("viktor", "Stovky lidí a já tu chodím sám...", "thought")], gap="small"),
    panel("close-up", "l_bridge", ["viktor"], "wry smile, looking down",
          [("viktor", "Starý kovboj, co patří spíš do stájí než do téhle historické nádhery.", "thought")], gap="large"),
    panel("wide", "l_statue", ["elena"], "papers flying, drawings scattered, wind, running, reaching out", [N("U sochy svaté Luitgardy.")]),
    panel("medium", "l_statue", ["viktor"], "stepping on paper, crouching, picking up drawings", gap="small"),
    panel("medium", "l_statue", ["elena", "viktor"], "man handing papers, woman out of breath, smile",
          [("elena", "Děkuji vám! To jsou všechny mé návrhy... Jste můj zachránce!")]),
    panel("close-up", "l_statue", ["viktor"], "shy, gentle, looking away",
          [("viktor", "Rádo se stalo, slečno. Jen jsem nechtěl, aby takové krásné umění skončilo ve Vltavě.")]),
    panel("close-up", "l_statue", ["elena", "viktor"], "woman holding his rough hand, looking into his eyes",
          [("elena", "Máte oči plné příběhů...")], gap="small"),
    panel("medium", "l_statue", ["elena", "viktor"], "smile, looking at each other, fog, sunbeam",
          [("elena", "Smím si vás nakreslit? Třeba u horké čokolády v kavárně za rohem?")], gap="large"),
])

# 7. Miami — western comic ------------------------------------------------------------------------------
STORIES["ra_07_miami"] = story(world("w_ra_07_miami", "Anděl z pláže South Beach",
    "Bledý kancelářský Lucas pomůže běžkyni Camile z písku.", "western_comic", [
    char("lucas", "Lucas Carter", "1boy", "mature male, pale skin, slender, glasses, black-framed eyewear, short hair, brown hair, brown eyes",
         "white shirt, sleeves rolled up, khaki shorts",
         "a pale slender young American office worker aged 23, dark-framed glasses, short brown hair"),
    char("camila", "Camila Silva", "1girl", "adult, tall female, long legs, athletic, tan skin, blonde hair, long hair, ponytail, brown eyes",
         "athletic tank top, running shorts, sneakers",
         "a tall athletic Brazilian runner aged 26, long blond hair in a ponytail, tanned skin"),
], [
    loc("l_ocean", "Ocean Drive", "outdoors, ocean drive, miami, palm trees, art deco, buildings, roller skates, sunny, blue sky, bench"),
    loc("l_beach", "Pláž", "outdoors, beach, white sand, driftwood, ocean, waves, sunny"),
]), [
    panel("establishing", "l_ocean", [], "art deco buildings, palm trees, people roller skating", [N("Ocean Drive, Miami.")]),
    panel("wide", "l_ocean", ["lucas"], "sitting on bench, adjusting glasses, watching people, sad"),
    panel("close-up", "l_ocean", ["lucas"], "sigh, pushing up glasses, melancholy",
          [("lucas", "Celé dny trávím u počítače.", "thought")], gap="small"),
    panel("medium", "l_ocean", ["lucas"], "slouching on bench, looking down",
          [("lucas", "V tomhle městě plném slunce a dokonale opálených lidí jsem jako duch z jiné planety.", "thought")], gap="large"),
    panel("wide", "l_beach", ["camila"], "running, tripping over driftwood, falling, motion lines", gap="small"),
    panel("medium", "l_beach", ["camila", "lucas"], "man running to help, kneeling, woman sitting on sand, concerned",
          [("lucas", "Jste v pořádku? Nenařízla jste si nohu?")]),
    panel("medium", "l_beach", ["camila"], "sitting on sand, smile, brushing sand off knee",
          [("camila", "Jen trocha písku! Ale děkuji... Vy jste tak pozorný.")]),
    panel("close-up", "l_beach", ["camila"], "warm smile, laughing",
          [("camila", "Většina kluků tady jen předvádí bicepsy a ani by si nevšimla.")], gap="small"),
    panel("close-up", "l_beach", ["lucas"], "blush, embarrassed, looking away",
          [("lucas", "Já nejsem žádný sportovec... Jen obyčejný klučina z kanceláře.")]),
    panel("medium", "l_beach", ["camila", "lucas"], "standing up, woman holding his hand, warm smile, ocean",
          [("camila", "Právě proto jste výjimečný. Pojďte, pozvu vás na čerstvý kokosový džus jako poděkování!")], gap="large"),
])

# 8. Šanghaj — ink wash ------------------------------------------------------------------------------------
STORIES["ra_08_sanghaj"] = story(world("w_ra_08_sanghaj", "Ztraceni v zahradě Yuyuan",
    "Bývalý boxer David chytí v zahradě Yuyuan šátek, který Mei-Ling spadl do jezírka.", "ink_wash", [
    char("david", "David Miller", "1boy", "mature male, very tall, broad shoulders, muscular, crooked nose, scar, short hair, brown hair",
         "dark t-shirt, denim jacket, jeans",
         "a very tall broad-shouldered American former heavyweight boxer aged 38, slightly crooked nose, short haircut, denim jacket"),
    char("meiling", "Mei-Ling Chen", "1girl", "adult, chinese, petite, slender, small breasts, long hair, straight hair, black hair, brown eyes, gentle smile",
         {"default": "modern qipao, silk scarf", "noscarf": "modern qipao"},
         "a petite Chinese woman aged 25, long straight black hair, gentle smile, modern qipao"),
], [
    loc("l_garden", "Zahrada Yuyuan", "outdoors, yuyuan garden, chinese garden, stone bridge, red pavilion, pond, koi, ornate roof, east asian architecture"),
    loc("l_pond", "Most devíti zatáček", "outdoors, zigzag bridge, pond, koi, paper lantern, lantern light, dusk, chinese architecture"),
]), [
    panel("establishing", "l_garden", [], "red pavilion, stone bridge, koi pond", [N("Zahrada Yuyuan, Šanghaj.")]),
    panel("wide", "l_garden", ["david"], "ducking under low roof, bending, narrow alley, too tall"),
    panel("medium", "l_garden", ["david"], "whispering, sad, looking at tourists",
          [("david", "Jsem tu jako medvěd v bambusovém lese... Vypadám strašidelně, lidé ze mě mají respekt.", "thought")], gap="small"),
    panel("close-up", "l_garden", ["david"], "lonely, looking away",
          [("david", "Kde bych tady našel někoho, kdo by se mě nezalekl?", "thought")], gap="large"),
    panel("wide", "l_pond", ["meiling"], "leaning over water, feeding fish, koi, lanterns, scarf falling into water",
          [N("Most devíti zatáček.")]),
    panel("medium", "l_pond", ["david"], "reaching out long arm, catching scarf, splash", gap="small"),
    panel("medium", "l_pond", ["meiling:noscarf"], "clasped hands on chest, surprised, smile",
          [("meiling", "Ó, děkuji vám! Máte tak rychlé reflexy!")]),
    panel("medium", "l_pond", ["meiling:noscarf", "david"], "man handing wet scarf, embarrassed, height difference",
          [("david", "Pardon... Jsem starý boxer. Reflexy mi zůstaly, i když vizáž mám spíš jako zápasník.")]),
    panel("close-up", "l_pond", ["meiling:noscarf", "david"], "woman holding his sleeve, looking up into his eyes, admiration, lanterns",
          [("meiling", "Pod tou drsnou slupkou vidím velmi jemné a dobré srdce.")], gap="small"),
    panel("medium", "l_pond", ["meiling:noscarf", "david"], "walking together, lanterns, smile",
          [("meiling", "Smím vám ukázat ty nejkrásnější čajovny v zahradě?")], gap="large"),
])

# 9. Jamajka — vintage poster -------------------------------------------------------------------------------
STORIES["ra_09_jamajka"] = story(world("w_ra_09_jamajka", "Záře nad tropickým rájem",
    "Bankéř Alex po rozvodu nevěří na romantiku, dokud mu v horské kavárně nepadne do náruče Zara.", "vintage_poster", [
    char("alex", "Alexander „Alex“ Bishop", "1boy", "mature male, blonde hair, grey hair, short hair, glasses, blue eyes",
         "linen shirt, light pants",
         "an elegant American banker aged 40, light blond hair greying at the temples, glasses, linen shirt"),
    char("zara", "Zara Jackson", "1girl", "adult, dark-skinned female, dark skin, red hair, dreadlocks, large breasts, wide smile, brown eyes",
         "light summer dress, bead necklace",
         "a curvy Jamaican woman aged 28 with dyed red dreadlocks and a wide beautiful smile, light summer dress"),
], [
    loc("l_terrace", "Blue Mountains", "outdoors, blue mountains, jamaica, green mountains, mist, light rays, coffee plantation, terrace"),
    loc("l_cafe", "Horská kavárna", "indoors, wooden cafe, mountainside, open window, jungle, warm light, coffee cup"),
]), [
    panel("establishing", "l_terrace", [], "mist, mountains, coffee plantation, light rays", [N("Blue Mountains, Jamajka.")]),
    panel("wide", "l_terrace", ["alex"], "sitting at terrace table, holding tablet, charts, mountain view"),
    panel("medium", "l_terrace", ["alex"], "sighing, closing tablet",
          [("alex", "Práce, čísla, tabulky... Přijel jsem na druhý konec světa, ale pořád jsem jen ten nudný muž z kanceláře.", "thought")],
          gap="small"),
    panel("close-up", "l_terrace", ["alex"], "melancholy, looking at mountains",
          [("alex", "Kdo by chtěl sdílet život s chlapem bez špetky spontánnosti?", "thought")], gap="large"),
    panel("medium", "l_cafe", ["zara"], "tripping over bag, stumbling, surprised", [N("Malá horská kavárna. Hraje jemné reggae.")], gap="small"),
    panel("medium", "l_cafe", ["zara", "alex"], "man catching woman by shoulders, eye contact, faces close"),
    panel("medium", "l_cafe", ["zara"], "laughing, hand on chest",
          [("zara", "Woah! Děkuji za záchranu!"),
           ("zara", "Vy máte ale pevný stisk na někoho, kdo vypadá, že celý den jen sedí u počítače!")]),
    panel("close-up", "l_cafe", ["alex"], "smile, taking off glasses, holding eyewear",
          [("alex", "To byla náhoda... Většinou se držím jen klávesnice. Jsem Alex.")]),
    panel("medium", "l_cafe", ["zara", "alex"], "woman sitting at his table, chin on hands, smiling",
          [("zara", "Nudný? Ani náhodou. Alexi, máte v očích hluboký klid.")], gap="small"),
    panel("medium", "l_cafe", ["zara", "alex"], "coffee cups, smiling at each other, warm light",
          [("zara", "A tenhle ostrov vás naučí tancovat. Začněme společným šálkem zdejší kávové speciality!")], gap="large"),
])

# 10. Mumbaj — 80s city pop ---------------------------------------------------------------------------------
STORIES["ra_10_mumbaj"] = story(world("w_ra_10_mumbaj", "Indická noc pod hvězdami",
    "Australský mechanik Rhoan nastartuje na Marine Drive kabriolet krásné Priyi.", "retro_citypop", [
    char("rhoan", "Rhoan Dean", "1boy", "mature male, muscular, tattoo, arm tattoo, blonde hair, messy hair, blue eyes",
         "tank top, jeans, tool belt, backpack",
         "a muscular Australian mechanic aged 27, tattooed arms, messy blond hair, tank top and tool belt"),
    char("priya", "Priya Sharma", "1girl", "adult, indian, brown skin, tall female, slender, small breasts, blonde hair, long hair, brown eyes, gold jewelry",
         "turquoise saree, gold earrings, bracelet",
         "a tall slender Indian woman aged 24 with long dyed blond hair, turquoise saree and gold jewelry"),
], [
    loc("l_market", "Tržnice", "outdoors, mumbai, market, bazaar, spices, colorful stalls, string lights, auto rickshaw, crowd, evening"),
    loc("l_drive", "Marine Drive", "outdoors, marine drive, mumbai, promenade, sea, night, street lights, city lights, vintage convertible"),
]), [
    panel("establishing", "l_market", [], "spice stalls, colorful, lights, auto rickshaw", [N("Tržnice v Mumbaji.")]),
    panel("wide", "l_market", ["rhoan"], "walking, backpack, wiping sweat from forehead, dodging auto rickshaw"),
    panel("close-up", "l_market", ["rhoan"], "tired, sad smile, dirty hands",
          [("rhoan", "Svět plný barev a exotiky... A já jsem jen kluk z dílny s rukama od šmíru.", "thought")], gap="small"),
    panel("medium", "l_market", ["rhoan"], "looking around, lonely, spice stalls",
          [("rhoan", "Tady žádnou princeznu nenajdu.", "thought")], gap="large"),
    panel("wide", "l_drive", ["priya"], "broken down car, smoke from car hood, standing by car, night",
          [N("Marine Drive, „Královnin náhrdelník“. Noc.")]),
    panel("medium", "l_drive", ["rhoan"], "leaning over open hood, repairing engine, focused", gap="small"),
    panel("medium", "l_drive", ["priya"], "stepping out of car, sparkling eyes, excited, smile",
          [("priya", "Vy jste neuvěřitelný! Volala jsem odtahovku a vy jste to spravil za pět minut!")]),
    panel("medium", "l_drive", ["rhoan"], "wiping hands with handkerchief, shy smile",
          [("rhoan", "Motory jsou to jediné, čemu rozumím, slečno. Nic víc neumím.")]),
    panel("close-up", "l_drive", ["priya", "rhoan"], "woman holding his dirty hand, looking into his eyes",
          [("priya", "Rozumíte věcem, které dávají věci do pohybu. A právě jste zachránil můj večer.")], gap="small"),
    panel("wide", "l_drive", ["priya", "rhoan"], "sitting in convertible, driving along the sea, night, city lights, smile",
          [("priya", "Projížďka podél moře s mým záchranářem je to nejmenší, jak vám mohu poděkovat.")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
