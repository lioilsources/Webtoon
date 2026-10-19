"""Romance set D (ten stories, "Romantické příběhy pro dospělé" block) → data/stories/rd_*/{world,storyboard}.json.

    python3 m0/romance_d.py

Same format as stories_romance.py: one style per story, SFW (kisses and hugs), dialogue condensed from the
author's script.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}

# 1. New York — Barevný obraz New Yorku ----------------------------------------------------------
STORIES["rd_01_ny"] = story(world("w_rd_01_ny", "Barevný obraz New Yorku",
    "Ilustrátorka Nadia a knihovník Marcus, který čte Nerudu v metru.", "watercolor_paris", [
    char("nadia", "Nadia", "1girl", "adult, dark-skinned female, dark skin, curvy, wide hips, small breasts, black hair, curly hair, medium hair",
         "floral dress, vintage dress, low heels",
         "a petite curvy Ghanaian woman aged 26, shoulder-length black curly hair, vintage floral dress"),
    char("marcus", "Marcus", "1boy", "mature male, tall, glasses, thin glasses, short hair, brown hair",
         "white shirt, open collar, cardigan",
         "a tall bookish man aged 32, thin glasses, shirt with one button undone"),
], [
    loc("l_subway", "Metro", "indoors, subway car, train interior, passengers, afternoon light"),
    loc("l_library", "Knihovna", "indoors, library, bookshelves, reading room, window light"),
    loc("l_roof", "Střecha", "outdoors, rooftop, new york skyline, chimneys, sunset, golden light"),
]), [
    panel("wide", "l_subway", ["nadia"], "sitting, holding sketchbook, drawing, pencil",
          [N("Brooklyn, podzim. Metro plné cizích lidí.")]),
    panel("medium", "l_subway", ["marcus"], "stumbling, falling, book falling, surprised", sfx=["SKŘÍÍP!"], gap="small"),
    panel("medium", "l_subway", ["nadia", "marcus"], "sitting side by side, she holds his book, laughing, he blushes",
          [("marcus", "Pardon — omlouvám se—"), ("nadia", "Neruda? Čtete Nerudu v metru?"),
           ("marcus", "V metru ho čtu proto, že tam nikdo nevidí, že pláču.")]),
    panel("close-up", "l_subway", ["nadia"], "showing sketchbook, smile",
          [("nadia", "Já zase kreslím, protože slova mě zradí dřív než čára.")], gap="large"),
    panel("medium", "l_library", ["marcus"], "looking at drawing, surprised, holding paper",
          [N("O týden později."), ("marcus", "To jsem… já?")]),
    panel("medium", "l_library", ["nadia"], "closing sketchbook, embarrassed, blush",
          [("nadia", "Chci tam New York, ale nevím, jakou má barvu.")]),
    panel("medium", "l_library", ["nadia", "marcus"], "sitting across table, looking at each other",
          [("marcus", "Dejte mu barvu, kterou vidíte, když se na něj díváte z okna."),
           ("nadia", "Zlatavě oranžovou. Na podzim, když slunce svítí mezi domy.")], gap="large"),
    panel("wide", "l_roof", ["nadia", "marcus"], "standing, painting on easel, sunset",
          [("marcus", "Nikdo mě nikdy neviděl takhle. Jako bych měl duši."),
           ("nadia", "Já vás vidím. Už od toho dne v metru.")]),
    panel("close-up", "l_roof", ["nadia", "marcus"], "kiss, closed eyes, sunset", gap="small"),
    panel("medium", "l_roof", ["nadia", "marcus"], "hug, smile, golden light",
          [("marcus", "Neruda říkal, že láska je tichá. Ale vy ji teď slyšíte, že?"),
           ("nadia", "Slyším. A vidím.")], gap="large"),
])

# 2. Paříž — Polévka a odvaha -------------------------------------------------------------------
STORIES["rd_02_pariz"] = story(world("w_rd_02_pariz", "Paříž, polévka a odvaha",
    "Novinářka Chloé a kuchař Étienne, který myslí místo hosta.", "ligne_claire", [
    char("chloe", "Chloé", "1girl", "adult, small breasts, short hair, black hair, blunt bangs, brown eyes",
         "oversized blazer, white shirt, flat shoes",
         "a petite Parisian woman aged 24, short black hair with bangs, men's blazer"),
    char("etienne", "Étienne", "1boy", "mature male, red hair, short hair, freckles, calm",
         {"default": "chef apron, white shirt, rolled up sleeves", "coat": "wool coat, scarf"},
         "a red-haired French chef aged 34, freckled forearms, calm slow manner"),
], [
    loc("l_bistro", "Bistro", "indoors, small bistro, window, silver chairs, soup bowl, winter afternoon"),
    loc("l_stairs", "Schody k Sacré-Cœur", "outdoors, montmartre, stairs, sacre-coeur, night, fog, paris city lights, winter"),
]), [
    panel("wide", "l_bistro", ["chloe"], "sitting alone by window, writing, coffee cup",
          [N("Montmartre, zima.")]),
    panel("medium", "l_bistro", ["etienne"], "placing soup bowl on table, calm",
          [("chloe", "Já jsem si objednala jen kávu."),
           ("etienne", "Vím. Ale píšete už dvě hodiny a nejíte.")]),
    panel("close-up", "l_bistro", ["chloe"], "holding notebook, smirk",
          [("chloe", "Právě jste dostal do recenze hvězdičku."),
           ("etienne", "Připište, že polévka je zdarma pro každého, kdo se tváří smutně.")], gap="large"),
    panel("medium", "l_bistro", ["chloe"], "placing book on counter, evening",
          [N("O týden později."), ("chloe", "Tu jste zapomněl.")]),
    panel("medium", "l_bistro", ["etienne"], "sitting at table, looking at viewer, gentle",
          [("etienne", "Já nic nezapomněl. Čekal jsem, jestli se vrátíte.")]),
    panel("medium", "l_bistro", ["chloe", "etienne"], "sitting across table, looking at each other",
          [("etienne", "A ta recenze je dobrá?"), ("chloe", "Nejlepší, co jsem kdy napsala.")], gap="large"),
    panel("wide", "l_stairs", ["chloe", "etienne:coat"], "walking up stairs, fog, breath, night",
          [("chloe", "Bála jsem se. Že kdybych měla ráda, musela bych přestat psát."),
           ("etienne", "Psát jinak. Psát jako někdo, kdo má rád.")]),
    panel("close-up", "l_stairs", ["chloe", "etienne:coat"], "kiss, standing on step, closed eyes, fog", gap="small"),
    panel("medium", "l_stairs", ["chloe", "etienne:coat"], "hug, smile",
          [("chloe", "Do recenze přidám hvězdičku."), ("etienne", "Proč?"), ("chloe", "Za chuť.")], gap="large"),
])

# 3. Havana — Salsa na Havaně -------------------------------------------------------------------
STORIES["rd_03_havana"] = story(world("w_rd_03_havana", "Salsa na Havaně",
    "Učitelka salsy Rosario a trumpetista Diego, který nevěří, že někdo zůstane.", "photo_realvis_film", [
    char("rosario", "Rosario", "1girl", "adult, tan skin, curvy, wide hips, long hair, curly hair, brown hair, bright smile",
         "floral dress, colorful dress, red sandals",
         "a curvy Cuban woman aged 28, long voluminous curly brown hair, killer smile, floral dress"),
    char("diego", "Diego", "1boy", "mature male, tan skin, square jaw, scar on eyebrow, short hair, black hair",
         "white shirt, rolled up sleeves, dark trousers",
         "a Cuban trumpet player aged 33, square jaw, small scar through one eyebrow"),
], [
    loc("l_malecon", "Malecón", "outdoors, malecon, seawall, havana, colorful buildings, vintage cars, afternoon, orange light"),
    loc("l_restaurant", "Restaurace", "outdoors, seaside restaurant, candles, night, ocean"),
    loc("l_dawn", "Svítání", "outdoors, malecon, dawn, orange sky, empty promenade"),
]), [
    panel("wide", "l_malecon", ["rosario"], "dancing, teaching salsa, hands on hips",
          [("rosario", "Salsa není v nohou, salsa je v bocích!")]),
    panel("medium", "l_malecon", ["diego"], "holding trumpet, lowering trumpet, smirk",
          [("diego", "Nemáte rytmus, Rosario.")]),
    panel("close-up", "l_malecon", ["rosario"], "hands on hips, raised eyebrow",
          [("rosario", "Promiňte?"), ("rosario", "Tak pojďte. Ukažte mi.")], gap="large"),
    panel("wide", "l_malecon", ["rosario", "diego"], "dancing together, salsa, sunset",
          [N("Po západu slunce.")]),
    panel("medium", "l_malecon", ["rosario", "diego"], "dancing, close, looking at each other",
          [("diego", "Tančíte, jako byste se bála, že by to mohlo být skutečné."), ("rosario", "Cože?")]),
    panel("close-up", "l_malecon", ["rosario"], "serious, looking at viewer, wind in hair", gap="large"),
    panel("medium", "l_restaurant", ["rosario", "diego"], "sitting at table, candles, reaching across table",
          [("rosario", "Bála jsem se. Ten poslední odešel před pěti lety."),
           ("diego", "Tohle je poprvé, co bych chtěl hrát pro někoho.")]),
    panel("medium", "l_restaurant", ["diego"], "playing trumpet, eyes closed", sfx=["♪"],
          bubbles=[("rosario", "Tak hrajte. Já budu poslouchat. A neodejdu.")], gap="large"),
    panel("wide", "l_dawn", ["rosario", "diego"], "dancing slowly, dawn", gap="small"),
    panel("close-up", "l_dawn", ["rosario", "diego"], "kiss, closed eyes, golden light", gap="small"),
    panel("medium", "l_dawn", ["rosario", "diego"], "hug, smile",
          [("diego", "Tak tedy jste zůstala."), ("rosario", "Nezůstala. Přišla jsem domů.")], gap="large"),
])

# 4. Praha — Praha v mlze -----------------------------------------------------------------------
STORIES["rd_04_praha"] = story(world("w_rd_04_praha", "Praha v mlze",
    "Fotografka architektury Tereza a architekt Filip, který poslouchá kámen.", "manga_mono", [
    char("tereza", "Tereza", "1girl", "adult, tall female, athletic, blonde hair, long hair, straight hair, blue eyes",
         "leather jacket, jeans, sneakers",
         "a tall athletic Czech woman aged 25, long straight blond hair, blue eyes, leather jacket"),
    char("filip", "Filip", "1boy", "mature male, dark hair, short hair, calm",
         "grey sweater, coat",
         "a calm Czech architect aged 30, dark hair, the same grey sweater every day"),
], [
    loc("l_bridge", "Karlův most", "outdoors, charles bridge, statues, fog, morning, river, prague"),
    loc("l_cafe", "Kavárna", "indoors, old cafe, velvet seats, window, afternoon"),
    loc("l_tower", "Petřín", "outdoors, observation tower, night, fog, city lights below, prague"),
]), [
    panel("wide", "l_bridge", ["tereza"], "camera on tripod, taking photo, fog",
          [N("Mlha nad Vltavou. Sochy jako přízraky.")]),
    panel("medium", "l_bridge", ["filip"], "bumping into tripod, surprised", sfx=["BUM"],
          bubbles=[("filip", "Pardon, ta mlha je dnes hustá jako—")], gap="small"),
    panel("medium", "l_bridge", ["tereza", "filip"], "kneeling, holding camera, looking at each other, fog",
          [("tereza", "Jen ho prosím nedotkněte, je starší než vy."), ("filip", "Mně je třicet."),
           ("tereza", "Tak možná mladší. Ale dražší.")], gap="large"),
    panel("medium", "l_cafe", ["filip"], "holding tablet, showing sketches",
          [("filip", "Architektura je poslouchání kamene.")]),
    panel("close-up", "l_cafe", ["tereza"], "smile, looking at viewer",
          [("tereza", "Řekla bych, že posloucháte víc než lidi."), ("filip", "Lidé lžou. Kámen ne."),
           ("tereza", "Já nelžu. Jen dlouho nic neříkám.")], gap="large"),
    panel("wide", "l_tower", ["tereza", "filip"], "standing at railing, looking at camera screen, night, fog",
          [("tereza", "Ta mlha. Vypadá, jako by most dýchal.")]),
    panel("close-up", "l_tower", ["filip"], "looking at her, soft expression",
          [("filip", "Terezo… vy nefotíte město. Vy ho milujete."), ("tereza", "A vy?")]),
    panel("medium", "l_tower", ["filip"], "gentle smile, city lights",
          [("filip", "Mám pocit, že jsem přišel domů. A nemyslím Prahu. Myslím vás.")], gap="small"),
    panel("close-up", "l_tower", ["tereza", "filip"], "kiss, closed eyes, fog, night", gap="small"),
    panel("medium", "l_tower", ["tereza", "filip"], "hug, smile, night",
          [("tereza", "Tak tedy. Město dnes poslouchalo dva.")], gap="large"),
])

# 5. Bombaj — Bombajská čajová pauza ------------------------------------------------------------
STORIES["rd_05_bombaj"] = story(world("w_rd_05_bombaj", "Bombajská čajová pauza",
    "Programátorka Priya a Arjun, bývalý kriketista, který nalévá nejlepší čaj v Bombaji.", "hassaku_soft", [
    char("priya", "Priya", "1girl", "adult, indian, brown skin, slender, small breasts, long hair, black hair, almond eyes",
         "pastel saree", "a slender Indian woman aged 27, long dark hair, almond eyes, pastel modern saree"),
    char("arjun", "Arjun", "1boy", "mature male, indian, brown skin, muscular arms, goatee, short hair, black hair, wide smile",
         "kurta, rolled up sleeves", "an Indian tea-stall owner aged 35, strong arms, goatee, broad smile"),
    char("otec", "Otec", "1boy", "old man, indian, brown skin, grey hair, mustache, stern", "white kurta",
         "a stern older Indian man dressed in white"),
], [
    loc("l_stall", "Čajový stánek", "outdoors, tea stall, tin roof, rain, train station, morning, mumbai, monsoon"),
    loc("l_marine", "Marine Drive", "outdoors, marine drive, seawall, night, city lights, wet street, waves"),
]), [
    panel("wide", "l_stall", ["priya"], "running, rain, wet, under tin roof", [N("Období monzunů.")]),
    panel("medium", "l_stall", ["arjun"], "pouring tea, offering cup, smile",
          [("arjun", "Silný, s kardamomem. Vypadáte jako člověk, který dnes potřebuje silný čaj.")]),
    panel("medium", "l_stall", ["priya"], "holding tea cup, laughing, wet hair",
          [("priya", "Tohle je nejlepší čaj v celém Bombaji."),
           ("arjun", "Vím. Proto vám ho dávám zdarma.")], gap="large"),
    panel("medium", "l_stall", ["otec"], "standing, arms crossed, stern",
          [N("O dva týdny později."), ("otec", "Priyo. Proč stojíte pod tím stánkem každé ráno?")]),
    panel("close-up", "l_stall", ["priya"], "determined, holding cup",
          [("priya", "Protože mi tady někdo připravuje den tak, že se nebojím ho začít.")]),
    panel("medium", "l_stall", ["arjun"], "respectful, hand on chest",
          [("arjun", "Odešel jsem, protože matka onemocněla. Vařil jsem čaj, abych ji uživil.")], gap="large"),
    panel("wide", "l_marine", ["priya", "arjun"], "sitting on seawall, two tea cups, night",
          [("arjun", "Nejsem bohatý. Mám jen čaj a ruce, které umějí pracovat."),
           ("priya", "Máte ruce, které dělají lidem den lepší.")]),
    panel("close-up", "l_marine", ["priya", "arjun"], "holding hands, close-up of hands", gap="small"),
    panel("close-up", "l_marine", ["priya", "arjun"], "kiss, closed eyes, rain", gap="small"),
    panel("medium", "l_marine", ["priya", "arjun"], "hug, rain, smile",
          [("priya", "Zítra ráno. Stejný čas?"), ("arjun", "Každé ráno. Silný, s kardamomem.")], gap="large"),
])

# 6. Los Angeles — Kovboj a malířka z Chinatownu ------------------------------------------------
STORIES["rd_06_la"] = story(world("w_rd_06_la", "Kovboj a malířka z Chinatownu",
    "Kovboj Jake hledá ticho, malířka Amara důvod ráno vstát.", "painterly_oil", [
    char("jake", "Jake", "1boy", "mature male, tall, broad shoulders, short hair, brown hair, stubble, cowboy hat",
         "denim jacket, jeans, cowboy boots",
         "a broad-shouldered Montana cowboy aged 36, cowboy hat, denim, faint smile"),
    char("amara", "Amara", "1girl", "adult, dark-skinned female, dark skin, curvy, afro, curly hair, black hair",
         "paint-stained overalls, white t-shirt",
         "an African American painter aged 31, curly afro, curvy, paint-stained overalls"),
], [
    loc("l_studio", "Ateliér", "indoors, art studio, gallery, canvases, paint, chinatown, afternoon light"),
    loc("l_roof", "Střecha", "outdoors, rooftop, los angeles skyline, sunset, blanket"),
]), [
    panel("wide", "l_studio", ["amara"], "standing in front of canvas, painting, holding brush",
          [N("Los Angeles, Chinatown. Jaro.")]),
    panel("medium", "l_studio", ["jake"], "holding hat, looking around, doorway",
          [("jake", "Promiňte — tohle je galerie, nebo dílna?"),
           ("amara", "Obojí. Záleží na tom, jestli kupujete, nebo koukáte.")]),
    panel("medium", "l_studio", ["jake"], "pointing at painting, prairie sunset painting",
          [("jake", "Tenhle je tichý. Slyším v něm vítr přes trávu.")]),
    panel("close-up", "l_studio", ["amara"], "surprised, turning around",
          [("amara", "…To je název, který jsem hledala měsíc.")], gap="large"),
    panel("medium", "l_studio", ["jake", "amara"], "cleaning up studio, talking, holding rag",
          [N("O týden později."), ("jake", "V Montaně jsem měl sto důvodů, proč být sám. Ale žádný, proč ráno vstát.")]),
    panel("close-up", "l_studio", ["amara"], "soft expression, looking down",
          [("amara", "Já vím, jak to je. Měsíce jsem neměla důvod vstát.")], gap="large"),
    panel("wide", "l_roof", ["jake", "amara"], "sitting on blanket, sunset, pizza",
          [("jake", "V Montaně má západ slunce osm barev. Tady jen tři, ale víc světel.")]),
    panel("close-up", "l_roof", ["jake", "amara"], "brushing hair from her forehead, looking at each other", gap="small"),
    panel("close-up", "l_roof", ["jake", "amara"], "kiss, closed eyes, sunset", gap="small"),
    panel("medium", "l_roof", ["jake", "amara"], "hug, head on chest, smile",
          [("amara", "Že jsme si našli důvod ráno vstát.")], gap="large"),
])

# 7. Londýn — Bankéř a violoncellistka ----------------------------------------------------------
STORIES["rd_07_londyn"] = story(world("w_rd_07_londyn", "Londýn, jedna bota u Temže",
    "Bankéř Oliver bez jedné boty a violoncellistka Ivy, která se bojí sálů.", "photo_cyberreal_night", [
    char("oliver", "Oliver", "1boy", "mature male, short hair, brown hair, neat hair, clean-shaven",
         "tailored suit, white shirt, tie",
         "a polished British banker aged 33 in a perfect suit"),
    char("ivy", "Ivy", "1girl", "adult, asian, tall female, slender, long hair, black hair, straight hair",
         "long flowing coat, scarf",
         "a tall slender Chinese-British cellist aged 29, long sleek black hair, flowing coat and scarf"),
], [
    loc("l_southbank", "Southbank", "outdoors, southbank, thames, bench, night, city lights reflection, london"),
    loc("l_eye", "London Eye", "indoors, ferris wheel capsule, night, london skyline, city lights"),
]), [
    panel("wide", "l_southbank", ["oliver"], "sitting on bench, one shoe off, shoe on bench, night",
          [N("Southbank, podzim.")]),
    panel("medium", "l_southbank", ["ivy"], "holding cello case, holding shoe, laughing",
          [("ivy", "Tohle je… vaše?"), ("oliver", "Ano. Puchýř. Omlouvám se za nepořádek.")]),
    panel("medium", "l_southbank", ["oliver"], "standing, embarrassed, smile",
          [("oliver", "Oblek má systém. Život má systém. Puchýř systém nemá."),
           ("ivy", "A co máte rád, když systém neplatí?")]),
    panel("close-up", "l_southbank", ["oliver"], "looking at viewer, quiet",
          [("oliver", "Nevím. Nikdy jsem to nezkoušel.")], gap="large"),
    panel("wide", "l_southbank", ["ivy"], "playing cello, street performance, crowd, night",
          [N("O týden později.")]),
    panel("medium", "l_southbank", ["oliver"], "standing in crowd, moved, teary eyes",
          [("oliver", "Poslouchám čísla celý den. A tohle bylo živé."),
           ("ivy", "Vždycky se ptají, proč nehraju v sále. Bojím se sálů.")], gap="large"),
    panel("medium", "l_eye", ["ivy", "oliver"], "sitting facing each other, night skyline",
          [("ivy", "Dnes jsem se rozhodla hrát v sále."), ("oliver", "Proč?")]),
    panel("close-up", "l_eye", ["ivy"], "looking at him, city lights",
          [("ivy", "Víc se bojím, že tohle — co cítím teď — zůstane jen náhodou.")]),
    panel("close-up", "l_eye", ["ivy", "oliver"], "kiss, closed eyes, london skyline", gap="small"),
    panel("medium", "l_eye", ["ivy", "oliver"], "hug, smile",
          [("oliver", "Tohle je první věc v životě, kde žádný systém nechci.")], gap="large"),
])

# 8. Miami — Boxer a píseň ---------------------------------------------------------------------
STORIES["rd_08_miami"] = story(world("w_rd_08_miami", "Miami, boxer a píseň",
    "Boxer Rafa trénuje děti, kadeřnice Solange zpívá haitské písně.", "retro_citypop", [
    char("rafa", "Rafa", "1boy", "mature male, tan skin, muscular, broken nose, short hair, black hair, gentle eyes",
         {"default": "tank top, track pants, towel on shoulder", "dinner": "white shirt, dark trousers"},
         "a Miami boxer aged 30, broken nose, hard hands, gentle eyes"),
    char("solange", "Solange", "1girl", "adult, dark-skinned female, dark skin, curvy, large breasts, wide hips, black hair, curly hair",
         "satin blouse, colorful blouse, skirt",
         "a curvy Haitian-American hairdresser aged 26, lively eyes, colorful satin blouse"),
], [
    loc("l_gym", "Tělocvična", "indoors, old boxing gym, boxing ring, cracked windows, rain outside, afternoon"),
    loc("l_beach", "Pláž", "outdoors, beach, sunset, orange sky, palm trees, miami"),
    loc("l_harbor", "Restaurace u přístavu", "outdoors, harbor restaurant, candles, night, boats, sea breeze"),
]), [
    panel("wide", "l_gym", ["solange"], "wet, running inside, broken umbrella, rain",
          [("solange", "Promiňte — mohla bych se schovat? Prší jako na Haiti.")]),
    panel("medium", "l_gym", ["rafa"], "holding towel, offering towel, smile",
          [("rafa", "Tady schováváme boxery, ale dámy s rozbitým deštníkem taky.")]),
    panel("medium", "l_gym", ["solange"], "drying hair with towel, smile",
          [("solange", "Vy jste ten boxer, ne?"),
           ("rafa", "Byl. Lepší je učit dětské rány než rozdávat vlastní.")], gap="large"),
    panel("wide", "l_beach", ["solange"], "singing, eyes closed, sunset", sfx=["♪"], gap="small"),
    panel("medium", "l_beach", ["rafa"], "sitting on sand, listening, moved",
          [("rafa", "Můj táta takhle zpíval. Ta píseň — zpívala jste ji úplně stejně.")]),
    panel("medium", "l_beach", ["rafa", "solange"], "sitting together on sand, sunset",
          [("rafa", "Říkali mi, že musím být kamenný."),
           ("solange", "Kamenný muž, který se nebojí měkkosti. To je v Miami vzácné.")], gap="large"),
    panel("medium", "l_harbor", ["rafa:dinner"], "sitting at table, candles, nervous",
          [("rafa", "Nikdy jsem nebyl zamilovaný. A teď rozumím každému slovu o lásce.")]),
    panel("close-up", "l_harbor", ["solange"], "smile, candlelight",
          [("solange", "Tak to bude první polibek, který v životě dáte?"), ("rafa", "Ano.")]),
    panel("close-up", "l_harbor", ["rafa:dinner", "solange"], "kiss, closed eyes, candlelight", gap="small"),
    panel("medium", "l_harbor", ["rafa:dinner", "solange"], "hug, head on chest, night",
          [("solange", "Skládám píseň pro chlapce z tělocvičny, který se nebojí být měkký.")], gap="large"),
])

# 9. Nairobi — Zvuk savany ---------------------------------------------------------------------
STORIES["rd_09_nairobi"] = story(world("w_rd_09_nairobi", "Nairobi, zvuk savany",
    "Automechanik Kwame a veterinářka Zuri — nejdřív pes, pak auto.", "vintage_poster", [
    char("kwame", "Kwame", "1boy", "mature male, dark-skinned male, very dark skin, muscular arms, short hair, black hair, big smile",
         "work overalls, oil stains", "a Kenyan mechanic aged 38, muscular arms, hearty laugh, overalls"),
    char("zuri", "Zuri", "1girl", "adult, dark-skinned female, very dark skin, tall female, very short hair, natural hair",
         "khaki shirt, cargo pants", "a tall Kenyan veterinarian aged 34, short natural hair, khaki shirt"),
], [
    loc("l_garage", "Autoservis", "indoors, auto repair shop, car, jeep, tools, afternoon, nairobi"),
    loc("l_clinic", "Klinika", "indoors, veterinary clinic, corridor, evening"),
    loc("l_park", "Národní park", "outdoors, savanna, sunset, giraffes in distance, acacia tree, nairobi national park"),
]), [
    panel("wide", "l_garage", ["kwame"], "lying under car, legs visible, tools",
          [N("Nairobi, období dešťů.")]),
    panel("medium", "l_garage", ["zuri"], "kneeling, worried, jeep",
          [("zuri", "Pes ještě dýchá, ale potřebuju mechanika dřív než zavírací hodinu.")]),
    panel("medium", "l_garage", ["kwame"], "sitting on floor, dog on lap, gentle",
          [("kwame", "Pak pes první, auto druhé.")]),
    panel("close-up", "l_garage", ["zuri"], "laughing, sitting on tire",
          [("zuri", "Máte psa raději než motor?"), ("kwame", "Motor neví, co je strach. Pes ano.")], gap="large"),
    panel("medium", "l_clinic", ["kwame"], "standing by wall, awkward, hands in pockets",
          [("zuri", "Pes bude žít."), ("kwame", "Dobře. Dobře. A vy — jak se máte?")]),
    panel("medium", "l_clinic", ["zuri"], "tired smile, lab coat",
          [("kwame", "Sny nejsou dědictví. Sny jsou vlastní.")], gap="large"),
    panel("wide", "l_park", ["kwame", "zuri"], "sitting on car hood, sunset, savanna",
          [("zuri", "Řeknu to rovnou: Líbíte se mi.")]),
    panel("close-up", "l_park", ["kwame"], "smile, sunset light",
          [("kwame", "Tak to je první zápas, který jsem kdy vyhrál bez jediné rány.")], gap="small"),
    panel("close-up", "l_park", ["kwame", "zuri"], "kiss, closed eyes, sunset", gap="small"),
    panel("medium", "l_park", ["kwame", "zuri"], "hug, smile, savanna",
          [("zuri", "Proč mě objímáte?"), ("kwame", "Protože auto neumí slovo ‚miluju‘.")], gap="large"),
])

# 10. Jakarta — Angličtina za deště -------------------------------------------------------------
STORIES["rd_10_jakarta"] = story(world("w_rd_10_jakarta", "Jakarta, angličtina za deště",
    "Přístavní dělník Bram se učí anglicky z knihy z tržiště, lékařka Maya ho učí.", "clean_webtoon_noartist", [
    char("bram", "Bram", "1boy", "mature male, asian, tan skin, athletic, short hair, black hair",
         "work jacket, grey t-shirt", "an athletic Indonesian dock worker aged 29, short black hair"),
    char("maya", "Maya", "1girl", "adult, asian, tan skin, curvy, wide hips, small breasts, long hair, black hair, glasses",
         {"default": "white coat, floral dress", "dress": "floral dress"},
         "a petite curvy Indonesian doctor aged 27, long hair, glasses, white coat over a floral dress"),
], [
    loc("l_port", "Přístav", "outdoors, port, shipping containers, shelter, heavy rain, morning, jakarta"),
    loc("l_cafe", "Kavárna", "indoors, small cafe, rain on window, textbook, coffee cup"),
    loc("l_quay", "Nábřeží", "outdoors, waterfront, night after rain, city lights, bay, containers on horizon"),
]), [
    panel("wide", "l_port", ["bram"], "sitting under shelter, reading book, rain", [N("Jakarta. Tropický déšť.")]),
    panel("medium", "l_port", ["maya"], "wet, broken umbrella, running under shelter",
          [("maya", "Promiňte — můžu se schovat?"), ("bram", "Yes. You can… stay.")]),
    panel("medium", "l_port", ["maya", "bram"], "sitting under shelter, showing book",
          [("bram", "Učím se. Chci jednou studovat univerzitu."),
           ("maya", "Já jsem lékařka. Možná bych vám mohla pomoct.")], gap="large"),
    panel("medium", "l_cafe", ["maya"], "holding textbook, strict teacher, smile",
          [N("O týden později."), ("maya", "Přeložte: ‚I love you.‘")]),
    panel("close-up", "l_cafe", ["bram"], "serious, looking down",
          [("bram", "Tohle slovo se neučím. Až ho řeknu, musím vědět, že je pravda.")]),
    panel("close-up", "l_cafe", ["maya"], "soft expression, blush",
          [("maya", "To slovo se neučí. To slovo se cítí.")], gap="large"),
    panel("wide", "l_quay", ["maya:dress", "bram"], "walking, night, wet ground, city lights",
          [("bram", "Chci říct jednu větu. Učil jsem se ji celý den.")]),
    panel("close-up", "l_quay", ["bram"], "nervous smile, looking at viewer",
          [("bram", "You… are… my sunshine in the rain.")]),
    panel("close-up", "l_quay", ["maya:dress"], "laughing, tears, happy tears", gap="small"),
    panel("close-up", "l_quay", ["maya:dress", "bram"], "kiss, closed eyes, night", gap="small"),
    panel("medium", "l_quay", ["maya:dress", "bram"], "hug, head on chest",
          [("maya", "To slovo už jsi řekl. A já jsem mu rozuměla bez překladu.")], gap="large"),
])


def main():
    for key, (w, sb) in STORIES.items():
        d = DATA / "stories" / key
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{key}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
