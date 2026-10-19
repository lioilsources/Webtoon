"""Romance set B: ten SFW stories for adults (5 told by her, 5 by him) → data/stories/rb_*/{world,storyboard}.json.

    python3 m0/romance_b.py
    WEBTOON_DAY=romance m0/run_romance.sh rb_01_ny ...

Same building blocks and conventions as stories_romance.py; each story uses a different style preset.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}

# 1. New York — Sofia a James ----------------------------------------------------------------------
STORIES["rb_01_ny"] = story(world("w_rb_01_ny", "New York – Malá brunetka a boxer",
    "Sofia z Miami pochybuje o sobě, James trénuje na zápas.", "webtoon_romance", [
    char("sofia", "Sofia", "1girl", "adult, petite, curvy, wide hips, small breasts, long hair, wavy hair, dark brown hair, "
         "olive skin, brown eyes",
         {"default": "oversized sweater, blue jeans, sneakers", "dinner": "burgundy dress, simple dress"},
         "a petite curvy Latina woman aged 26, olive skin, long wavy dark brown hair, brown eyes"),
    char("james", "James", "1boy", "mature male, dark-skinned male, dark skin, tall, muscular, short hair, black hair",
         {"default": "grey hoodie, sweatpants, boxing gloves over shoulder", "dinner": "black shirt, dark trousers"},
         "a tall muscular African American man aged 32, short black hair, boxer"),
], [
    loc("l_park", "Central Park", "outdoors, central park, autumn, golden leaves, park bench, afternoon, sunlight"),
    loc("l_cafe", "Kavárna u parku", "indoors, cafe, window, coffee cup, autumn, warm light"),
    loc("l_lake", "Jezero", "outdoors, central park, lake, evening, street lamps, manhattan skyline, reflections"),
    loc("l_rest", "Restaurace", "indoors, restaurant, window, city lights, night, candle, new york"),
]), [
    panel("wide", "l_park", ["sofia"], "sitting on bench, holding compact mirror, looking at mirror, sad",
          [N("Central Park. Podzimní odpoledne."), ("sofia", "Proč bych někoho zajímala… jsem moc malá a…", "thought")]),
    panel("wide", "l_park", ["james"], "running, jogging, tripping over backpack, falling, surprised", sfx=["BUCH!"], gap="small"),
    panel("medium", "l_park", ["sofia", "james"], "man sitting on ground next to bench, embarrassed, laughing"),
    panel("medium", "l_cafe", ["james"], "sitting, apologetic smile, holding two coffee cups",
          [("james", "Omlouvám se. Jsem James. Trénuju na zápas.")]),
    panel("close-up", "l_cafe", ["sofia"], "shy, looking down, holding coffee cup",
          [("sofia", "Sofia. Právě jsem přijela z Miami… a pořád si myslím, že sem nepatřím.")]),
    panel("close-up", "l_cafe", ["james"], "smile, warm eyes",
          [("james", "Patříš. A ta tvoje energie je silnější než jakýkoliv úder.")], gap="large"),
    panel("wide", "l_lake", ["sofia", "james"], "walking, holding hands, evening",
          [("james", "Smím tě políbit?")]),
    panel("close-up", "l_lake", ["sofia", "james"], "kiss, closed eyes, slow, tender", gap="small"),
    panel("medium", "l_lake", ["sofia", "james"], "hug, head on chest, closed eyes, smile", gap="large"),
    panel("medium", "l_rest", ["sofia:dinner", "james:dinner"], "sitting at table, city view, smiling at each other",
          [("sofia", "Poprvé se cítím… hezká."),
           ("james", "Jsi. A já chci být ten, kdo ti to bude říkat každý den.")], gap="large"),
])

# 2. Paříž — Emma a Luc ----------------------------------------------------------------------------
STORIES["rb_02_pariz"] = story(world("w_rb_02_pariz", "Paříž – Vysoká blondýnka",
    "Emma z Londýna si připadá jako věž, Luc hledá cestu k Notre-Dame.", "watercolor_paris", [
    char("emma", "Emma", "1girl", "adult, tall female, slender, long hair, blonde hair, blue eyes, pale skin",
         {"default": "elegant grey coat, scarf", "dinner": "navy dress, long sleeves"},
         "a tall slender Nordic-looking woman aged 28, long blond hair, pale skin, elegant grey coat"),
    char("luc", "Luc", "1boy", "mature male, athletic, short hair, brown hair, brown eyes",
         {"default": "leather jacket, white t-shirt, jeans", "dinner": "leather jacket, white shirt"},
         "an athletic French man aged 35, short chestnut hair, leather jacket and jeans"),
], [
    loc("l_seine", "Nábřeží Seiny", "outdoors, seine, river, quay, paris, stone wall, overcast"),
    loc("l_cafe", "Kavárna", "outdoors, parisian cafe, small round table, coffee cup, awning, paris street"),
    loc("l_bridge", "Pod mostem", "outdoors, under bridge, seine, night, lamps, reflections on water"),
    loc("l_rest", "Restaurace s výhledem", "indoors, restaurant, window, eiffel tower, night, city lights, candle"),
]), [
    panel("wide", "l_seine", ["emma"], "standing at riverside, looking at water, lonely",
          [("emma", "Všichni tady jsou malí a roztomilí… já jsem jako věž.", "thought")]),
    panel("medium", "l_seine", ["luc"], "jogging, stopping, smile, slightly out of breath",
          [("luc", "Pardon… hledám cestu k Notre-Dame. A ty vypadáš, jako bys věděla, kam jít.")]),
    panel("close-up", "l_seine", ["emma"], "surprised, slight smile", gap="large"),
    panel("medium", "l_cafe", ["emma", "luc"], "sitting at small table, coffee cups, looking at each other",
          [("emma", "Přijela jsem z Londýna. Hledám… něco. Někoho.")]),
    panel("close-up", "l_cafe", ["luc"], "gentle smile", [("luc", "Možná jsi právě našla.")], gap="large"),
    panel("medium", "l_bridge", ["emma", "luc"], "hug, night, under bridge",
          [("luc", "Jsi krásná přesně taková, jaká jsi.")]),
    panel("close-up", "l_bridge", ["emma", "luc"], "kiss, closed eyes, smile, night", gap="large"),
    panel("medium", "l_rest", ["emma:dinner"], "sitting, smile, eiffel tower behind window",
          [("emma", "Poprvé se necítím moc vysoká.")]),
    panel("medium", "l_rest", ["emma:dinner", "luc:dinner"], "standing face to face, same height, smiling",
          [("luc", "Protože jsi přesně na mou výšku.")], gap="large"),
])

# 3. Praha — Klára a Tomáš -------------------------------------------------------------------------
STORIES["rb_03_praha"] = story(world("w_rb_03_praha", "Praha – Zrzka s kudrnami",
    "Klára pochybuje o svém těle, Tomáš z Brna nese krabici náhradních dílů.", "painterly_oil", [
    char("klara", "Klára", "1girl", "adult, curvy, large breasts, red hair, curly hair, long hair, freckles, green eyes",
         {"default": "dark green coat, long dress, high neckline", "dinner": "emerald dress, long sleeves, high neckline"},
         "a curvy Czech woman aged 27, curly red hair, freckles, green coat over a modest dress"),
    char("tomas", "Tomáš", "1boy", "mature male, broad shoulders, short hair, brown hair, beard",
         {"default": "flannel shirt, jeans, carrying cardboard box", "walk": "flannel shirt, jeans", "dinner": "dark shirt, jeans"},
         "a broad-shouldered Czech mechanic aged 34, short brown hair, beard, flannel shirt"),
], [
    loc("l_bridge", "Karlův most", "outdoors, charles bridge, fog, autumn, statues, vltava, morning"),
    loc("l_cafe", "Kavárna na Malé Straně", "indoors, old cafe, window, coffee cup, prague, warm light"),
    loc("l_petrin", "Petřín", "outdoors, petrin hill, autumn trees, path, golden leaves, prague view"),
    loc("l_rest", "Restaurace pod Hradem", "indoors, restaurant, window, prague castle, night, city lights, candle"),
]), [
    panel("wide", "l_bridge", ["klara"], "leaning on railing, looking at river, fog, sad",
          [("klara", "Proč se pořád dívají… asi proto, že jsem moc…", "thought")]),
    panel("medium", "l_bridge", ["tomas"], "carrying box, stopping, friendly smile",
          [("tomas", "Promiňte, nevíte, kde je nejbližší kavárna?"),
           ("tomas", "A vy vypadáte, jako byste potřebovala kafe víc než já.")]),
    panel("close-up", "l_bridge", ["klara"], "surprised, small smile, fog", gap="large"),
    panel("medium", "l_cafe", ["klara", "tomas"], "sitting at table, coffee cups, box on floor",
          [("tomas", "Jsem z Brna, přijel jsem na víkend. A ty?"), ("klara", "Hledám něco, co ještě neznám.")], gap="large"),
    panel("wide", "l_petrin", ["klara", "tomas:walk"], "walking, holding hands, autumn trees"),
    panel("close-up", "l_petrin", ["tomas:walk"], "gentle look, smile",
          [("tomas", "Jsi nádherná. A ty křivky jsou přesně to, co mě drží.")]),
    panel("medium", "l_petrin", ["klara", "tomas:walk"], "kiss, under trees, falling leaves, closed eyes", gap="large"),
    panel("medium", "l_rest", ["klara:dinner"], "sitting, castle view, shy smile",
          [("klara", "Poprvé se necítím moc… nápadná.")]),
    panel("medium", "l_rest", ["klara:dinner", "tomas:dinner"], "holding hands across table, smile, candlelight",
          [("tomas", "Jsi. A já to miluju.")], gap="large"),
])

# 4. Miami — Aisha a Carlos ------------------------------------------------------------------------
STORIES["rb_04_miami"] = story(world("w_rb_04_miami", "Miami – Dívka, kterou je třeba vidět",
    "Aisha pochybuje o své ženskosti, Carlos z Texasu přijel na rodeo.", "vintage_poster", [
    char("aisha", "Aisha", "1girl", "adult, petite, slender, small breasts, very short hair, black hair, dark-skinned female, dark skin",
         {"default": "loose sundress, sandals", "dinner": "white dress, gold earrings"},
         "a petite slender Afro-Caribbean woman aged 25, dark skin, very short black hair, loose sundress"),
    char("carlos", "Carlos", "1boy", "mature male, tall, muscular, brown hair, short hair, cowboy hat",
         {"default": "plaid shirt, jeans, cowboy boots", "dinner": "white shirt, jeans, cowboy hat"},
         "a tall muscular Texan cowboy aged 31, brown hair, cowboy hat, plaid shirt and jeans"),
], [
    loc("l_beach", "South Beach", "outdoors, south beach, sand, ocean, sunset, palm trees, miami"),
    loc("l_bar", "Beach bar", "outdoors, beach bar, string lights, tiki bar, evening, cocktails"),
    loc("l_pier", "Molo", "outdoors, pier, ocean, dusk, wooden boardwalk, sea breeze"),
    loc("l_rest", "Restaurace u oceánu", "indoors, restaurant, ocean view, night, candle, warm light"),
]), [
    panel("wide", "l_beach", ["aisha"], "sitting on sand, hugging knees, sunset, lonely",
          [("aisha", "Všichni tady mají… víc. Já jsem jako kluk.", "thought")]),
    panel("wide", "l_beach", ["carlos"], "riding bicycle, stopping, cowboy hat"),
    panel("medium", "l_beach", ["aisha", "carlos"], "man standing with bicycle, tipping hat, smile",
          [("carlos", "Hezký večer. Nechceš společnost?")], gap="large"),
    panel("medium", "l_bar", ["aisha", "carlos"], "sitting at bar, drinks, talking",
          [("carlos", "Přijel jsem na rodeo. A ty?"), ("aisha", "Hledám někoho, kdo mě uvidí.")], gap="large"),
    panel("wide", "l_pier", ["aisha", "carlos"], "hug, embrace, wind, dusk"),
    panel("close-up", "l_pier", ["carlos"], "looking at her, gentle", [("carlos", "Vidím tě. A jsi dokonalá.")]),
    panel("close-up", "l_pier", ["aisha", "carlos"], "kiss, closed eyes, sea breeze", gap="large"),
    panel("medium", "l_rest", ["aisha:dinner"], "sitting, smile, candlelight, ocean view",
          [("aisha", "Poprvé se cítím dost ženská.")]),
    panel("medium", "l_rest", ["aisha:dinner", "carlos:dinner"], "holding hands across table, smile",
          [("carlos", "Protože jsi.")], gap="large"),
])

# 5. Londýn — Mei a Oliver -------------------------------------------------------------------------
STORIES["rb_05_londyn"] = story(world("w_rb_05_londyn", "Londýn – Tichá krása",
    "Mei z Jakarty si myslí, že si jí nikdo nevšimne, Oliver upustí dokumenty.", "manga_mono", [
    char("mei", "Mei", "1girl", "adult, asian, slender, long hair, straight hair, black hair, brown eyes",
         {"default": "trench coat, high heels", "dinner": "black dress, trench coat"},
         "a slender Asian woman aged 29, long straight black hair, trench coat"),
    char("oliver", "Oliver", "1boy", "mature male, blonde hair, short hair, glasses, elegant",
         "dark suit, white shirt, tie",
         "an elegant English man aged 36, light blond hair, glasses, tailored suit"),
], [
    loc("l_park", "Hyde Park", "outdoors, hyde park, autumn leaves, park bench, london, overcast"),
    loc("l_cafe", "Kavárna", "indoors, cafe, window, rain on window, coffee cup, london"),
    loc("l_thames", "Temže", "outdoors, thames, riverside, evening, big ben, street lamps"),
    loc("l_rest", "Restaurace v Soho", "indoors, restaurant, soho, night, candle, warm light"),
]), [
    panel("wide", "l_park", ["mei"], "sitting on bench, alone, falling leaves",
          [("mei", "Nikdo si mě nevšimne…", "thought")]),
    panel("wide", "l_park", ["oliver"], "hurrying, dropping documents, papers flying", sfx=["ŠUST!"], gap="small"),
    panel("medium", "l_park", ["mei", "oliver"], "picking up papers, kneeling, looking at each other",
          [("oliver", "Omlouvám se… jste v pořádku?")], gap="large"),
    panel("medium", "l_cafe", ["mei", "oliver"], "sitting at table, coffee cups",
          [("oliver", "Pracuju ve financích. A vy?"), ("mei", "Přijela jsem z Jakarty. Hledám… víc než práci.")], gap="large"),
    panel("medium", "l_thames", ["mei", "oliver"], "kiss on forehead, closed eyes, evening"),
    panel("close-up", "l_thames", ["mei", "oliver"], "kiss, closed eyes",
          [("oliver", "Jsi tichá, ale tvá přítomnost je silná.")], gap="large"),
    panel("medium", "l_rest", ["mei:dinner"], "sitting, gentle smile, candlelight",
          [("mei", "Poprvé se cítím viděná.")]),
    panel("close-up", "l_rest", ["oliver"], "looking at viewer, soft smile",
          [("oliver", "A já chci, abys byla viděná jen mnou.")], gap="large"),
])

# 6. Los Angeles — Marcus a Lila -------------------------------------------------------------------
STORIES["rb_06_la"] = story(world("w_rb_06_la", "Los Angeles – Svalovec",
    "Marcus si myslí, že ženy chtějí jen jeho tělo, Lila z Mexika hledá něco skutečného.", "photo_juggernaut", [
    char("marcus", "Marcus", "1boy", "mature male, dark-skinned male, dark skin, tall, muscular, short hair, black hair",
         {"default": "tank top, sweatpants", "dinner": "black shirt, dark trousers"},
         "a tall very muscular Black man aged 33, short black hair, tank top"),
    char("lila", "Lila", "1girl", "adult, petite, curvy, wide hips, long hair, brown hair, tan skin, brown eyes",
         {"default": "jeans, crop top, denim jacket", "dinner": "red dress, long sleeves"},
         "a petite curvy Latina woman aged 27, long chestnut hair, jeans and a denim jacket"),
], [
    loc("l_pier", "Santa Monica Pier", "outdoors, santa monica pier, ferris wheel, ocean, sunset"),
    loc("l_truck", "Food truck", "outdoors, food truck, string lights, evening, tacos, beach"),
    loc("l_beach", "Pláž", "outdoors, beach, sand, waves, dusk, pacific ocean"),
    loc("l_rest", "Restaurace s výhledem", "indoors, rooftop restaurant, los angeles skyline, night, city lights"),
]), [
    panel("wide", "l_pier", ["marcus"], "leaning on railing, looking at ocean, lonely",
          [("marcus", "Všichni chtějí jen fotku…", "thought")]),
    panel("wide", "l_pier", ["lila"], "running, tripping, stumbling, surprised", gap="small"),
    panel("medium", "l_pier", ["lila", "marcus"], "man catching woman, holding her arm",
          [("lila", "Omlouvám se! Jsi v pořádku?")], gap="large"),
    panel("medium", "l_truck", ["lila", "marcus"], "eating tacos, standing by food truck, smile",
          [("lila", "Přijela jsem z Mexika. Hledám něco skutečného."), ("marcus", "Já taky.")], gap="large"),
    panel("wide", "l_beach", ["lila", "marcus"], "hug, embrace, dusk, waves"),
    panel("close-up", "l_beach", ["marcus"], "soft eyes, smile",
          [("marcus", "Ty se nedíváš na svaly. Ty se díváš na mě.")]),
    panel("close-up", "l_beach", ["lila", "marcus"], "kiss, closed eyes, dusk", gap="large"),
    panel("medium", "l_rest", ["marcus:dinner"], "sitting, city lights, thoughtful smile",
          [("marcus", "Poprvé se cítím víc než tělo.")]),
    panel("medium", "l_rest", ["lila:dinner", "marcus:dinner"], "holding hands across table, smile",
          [("lila", "Protože jsi.")], gap="large"),
])

# 7. Havana — Diego a Isabella ---------------------------------------------------------------------
STORIES["rb_07_havana"] = story(world("w_rb_07_havana", "Havana – Boxer na Malecónu",
    "Diego nezná nic než ring, Isabella z Miami hledá něco opravdového.", "ligne_claire", [
    char("diego", "Diego", "1boy", "mature male, athletic, short hair, brown hair, beard, tan skin",
         {"default": "boxing jersey, shorts", "dinner": "white linen shirt, dark trousers"},
         "an athletic Cuban boxer aged 30, short brown hair, beard"),
    char("isabella", "Isabella", "1girl", "adult, tall female, long hair, blonde hair, pale skin, blue eyes",
         "light summer dress", "a tall woman aged 26, long blond hair, fair skin, light summer dress"),
], [
    loc("l_malecon", "Malecón", "outdoors, malecon seawall, sunset, ocean, havana skyline"),
    loc("l_cafe", "Kavárna", "indoors, havana cafe, wooden counter, ceiling fan, espresso cups, sunlight"),
    loc("l_street", "Ulice", "outdoors, havana street, colorful buildings, evening, string lights, music"),
    loc("l_rest", "Restaurace s kapelou", "indoors, restaurant, live band, night, warm light"),
]), [
    panel("wide", "l_malecon", ["diego"], "sitting on seawall, sunset, alone",
          [("diego", "Ring je jediné, co znám…", "thought")]),
    panel("medium", "l_malecon", ["isabella"], "walking, stopping, smile, wind in hair",
          [("isabella", "Krásný výhled, že?")], gap="large"),
    panel("medium", "l_cafe", ["isabella", "diego"], "sitting at counter, coffee cups",
          [("isabella", "Přijela jsem z Miami. Hledám něco opravdového."), ("diego", "Já taky.")], gap="large"),
    panel("wide", "l_street", ["isabella", "diego"], "dancing, man holding woman, twirling, music"),
    panel("close-up", "l_street", ["isabella", "diego"], "faces close, looking at each other",
          [("diego", "Smím tě políbit?")]),
    panel("close-up", "l_street", ["isabella", "diego"], "kiss, closed eyes, string lights", gap="large"),
    panel("medium", "l_rest", ["diego:dinner"], "sitting, band in background, smile",
          [("diego", "Poprvé se cítím jako muž, ne jen boxer.")]),
    panel("medium", "l_rest", ["isabella", "diego:dinner"], "holding hands, smile, candlelight",
          [("isabella", "Protože jsi obojí.")], gap="large"),
])

# 8. Nairobi — Jabari a Elena ----------------------------------------------------------------------
STORIES["rb_08_nairobi"] = story(world("w_rb_08_nairobi", "Nairobi – Běžec a fotografka",
    "Jabari pořád běží, Elena z Prahy hledá klid.", "minimal_flat", [
    char("jabari", "Jabari", "1boy", "mature male, dark-skinned male, very dark skin, tall, athletic, very short hair, black hair",
         {"default": "running clothes, tank top, running shorts", "dinner": "white shirt, dark trousers"},
         "a tall athletic Kenyan man aged 34, very dark skin, very short hair, running clothes"),
    char("elena", "Elena", "1girl", "adult, red hair, long hair, freckles, large breasts, pale skin, green eyes",
         "linen dress, camera", "a European woman aged 28, long red hair, freckles, linen dress, camera"),
], [
    loc("l_park", "Národní park", "outdoors, savanna, nairobi national park, acacia tree, giraffes, morning"),
    loc("l_lodge", "Lodge", "outdoors, safari lodge, wooden terrace, savanna view, afternoon"),
    loc("l_sunset", "Západ slunce", "outdoors, savanna, sunset, orange sky, acacia silhouette"),
    loc("l_dinner", "Večeře pod hvězdami", "outdoors, night, starry sky, lanterns, dinner table, savanna"),
]), [
    panel("wide", "l_park", ["jabari"], "running, stopping, looking at view, breathing",
          [("jabari", "Vždycky běžím… ale od čeho?", "thought")]),
    panel("medium", "l_park", ["elena"], "holding camera, taking photo, smile",
          [("elena", "Omlouvám se, že vás ruším. Jste nádherný v pohybu.")]),
    panel("close-up", "l_park", ["jabari"], "surprised, shy smile", gap="large"),
    panel("medium", "l_lodge", ["elena", "jabari"], "sitting on terrace, tea cups",
          [("elena", "Přijela jsem z Prahy. Hledám klid."), ("jabari", "Já taky.")], gap="large"),
    panel("wide", "l_sunset", ["elena", "jabari"], "hug, embrace, sunset, silhouette"),
    panel("close-up", "l_sunset", ["jabari"], "gentle smile, sunset light",
          [("jabari", "Ty nechceš medaile. Chceš mě.")]),
    panel("close-up", "l_sunset", ["elena", "jabari"], "kiss, closed eyes, sunset", gap="large"),
    panel("wide", "l_dinner", ["elena", "jabari:dinner"], "sitting at table, lanterns, stars, smile",
          [("jabari", "Poprvé se cítím doma."), ("elena", "I já.")], gap="large"),
])

# 9. Jakarta — Adrian a Sari -----------------------------------------------------------------------
STORIES["rb_09_jakarta"] = story(world("w_rb_09_jakarta", "Jakarta – Muž z kanceláře",
    "Adrian z Londýna si připadá nudný, Sari mu nese něco silnějšího než kávu.", "photo_cyberreal_night", [
    char("adrian", "Adrian", "1boy", "mature male, short hair, black hair, glasses, elegant",
         "dark suit, white shirt", "an elegant Eurasian man aged 37, short black hair, glasses, dark suit"),
    char("sari", "Sari", "1girl", "adult, asian, petite, small breasts, long hair, black hair, tan skin, brown eyes",
         {"default": "batik blouse, black skirt", "tray": "batik blouse, black skirt, holding tray"},
         "a petite Indonesian woman aged 25, long dark hair, batik blouse"),
], [
    loc("l_cafe", "Kavárna ve starém městě", "indoors, colonial cafe, kota tua, jakarta, ceiling fan, evening"),
    loc("l_market", "Večerní trh", "outdoors, night market, food stalls, string lights, crowd, jakarta"),
    loc("l_canal", "Kanál", "outdoors, canal, night, lanterns, reflections, old buildings"),
    loc("l_rest", "Restaurace s výhledem", "indoors, rooftop restaurant, jakarta skyline, night, neon, city lights"),
]), [
    panel("medium", "l_cafe", ["adrian"], "sitting, coffee cup, laptop, tired, alone",
          [("adrian", "Všichni chtějí dobrodružství… já jsem jen čísla.", "thought")]),
    panel("medium", "l_cafe", ["sari:tray"], "carrying tray, smile, looking at viewer",
          [("sari", "Vypadáte, jako byste potřeboval něco silnějšího než kávu.")]),
    panel("close-up", "l_cafe", ["adrian"], "surprised, small smile", gap="large"),
    panel("wide", "l_market", ["sari", "adrian"], "walking through market, street food, lights",
          [("sari", "Pracuju tady. A vy?"), ("adrian", "Přijel jsem z Londýna. Hledám něco, co není v tabulkách.")], gap="large"),
    panel("wide", "l_canal", ["sari", "adrian"], "walking along canal, night, lanterns"),
    panel("close-up", "l_canal", ["sari", "adrian"], "kiss, closed eyes, gentle",
          [("adrian", "Ty mě vidíš jinak.")], gap="large"),
    panel("medium", "l_rest", ["adrian"], "sitting, city lights, relaxed smile, no tie",
          [("adrian", "Poprvé se necítím nudný.")]),
    panel("medium", "l_rest", ["sari", "adrian"], "holding hands across table, smile, neon lights",
          [("sari", "Protože nejsi.")], gap="large"),
])

# 10. Jamajka — Cole a Amara -----------------------------------------------------------------------
STORIES["rb_10_jamaica"] = story(world("w_rb_10_jamaica", "Jamajka – Kovboj v Negrilu",
    "Cole si myslí, že nikdo nechce venkovana, Amara tančí bosá po pláži.", "clean_webtoon", [
    char("cole", "Cole", "1boy", "mature male, tall, broad shoulders, brown hair, beard, cowboy hat",
         {"default": "denim shirt, jeans, cowboy hat", "dinner": "white shirt, jeans, cowboy hat"},
         "a tall broad-shouldered American cowboy aged 35, brown hair, beard, cowboy hat"),
    char("amara", "Amara", "1girl", "adult, petite, curvy, wide hips, short hair, curly hair, black hair, dark-skinned female, dark skin",
         "colorful dress, barefoot", "a petite curvy Jamaican woman aged 27, short curly hair, dark skin, colorful dress"),
], [
    loc("l_beach", "Pláž Negril", "outdoors, negril beach, white sand, turquoise sea, palm trees, afternoon"),
    loc("l_bar", "Beach bar", "outdoors, beach bar, reggae, wooden bar, string lights, evening"),
    loc("l_sunset", "Západ slunce", "outdoors, beach, sunset, orange sky, waves"),
    loc("l_rest", "Restaurace u oceánu", "indoors, restaurant, ocean view, night, candle, lanterns"),
]), [
    panel("wide", "l_beach", ["cole"], "sitting on sand, alone, cowboy hat",
          [("cole", "Tady jsem cizinec…", "thought")]),
    panel("wide", "l_beach", ["amara"], "dancing, barefoot, twirling, happy"),
    panel("medium", "l_beach", ["amara", "cole"], "woman stopping, pointing at hat, smile",
          [("amara", "Klobouk ti sluší. Jsi z Ameriky?")], gap="large"),
    panel("medium", "l_bar", ["amara", "cole"], "sitting at bar, drinks, laughing",
          [("amara", "Žiju tady. A ty?"), ("cole", "Přijel jsem hledat něco, co ranch nemá.")], gap="large"),
    panel("wide", "l_sunset", ["amara", "cole"], "hug, embrace, sunset, waves"),
    panel("close-up", "l_sunset", ["cole"], "gentle smile, sunset light",
          [("cole", "Ty mě nevidíš jako kovboje. Vidíš mě.")]),
    panel("close-up", "l_sunset", ["amara", "cole"], "kiss, closed eyes, sea breeze", gap="large"),
    panel("medium", "l_rest", ["cole:dinner"], "sitting, hat on table, smile",
          [("cole", "Poprvé se cítím doma i daleko od domova.")]),
    panel("medium", "l_rest", ["amara", "cole:dinner"], "holding hands across table, candlelight, smile",
          [("amara", "Protože jsi tady se mnou.")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
