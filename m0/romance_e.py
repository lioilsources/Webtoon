"""Romance set E (10 stories: 5 women find love, 5 men find a muse) → data/stories/re_*/{world,storyboard}.json.

    python3 m0/romance_e.py
    WEBTOON_DAY=romance m0/run_romance.sh re_01_ny re_02_kingston ...

Same helpers and rules as stories_romance.py; one style preset per story, each used once.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}

# 1. Šátek nad Brooklynem — photoreal --------------------------------------------------------------
STORIES["re_01_ny"] = story(world("w_re_01_ny", "Šátek nad Brooklynem",
    "Nikol z Prahy ztratí v Brooklynu babiččin šátek a sochař Gabriel ho najde.", "photo_juggernaut", [
    char("nikol", "Nikol", "1girl", "adult, curvy, wide hips, short stature, curly hair, brown hair, brown eyes",
         "oversized coat, red scarf, sneakers",
         "a short curvy Czech woman aged 26, curly brown hair, warm humorous eyes"),
    char("gabriel", "Gabriel", "1boy", "mature male, dark-skinned male, dark skin, tall, slender, dreadlocks, black hair, brown eyes",
         {"default": "leather apron, grey t-shirt, clay on hands", "evening": "denim jacket, grey t-shirt"},
         "a tall slender African American sculptor aged 33, dreadlocks, smudge of clay on his cheek"),
], [
    loc("l_street", "Brooklyn", "outdoors, brooklyn, brooklyn bridge, grey sky, autumn, galleries, alley"),
    loc("l_studio", "Ateliér", "indoors, sculpture studio, clay, sculptures, dust in light, light rays"),
    loc("l_roof", "Střecha", "outdoors, rooftop, dusk, new york skyline, city lights, blanket, paper cups"),
]), [
    panel("establishing", "l_street", [], "autumn, bridge, cloudy sky", [N("Brooklyn, podzim. Kafe stojí sedm dolarů.")]),
    panel("medium", "l_street", ["nikol"], "holding map upside down, wind, red scarf flying away, surprised", sfx=["FŮŮ"]),
    panel("medium", "l_street", ["gabriel"], "picking up red scarf, clay on face, smile"),
    panel("medium", "l_street", ["nikol", "gabriel"], "blush, embarrassed, man holding red scarf",
          [("nikol", "To je můj šátek. Teda byl. Teda je. Promiň, mluvím česky, když se stydím."),
           ("gabriel", "Pak se styďte dál. Česky je to nejhezčí, co jsem dnes slyšel.")]),
    panel("close-up", "l_street", ["nikol", "gabriel"], "man tying scarf around her neck, gentle, looking at each other",
          [("gabriel", "Teď patříte k Brooklynu. Odhlasováno.")], gap="large"),
    panel("medium", "l_studio", ["nikol"], "touching unfinished sculpture, surprised, sculpture of woman's head",
          [("nikol", "Proč má ta socha můj nos?")]),
    panel("medium", "l_studio", ["gabriel"], "standing among sculptures, shy smile",
          [("gabriel", "Protože jsem ho viděl v metru před třemi dny. A pak jsem ho nemohl přestat vymýšlet.")]),
    panel("close-up", "l_studio", ["nikol", "gabriel"], "handshake, holding hands, clay on hands, smile",
          [("nikol", "To je… skoro děsivé. A trochu to nejromantičtější, co jsem slyšela.")], gap="large"),
    panel("wide", "l_roof", ["nikol", "gabriel:evening"], "sitting on blanket, paper cups, city lights",
          [("gabriel", "Pochybovala jste o své kráse. Proč?"),
           ("nikol", "Protože jsem malá a kulatá a v metru mě lidé přehlížejí.")]),
    panel("close-up", "l_roof", ["gabriel:evening"], "looking at viewer, soft smile, city lights",
          [("gabriel", "Newyorčané se neumí dívat. Já umím. Dívám se pořád.")], gap="small"),
    panel("close-up", "l_roof", ["nikol", "gabriel:evening"], "kiss, closed eyes, first star in sky, dusk", gap="large"),
])

# 2. Rytmus Kingstonu — flat minimalism ------------------------------------------------------------
STORIES["re_02_kingston"] = story(world("w_re_02_kingston", "Rytmus Kingstonu",
    "Aisha z Paříže roztančí ulici v Kingstonu a hudebník Rohan přestane hrát.", "minimal_flat", [
    char("aisha", "Aisha", "1girl", "adult, dark-skinned female, dark skin, tall female, athletic, very short hair, afro, big earrings",
         "linen overalls", "a tall athletic Black French woman aged 29, short afro, big earrings, explosive laugh"),
    char("rohan", "Rohan", "1boy", "mature male, dark-skinned male, dark skin, long hair, braids, relaxed, guitar on back",
         "open shirt, linen pants", "a relaxed Jamaican musician aged 31, long braids, guitar on his back"),
], [
    loc("l_corner", "Kingston", "outdoors, kingston, colorful houses, street corner, street band, hot, sunny"),
    loc("l_beach", "Blue Lagoon", "outdoors, beach, lagoon, turquoise water, palm trees, late afternoon"),
    loc("l_fire", "Koncert na pláži", "outdoors, beach, night, bonfire, drums, stars, palm tree"),
]), [
    panel("wide", "l_corner", ["aisha"], "holding guidebook, lost, standing on corner"),
    panel("wide", "l_corner", ["aisha"], "dancing, happy, children dancing, music notes", sfx=["BUM-TSS"]),
    panel("medium", "l_corner", ["rohan"], "holding guitar, stopped playing, smile",
          [("rohan", "Slečno. Vy jste mi rozbila písničku.")]),
    panel("medium", "l_corner", ["aisha", "rohan"], "laughing, man offering hand",
          [("aisha", "Promiňte. Tanec se prostě stane."),
           ("rohan", "To nebyla stížnost. To byla žádost o ruku. Na tanec. Hned.")], gap="large"),
    panel("wide", "l_beach", ["aisha", "rohan"], "dancing together, teaching dance steps, barefoot",
          [("aisha", "Řekni: ‚Tu es belle.‘ — Jsi krásná."), ("rohan", "Tů é bél…")]),
    panel("close-up", "l_beach", ["aisha"], "blush, smile",
          [("rohan", "‚Mi soon come.‘ — Hned jsem tady."), ("aisha", "Mi soon come.")]),
    panel("medium", "l_beach", ["aisha"], "laughing loudly, seagulls flying away, head back", sfx=["HAHA!"], gap="large"),
    panel("medium", "l_fire", ["rohan"], "sitting by bonfire, playing guitar, looking at viewer",
          [("rohan", "Hledal jsem ženu, která má rytmus v kostech. Pak jste roztancovala ulice, na kterých tančím celý život.")]),
    panel("medium", "l_fire", ["aisha"], "smile, firelight, hand on chest",
          [("aisha", "Rozesmál jste mě, roztančil a pak mi ukradl srdce. To je krádež, pane."), ("rohan", "Zatkněte mě.")]),
    panel("wide", "l_fire", ["aisha", "rohan"], "kiss, under palm tree, bonfire, stars, closed eyes", gap="large"),
])

# 3. Havana ve 4/4 taktu — analogue film photo -----------------------------------------------------
STORIES["re_03_havana"] = story(world("w_re_03_havana", "Havana ve 4/4 taktu",
    "Lucia z Madridu váhá před klubem La Terraza, tanečník Alejandro jí nabídne ruku.", "photo_realvis_film", [
    char("lucia", "Lucia", "1girl", "adult, red hair, long hair, freckles, round face, large breasts, curvy",
         "floral dress, vintage dress, modest neckline, dance shoes",
         "a Spanish woman aged 24, red hair, freckles, round cheeks, vintage floral dress"),
    char("alejandro", "Alejandro", "1boy", "mature male, tan skin, wavy hair, black hair, bright smile, elegant",
         "1950s suit, cream suit, white shirt",
         "a Cuban dancer aged 32, wavy black hair, white teeth, elegant 1950s-style suit"),
], [
    loc("l_terraza", "La Terraza", "outdoors, havana, vintage car, pastel buildings, club entrance, evening"),
    loc("l_club", "Klub", "indoors, dance club, ceiling fans, shadows, live band, warm light"),
    loc("l_malecon", "Malecón", "outdoors, malecon seawall, midnight, waves, moonlight, havana"),
]), [
    panel("establishing", "l_terraza", [], "vintage car, pastel houses, salsa music", [N("Havana. Ze dveří zní salsa.")]),
    panel("medium", "l_terraza", ["lucia"], "standing at entrance, hesitant, hand on chest"),
    panel("medium", "l_terraza", ["alejandro"], "offering hand, smile, standing in doorway",
          [("alejandro", "Máte dvě možnosti. Jít domů. Nebo tančit se mnou a pak mi vyprávět, proč váháte.")]),
    panel("medium", "l_terraza", ["lucia", "alejandro"], "smile, taking his hand",
          [("lucia", "A jsou ty možnosti seřazené podle doporučení?"), ("alejandro", "Ano. Druhá. Vždy druhá.")], gap="large"),
    panel("wide", "l_club", ["lucia", "alejandro"], "dancing, salsa, twirling, dress flowing, motion blur"),
    panel("close-up", "l_club", ["alejandro"], "smile, looking at her, warm light",
          [("alejandro", "Vy tančíte jako Havana. Trochu zchátralé, úplně krásné, plné příběhů.")]),
    panel("close-up", "l_club", ["lucia"], "laughing, blush",
          [("lucia", "To je nejromantičtější urážka, co jsem kdy dostala.")], gap="large"),
    panel("wide", "l_malecon", ["lucia", "alejandro"], "sitting on seawall, legs dangling, man's jacket on her shoulders, waves",
          [("lucia", "Říkala jsem si, že romantika umřela. Že všichni jen koukají do telefonů.")]),
    panel("close-up", "l_malecon", ["alejandro"], "soft smile, moonlight",
          [("alejandro", "Na Kubě telefony vypadávají. Zůstávají jen lidé. A tanec. A ty.")], gap="small"),
    panel("medium", "l_malecon", ["lucia", "alejandro"], "kiss, closed eyes, waves, moonlight, dress in breeze",
          [N("Kapitola jedna: Havana. Kapitola dvě: celý život.")], gap="large"),
])

# 4. Tiše v Paříži — watercolour -------------------------------------------------------------------
STORIES["re_04_pariz"] = story(world("w_re_04_pariz", "Tiše v Paříži",
    "Tichá Mei Lin ze Šanghaje a knihkupec Henri z Rue Mouffetard.", "watercolor_paris", [
    char("meilin", "Mei Lin", "1girl", "adult, asian, slender, long hair, very long hair, black hair, straight hair, delicate features",
         "white shirt, black trousers, minimalist", "a slender Chinese woman aged 31, waist-length straight black hair, delicate features"),
    char("henri", "Henri", "1boy", "mature male, glasses, messy hair, brown hair, brown eyes",
         "knit sweater, beige sweater", "a French bookseller aged 34, glasses, tousled brown hair, knitted sweater"),
], [
    loc("l_rain", "Rue Mouffetard", "outdoors, paris, rain, bookstore front, awning, cobblestones"),
    loc("l_books", "Knihkupectví", "indoors, bookstore, bookshelves, dust in light, warm light, old books"),
    loc("l_seine", "Seina", "outdoors, seine, riverbank, bench, sunset, croissant, paris"),
]), [
    panel("wide", "l_rain", ["meilin"], "standing under awning, holding umbrella, rain, hesitant"),
    panel("medium", "l_rain", ["henri"], "opening door, smile, gesturing inside",
          [("henri", "Knihkupectví je jediné místo, kde se nesmí mlčet. Ale můžete začít knihou.")]),
    panel("close-up", "l_rain", ["meilin"], "shy, looking down, rain",
          [("meilin", "Já… jsem moc tichá. Hledám si v knihách odvahu, kterou nemám.")]),
    panel("medium", "l_books", ["henri"], "pointing at bookshelf, smile",
          [("henri", "Pak jste přišla správně. Odvaha je na policích. Levá strana, druhá řada.")], gap="large"),
    panel("medium", "l_books", ["meilin", "henri"], "browsing books, man pretending to sort books",
          [("henri", "Mluvíte málo. Já mluvím moc. Jsme kompletní rozhovor."),
           ("meilin", "V Číně říkáme: nejhlasitější slovo je to, které čeká.")]),
    panel("close-up", "l_books", ["meilin"], "full smile, holding book"),
    panel("close-up", "l_books", ["henri"], "stunned, open mouth, blush", gap="large"),
    panel("wide", "l_seine", ["meilin", "henri"], "sitting on bench, croissants, sunset",
          [("henri", "Máte ráda Paříž?"),
           ("meilin", "Dnes mi připadá tichá. Protože někdo mi naslouchá, jako by ticho byla hudba.")]),
    panel("close-up", "l_seine", ["henri"], "gentle smile, sunset light",
          [("henri", "Ticho je hudba. Vy jste mi to dnes dokázala.")], gap="small"),
    panel("medium", "l_seine", ["meilin", "henri"], "hug, kiss on head, closed eyes, sunset", gap="large"),
])

# 5. Londýnská mlha, varšavské srdce — noir monochrome ---------------------------------------------
STORIES["re_05_londyn"] = story(world("w_re_05_londyn", "Londýnská mlha, varšavské srdce",
    "Zofia z Varšavy bojuje s deštníkem na Borough Market, kuchař Daniel ji zachrání.", "noir_mono", [
    char("zofia", "Zofia", "1girl", "adult, tall female, athletic, blonde hair, long hair, freckles, glasses, broken glasses",
         "leather jacket, long scarf", "a tall athletic Polish woman aged 27, blond hair, freckles, taped glasses, grandfather's scarf"),
    char("daniel", "Daniel", "1boy", "mature male, dark-skinned male, dark skin, tall, dreadlocks, hair bun, smile",
         "chef apron, white shirt", "a tall British chef aged 30 with Jamaican roots, dreadlocks tied in a bun, apron"),
], [
    loc("l_market", "Borough Market", "outdoors, london, market, fog, spices, stalls"),
    loc("l_bistro", "Bistro", "indoors, small bistro kitchen, spices, steam, counter"),
    loc("l_bridge", "Tower Bridge", "outdoors, tower bridge, night, fog, street lamps, london"),
]), [
    panel("establishing", "l_market", [], "fog, market stalls", [N("Londýn, Borough Market. Mlha a vůně koření.")]),
    panel("medium", "l_market", ["zofia"], "umbrella turned inside out, wind, annoyed, rain", sfx=["PRÁSK"]),
    panel("medium", "l_market", ["daniel"], "running out of bistro, apron, smile",
          [("daniel", "Váš deštník právě zemřel. Pojďte dovnitř, než skončíte jako on.")]),
    panel("close-up", "l_market", ["zofia"], "stubborn, blush",
          [("zofia", "Já zvládnu cokoliv. Jen ne deštníky. A ne muže, kteří vaří, protože pak nechci odejít.")], gap="large"),
    panel("medium", "l_bistro", ["daniel"], "cooking, holding spices, steam, smile",
          [("daniel", "Kardamom je tichá dáma. Chilli je moje sestra. Hlučná, ale bez ní by svět stál.")]),
    panel("medium", "l_bistro", ["zofia"], "sitting at counter, chin on hand, curious",
          [("zofia", "A co jste vy?"), ("daniel", "Já jsem sůl. Nepoznáte mě, dokud chybím.")], gap="large"),
    panel("close-up", "l_bridge", ["zofia"], "glasses fixed with string, smile, fog",
          [N("Daniel jí opravil brýle provázkem — „dočasné řešení, trvalý úmysl“.")]),
    panel("medium", "l_bridge", ["daniel"], "looking at viewer, fog, street lamp",
          [("daniel", "Bojovala jste s deštníkem a vyhrála jste. Zamiloval jsem se do vítěze.")]),
    panel("close-up", "l_bridge", ["zofia"], "sad smile, fog",
          [("zofia", "Já jsem jen Polka s rozbitýma brýlema."), ("daniel", "Pak se Anglie mýlí a já ne.")], gap="small"),
    panel("medium", "l_bridge", ["zofia", "daniel"], "kiss, shared scarf around both, fog, closed eyes", gap="large"),
])

# 6. Účetní a Pacifik — 80s city pop -------------------------------------------------------------
STORIES["re_06_la"] = story(world("w_re_06_la", "Účetní a Pacifik",
    "Účetní Tomáš z Brna přijde v kravatě na pláž v Santa Monice, surfařka Kayla mu chytí mapu.", "retro_citypop", [
    char("tomas", "Tomáš", "1boy", "mature male, slender, glasses, short hair, brown hair",
         {"default": "white shirt, necktie, dress pants", "surf": "rash guard, board shorts, wet hair",
          "evening": "white shirt, loosened necktie, rolled up sleeves"},
         "a slender Czech accountant aged 28, glasses, neatly ironed shirt"),
    char("kayla", "Kayla", "1girl", "adult, tan skin, blonde hair, streaked hair, long hair, smile",
         {"default": "rash guard, board shorts", "evening": "denim jacket, sundress"},
         "a sun-tanned Californian surfer aged 27, sun-streaked blond hair, laughing"),
], [
    loc("l_beach", "Santa Monica", "outdoors, santa monica, beach, pier, ocean, waves, sunny"),
    loc("l_surf", "Vlny", "outdoors, ocean, waves, surfboard, sunset, orange sky"),
    loc("l_pier", "Promenáda", "outdoors, santa monica pier, ferris wheel, night, carnival lights"),
]), [
    panel("wide", "l_beach", ["tomas"], "standing on beach, shoes in sand, holding map, out of place"),
    panel("medium", "l_beach", ["kayla"], "surfing, catching paper in air, splash", sfx=["ŠPLOUCH"]),
    panel("medium", "l_beach", ["kayla"], "holding wet map, grin",
          [("kayla", "Gratuluji. První vlna, první ztracený dokument. Jste oficiálně Kalifornan.")]),
    panel("close-up", "l_beach", ["tomas"], "embarrassed, adjusting glasses",
          [("tomas", "Já jsem účetní z Brna. Já jsem sem nepatřil ani před tou vlnou.")], gap="large"),
    panel("wide", "l_surf", ["tomas:surf"], "falling off surfboard, splash", sfx=["ŽBLUŇK"], gap="small"),
    panel("wide", "l_surf", ["tomas:surf", "kayla"], "man standing on surfboard, woman cheering, sunset",
          [("tomas", "Já stojím! Já opravdu stojím!", "shout"), ("kayla", "To říká každý, koho jsem naučila surfovat.")]),
    panel("close-up", "l_surf", ["kayla"], "wink, laughing",
          [("tomas", "Kolik jich bylo?"), ("kayla", "Jeden. Právě teď.")], gap="large"),
    panel("medium", "l_pier", ["tomas:evening"], "writing in notebook, smile, carnival lights",
          [("tomas", "Náklady: letenka. Výnos: ona.", "thought")]),
    panel("medium", "l_pier", ["kayla:evening", "tomas:evening"], "standing close, ferris wheel lights",
          [("kayla", "Hledala jsem muže, který se nebojí vypadat směšně. Vy padáte úžasně."),
           ("tomas", "Teď bych rád poprvé skončil v něčích rukou.")]),
    panel("wide", "l_pier", ["kayla:evening", "tomas:evening"], "kiss, under ferris wheel, night, carnival lights, closed eyes", gap="large"),
])

# 7. Nairobské slunce — oil painting -------------------------------------------------------------
STORIES["re_07_nairobi"] = story(world("w_re_07_nairobi", "Nairobské slunce",
    "Trenér Marcus „Mo“ s tajnými básněmi a fotografka Wanjiru v parku Uhuru.", "painterly_oil", [
    char("mo", "Mo", "1boy", "mature male, dark-skinned male, very dark skin, muscular, bald, smile",
         {"default": "sportswear, tank top, track pants", "evening": "grey hoodie"},
         "a muscular Black British coach aged 32, shaved head, big smile, sportswear"),
    char("wanjiru", "Wanjiru", "1girl", "adult, dark-skinned female, very dark skin, short hair, dreadlocks, expressive eyes",
         "khaki shirt, camera strap, jeans", "a Kenyan photographer aged 28, short dreadlocks, striking eyes, camera"),
], [
    loc("l_park", "Park Uhuru", "outdoors, uhuru park, nairobi, sunny, running track, fountain"),
    loc("l_cafe", "Kavárna", "indoors, cafe, nairobi, window, photographs on table"),
    loc("l_hills", "Ngong Hills", "outdoors, ngong hills, sunset, valley, wind, golden light"),
]), [
    panel("wide", "l_park", ["mo"], "sprinting, coaching, shouting, sweat, sunny", [("mo", "Ještě jednou! Rychleji!", "shout")]),
    panel("medium", "l_park", ["wanjiru"], "holding camera, water splash on camera, surprised", sfx=["ŠPLÍCH"]),
    panel("medium", "l_park", ["mo"], "apologizing, hands up, embarrassed",
          [("mo", "Promiňte! Zaplatím! Jsem trenér, ne ničitel!")]),
    panel("close-up", "l_park", ["wanjiru"], "smirk, looking at camera screen",
          [("wanjiru", "Klid. Mám to na fotce. Zlato. Smůla vám sluší."), ("mo", "To je nejhorší kompliment… a chci druhý.")], gap="large"),
    panel("medium", "l_cafe", ["mo:evening"], "holding folder of poems, nervous, trembling hands",
          [("mo", "Básničky. Jsem svalovec s básněmi. Ve fitku o tom nikdo neví.")]),
    panel("medium", "l_cafe", ["wanjiru"], "gentle smile, photos on table",
          [("wanjiru", "Každý správný muž má šuplík, který nikdo neotevře. Ale čtěte nahlas.")]),
    panel("close-up", "l_cafe", ["mo:evening"], "reading aloud, eyes closed, soft",
          [N("Hlas, který křičí na stadionu, teď šeptá slova o slunci, které se učí plavat.")], gap="large"),
    panel("wide", "l_hills", ["wanjiru", "mo:evening"], "standing on hill, wind, sunset, valley",
          [("wanjiru", "Hledala jsem muže, který je silný, ale ne tvrdý. Který zvedne činku i mé pochybnosti.")]),
    panel("close-up", "l_hills", ["mo:evening"], "looking at viewer, gentle, golden light",
          [("mo", "A já hledal ženu, která opravdu vidí. Uvidíte mě i v den, kdy nesvedu ani úsměv.")], gap="small"),
    panel("wide", "l_hills", ["wanjiru", "mo:evening"], "kiss, wind, sunset, silhouette", sfx=["CVAK"], gap="large"),
])

# 8. Mastné ruce, čisté srdce — western comic ------------------------------------------------------
STORIES["re_08_miami"] = story(world("w_re_08_miami", "Mastné ruce, čisté srdce",
    "Mechanik Diego z Little Havana nastartuje auto advokátce Carmen, která spěchá k soudu.", "western_comic", [
    char("diego", "Diego", "1boy", "mature male, tan skin, broad shoulders, long hair, ponytail, black hair, sleeve tattoo",
         {"default": "jeans, grease stains, shirt, rolled up sleeves", "clean": "white shirt, open collar, hair down"},
         "a broad-shouldered Mexican mechanic aged 30, tattoo sleeves, long hair in a ponytail"),
    char("carmen", "Carmen", "1girl", "adult, tan skin, black hair, hair bun, brown eyes",
         {"default": "business suit, pencil skirt, blazer", "evening": "summer dress, hair down"},
         "a Cuban-American lawyer aged 30, dark hair in a bun, sharp suit, soft eyes"),
], [
    loc("l_garage", "Little Havana", "outdoors, little havana, miami, vintage car, street garage, sunny"),
    loc("l_coffee", "Calle Ocho", "outdoors, calle ocho, coffee stand, cuban coffee, colorful mural"),
    loc("l_beach", "South Beach", "outdoors, south beach, evening, sand, ocean, distant storm clouds"),
]), [
    panel("wide", "l_garage", ["diego"], "lying under car, only legs visible, tools"),
    panel("medium", "l_garage", ["carmen"], "hurrying, holding briefcase, worried",
          [("carmen", "Pane mechaniku. Moje auto umřelo a já mám jednu hodinu na případ zbytku života.")]),
    panel("medium", "l_garage", ["diego"], "crawling out from under car, greasy, grin, talking to car",
          [("diego", "Hola, bonita. Probouzíme se.")]),
    panel("close-up", "l_garage", ["carmen"], "laughing, surprised",
          [("carmen", "Vy s auty mluvíte španělsky?"), ("diego", "Všechno dobré na světě mluví španělsky.")], sfx=["VRRRM"], gap="large"),
    panel("medium", "l_coffee", ["carmen"], "holding coffee cup, soft smile",
          [("carmen", "Všichni mě vidí jako advokátku. Vy jste řekl ‚žena ve spěchu‘. To bylo… lidské.")]),
    panel("medium", "l_coffee", ["diego"], "holding coffee cup, wiping forehead with handkerchief",
          [("diego", "Hledal jsem ženu, která pozná, že mastné ruce můžou být čisté.")], gap="large"),
    panel("wide", "l_beach", ["diego:clean"], "walking on sand, clean, hair down, evening",
          [("carmen", "Vypadáte jinak.")]),
    panel("close-up", "l_beach", ["carmen:evening"], "smile, wind in hair",
          [("carmen", "Jsem zvyklá vyhrávat spory. Ale s vámi nechci vyhrát. Chci remízu. Napořád.")], gap="small"),
    panel("medium", "l_beach", ["carmen:evening", "diego:clean"], "hug, careful embrace, closed eyes"),
    panel("wide", "l_beach", ["carmen:evening", "diego:clean"], "kiss, sand, ocean, storm clouds on horizon",
          [N("Na obzoru bouřka, která se rozhodne počkat.")], gap="large"),
])

# 9. Klobouk v Praze — ink wash ------------------------------------------------------------------
STORIES["re_09_praha"] = story(world("w_re_09_praha", "Klobouk v Praze",
    "Irský kovboj Sean zabloudí na Náplavku ke keramičce Petře.", "ink_wash", [
    char("sean", "Sean", "1boy", "mature male, tall, beard, brown hair, green eyes, cowboy hat",
         "flannel shirt, jeans", "a tall bearded Irish ranch hand aged 35, brown hair, green eyes, cowboy hat"),
    char("petra", "Petra", "1girl", "adult, curly hair, dark brown hair, freckles, brown eyes",
         "dress with pockets, apron", "a Czech ceramicist aged 32, dark curly hair, freckles, dress with tool pockets"),
], [
    loc("l_river", "Náplavka", "outdoors, prague, riverbank, vltava, potter's wheel, clay"),
    loc("l_workshop", "Dílna", "indoors, pottery workshop, fireplace, shelves with mugs, potter's wheel"),
    loc("l_bridge", "Karlův most", "outdoors, charles bridge, statues, dusk, prague castle"),
]), [
    panel("wide", "l_river", ["sean"], "holding map, lost, cowboy hat, looking around"),
    panel("medium", "l_river", ["petra"], "shaping clay, looking up, amused",
          [("petra", "Pane. Klobouk dovnitř nenosíme. Praha je vysoká.")]),
    panel("medium", "l_river", ["sean"], "confused, scratching head",
          [("sean", "Nejdřív jsem šel rovně. Teď jsem tady. Kde je tady?")]),
    panel("close-up", "l_river", ["petra"], "smile, clay on hands",
          [("petra", "Nejhezčí místo, které jste mohl ztratit. Sedněte si.")], gap="large"),
    panel("medium", "l_workshop", ["sean"], "using potter's wheel, clay splashing on hat, clumsy", sfx=["ČVACHT"],
          bubbles=[("sean", "V Irsku hlína poslouchá.")]),
    panel("medium", "l_workshop", ["petra"], "standing by fireplace, arms crossed, smile",
          [("petra", "Hlína nikde neposlouchá. Hlína naslouchá. Zkuste to znovu. Pomaleji.")]),
    panel("close-up", "l_workshop", ["sean"], "holding small ugly bowl, moved, proud",
          [("sean", "První věc, kterou jsem v životě vyrobil rukama.")], gap="large"),
    panel("wide", "l_bridge", ["petra", "sean"], "walking, statues, dusk, man holding hat in hand",
          [("petra", "Sundal jste klobouk."), ("sean", "Řekl jsem skoro nikdy. Jste ten rozdíl mezi skoro a vždycky.")]),
    panel("close-up", "l_bridge", ["sean"], "looking at viewer, gentle",
          [("sean", "Hledal jsem ženu, která mě naučí dělat věci pomalu. Našel jsem tři najednou. Všechny se jmenují Petra.")], gap="small"),
    panel("medium", "l_bridge", ["petra", "sean"], "kiss, statues, dusk, cowboy hat on ground, closed eyes", gap="large"),
])

# 10. Boxerův deník — clean webtoon ---------------------------------------------------------------
STORIES["re_10_jakarta"] = story(world("w_re_10_jakarta", "Boxerův deník",
    "Boxer Arjun z Bombaje a novinářka Sari, která našla jeho deník.", "clean_webtoon", [
    char("arjun", "Arjun", "1boy", "mature male, indian, brown skin, short hair, black hair, scar on chin, athletic",
         {"default": "tank top, track pants, boxing wraps", "evening": "white t-shirt, pants"},
         "an Indian boxer aged 29, short black hair, scar on his chin, quick hands"),
    char("sari", "Sari", "1girl", "adult, asian, tan skin, black hair, blunt bangs, medium hair, calm eyes",
         "blouse, cardigan, holding notebook", "an Indonesian journalist aged 29, black hair with blunt bangs, calm gaze, notebook"),
], [
    loc("l_gym", "Tělocvična", "indoors, old boxing gym, punching bag, jakarta, dim light"),
    loc("l_canal", "Kavárna u kanálu", "outdoors, cafe by canal, jakarta, evening, string lights"),
    loc("l_roof", "Střecha", "outdoors, rooftop, jakarta skyline, mosque, skyscrapers, dusk"),
]), [
    panel("wide", "l_gym", ["arjun"], "punching bag, boxing, sweat", sfx=["BUM! BUM!"]),
    panel("medium", "l_gym", ["sari"], "standing in doorway, holding notebook, calm",
          [("sari", "Arjun Mehta? Vím, že jste se rozhodl nemluvit. Proto jsem přišla mluvit první.")]),
    panel("medium", "l_gym", ["arjun"], "stops punching, turning around, wary",
          [("arjun", "Novinářky mluví. Boxeři drží stráž.")]),
    panel("close-up", "l_gym", ["sari"], "slight smile, holding diary",
          [("sari", "Vstával jste sedmkrát. Váš deník jste nechal v knihovně v Bombaji. Špatně skrývaný, výborně psaný.")], gap="large"),
    panel("medium", "l_canal", ["arjun:evening"], "embarrassed, blush, hand on neck",
          [("arjun", "To bylo soukromé. I to o ‚ní‘.")]),
    panel("medium", "l_canal", ["sari"], "soft smile, string lights",
          [("sari", "O ní jste psal osmnáct stran. Nejstatečnější a nejsmutnější čtení mého roku.")]),
    panel("close-up", "l_canal", ["arjun:evening"], "looking at viewer, earnest",
          [("arjun", "Psal jsem o ženě, která existuje jen v hlavě. A pak jste vešla s mým deníkem.")], gap="large"),
    panel("medium", "l_roof", ["arjun:evening"], "holding new diary, writing, dusk",
          [("arjun", "Deník jedna: ‚Záznamy o ní.‘ Deník dva: ‚Záznamy s ní.‘ Rozdíl je celý život.")]),
    panel("medium", "l_roof", ["sari", "arjun:evening"], "looking at diary together, skyline",
          [("sari", "První záznam?"), ("arjun", "Dnes jsem prohrál rány, ale vyhrál večer. Vstal jsem poosmé.")], gap="small"),
    panel("close-up", "l_roof", ["sari", "arjun:evening"], "kiss, closed eyes, dusk, skyline",
          [("sari", "To bude titul.", "thought")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
