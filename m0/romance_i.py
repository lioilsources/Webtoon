"""Romance set I — ten fashion stories ("Níže je 10 scénářů pro dospělé publikum… MÓDNÍ PROLOG…").

    python3 m0/romance_i.py        → data/stories/ri_*/{world,storyboard}.json

Same building blocks and rules as stories_romance.py: one medium per story, dialogue near-verbatim (typos fixed),
inner monologue as thought bubbles, never two characters of the same gender in one panel. Fashion is the theme,
so every lead has named outfits; brand names from the source are replaced by a description of the look. The
source's bedroom scenes ("pomalé odhazování… fade to black") become a kiss, a closed door and a dressed morning.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}


def ending(w, text):
    w["canon"]["constraints"] = [text]
    return w


# 1. Tokio — night neon photoreal ------------------------------------------------------------------
STORIES["ri_01_tokio"] = story(ending(world("w_ri_01_tokio", "Tokio – Módní týden",
    "Vizážistka Klára si mezi modelkami v Tokiu připadá navíc, dokud ji tichý Haruto neuvidí jinak.", "photo_cyberreal_night", [
    char("klara", "Klára", "1girl", "adult, mature female, petite, slender, short hair, bob cut, copper hair, green eyes, glasses",
         {"default": "beige trench coat, black turtleneck, thigh boots, round glasses",
          "work": "black apron, black blouse, makeup brush, round glasses",
          "evening": "little black dress, black pumps, gold earrings, round glasses"},
         "a petite slender Czech woman aged 29, copper bob haircut, green eyes, round tortoiseshell glasses"),
    char("haruto", "Haruto", "1boy", "mature male, slender, short hair, black hair, neat hair, dark eyes, glasses",
         {"default": "dark navy suit, white shirt, thin black necktie, glasses",
          "nojacket": "white shirt, rolled sleeves, loosened necktie, glasses"},
         "a slender Japanese office worker aged 32, neat black hair, thin-rimmed glasses"),
], [
    loc("l_backstage", "Backstage přehlídky", "indoors, fashion show backstage, mirrors with lights, clothing racks, gold dresses, models in background, busy"),
    loc("l_bar", "Hotelový bar", "indoors, hotel bar, night, city view window, tokyo skyline, cocktail glass, dim warm light"),
    loc("l_shibuya", "Šibuja", "outdoors, shibuya crossing, tokyo, night, rain, neon signs, wet street, reflections, umbrellas"),
    loc("l_room", "Hotelový pokoj", "indoors, hotel room entrance, door, night, city lights through window, dim lamp"),
]), "Dobrý konec: zůstanou spolu."), [
    panel("establishing", "l_backstage", [], "fashion week, gold dresses on racks, hairspray mist", [N("Tokio. Týden módy.")]),
    panel("medium", "l_backstage", ["klara:work"], "holding makeup brush, doing makeup, concentrated, mirror lights",
          [("klara", "Mezi modelkami jsem jen ta malá s štětcem.", "thought")]),
    panel("medium", "l_backstage", ["haruto"], "holding documents, looking around, polite, lost",
          [("haruto", "Promiňte, nevíte, kde je pan Tanaka?")]),
    panel("medium", "l_backstage", ["klara:work", "haruto"], "talking, woman pointing to the left, man smiling",
          [("klara", "Já jsem jen vizážistka. Ale zkuste chodbu vlevo."),
           ("haruto", "Vy nejste jen vizážistka. Máte nejklidnější ruce v celé místnosti.")], gap="large"),
    panel("medium", "l_bar", ["klara:evening", "haruto:nojacket"], "sitting at bar, cocktail glasses, city view, talking",
          [("klara", "V Tokiu si připadám moc kulatá."), ("haruto", "A já moc nudný. Přesto tu sedíme spolu.")]),
    panel("close-up", "l_bar", ["klara:evening"], "small smile, looking down, glass in hand", [("klara", "To je pravda.")], gap="large"),
    panel("wide", "l_shibuya", ["klara", "haruto"], "rain, man holding umbrella over woman, neon reflections",
          [("haruto", "Kláro, můžu vás pozvat zítra? Na procházku a večeři.")]),
    panel("close-up", "l_shibuya", ["klara"], "smile, rain, neon light on face, under umbrella",
          [("klara", "Ano. Ale vezmu si kozačky.")], gap="large"),
    panel("medium", "l_room", ["klara:evening", "haruto:nojacket"], "standing at door, embrace, looking at each other, night",
          [N("Druhý večer. Trenčkot zůstane na věšáku, kozačky u dveří.")]),
    panel("medium", "l_room", ["klara:evening", "haruto:nojacket"], "kiss, closed eyes, tender, dim light", gap="small"),
    panel("establishing", "l_room", [], "closed door, light under door, dark corridor, night", [N("Dveře se zavřou. Tokio svítí dál.")], gap="large"),
])

# 2. Santorini — photoreal --------------------------------------------------------------------------
STORIES["ri_02_santorini"] = story(ending(world("w_ri_02_santorini", "Santorini – Resort",
    "Nora přijela na Santorini na týden a plavčík Nikos jí ukáže nejlepší gyros i to, že léto nemusí trvat věčně.", "photo_juggernaut", [
    char("nora", "Nora", "1girl", "adult, curvy, dark-skinned female, dark skin, afro, black hair, brown eyes",
         {"default": "white linen shirt dress, straw hat, sandals, gold hoop earrings",
          "sunset": "emerald silk wrap dress, gold hoop earrings, gold bangles",
          "night": "white linen shirt dress, gold hoop earrings, barefoot"},
         "a curvy Black British woman aged 30, natural afro hair, warm brown eyes"),
    char("nikos", "Nikos", "1boy", "mature male, athletic, tan, short hair, black hair, stubble, brown eyes",
         {"default": "white t-shirt, red shorts, whistle",
          "evening": "white linen shirt, beige chinos"},
         "an athletic Greek lifeguard aged 33, short black hair, stubble, sun-tanned"),
], [
    loc("l_beach", "Pláž", "outdoors, beach, black sand, blue sea, sunny, beach umbrella, santorini"),
    loc("l_terrace", "Terasa", "outdoors, terrace, white houses, blue domes, caldera view, sunset, wine glasses"),
    loc("l_nightbeach", "Noční pláž", "outdoors, beach, night, stars, moonlight, calm sea"),
    loc("l_bungalow", "Bungalov", "outdoors, white bungalow door, night, lantern, bougainvillea"),
    loc("l_morning", "Ráno v bungalovu", "indoors, white room, morning light, linen curtains, seashell on pillow, sea view"),
]), "Hořkosladký konec: letní romance skončí, zůstane vzpomínka."), [
    panel("wide", "l_beach", ["nora"], "sitting under beach umbrella, reading book, straw hat"),
    panel("medium", "l_beach", ["nikos"], "running, reaching out, apologetic smile", [("nikos", "Promiň! Můžeš hodit?")], sfx=["BUM"]),
    panel("medium", "l_beach", ["nora", "nikos"], "woman holding ball, playful smile, man standing",
          [("nora", "Jen když mi řekneš, kde je nejlepší gyros."), ("nikos", "To ti ukážu sám.")], gap="large"),
    panel("wide", "l_terrace", ["nora:sunset", "nikos:evening"], "sitting at table, wine glasses, sunset, caldera",
          [("nora", "Za týden odjíždím.")]),
    panel("close-up", "l_terrace", ["nikos:evening"], "honest, soft smile, sunset light",
          [("nikos", "Já vím. Nechci to pokazit tím, že si budu hrát na něco trvalého.")]),
    panel("close-up", "l_terrace", ["nora:sunset"], "smile, gold earrings, sunset", [("nora", "Tak to nehrajme.")], gap="large"),
    panel("wide", "l_nightbeach", ["nora:night", "nikos:evening"], "walking, holding hands, barefoot, stars",
          [("nikos", "Noro, jsi nejkrásnější člověk, kterého jsem tu potkal."), ("nora", "A ty nejlepší plavčík.")]),
    panel("medium", "l_bungalow", ["nora:night", "nikos:evening"], "kiss, embrace, lantern light, night", gap="small"),
    panel("establishing", "l_bungalow", [], "closed door, lantern, night, bougainvillea", [N("Dveře bungalovu se zavřou.")], gap="large"),
    panel("medium", "l_morning", ["nora:night"], "sitting, holding seashell, reading note, morning light, bittersweet smile",
          [N("Ráno je jeho strana prázdná. Na polštáři lastura a vzkaz."), ("", "„Bylo to krásné. Nikos.“", "narration")]),
    panel("close-up", "l_morning", ["nora:night"], "smile, tear, holding seashell, sea view", gap="large"),
])

# 3. Norské fjordy — thin paint ----------------------------------------------------------------------
STORIES["ri_03_fjordy"] = story(ending(world("w_ri_03_fjordy", "Norské fjordy – Jachta",
    "Fotografka Tamara si na palubě připadá jako věž, kapitán Erik se podle ní orientuje jako podle majáku.", "thin_paint", [
    char("tamara", "Tamara", "1girl", "adult, tall female, athletic, tan skin, long hair, black hair, brown eyes",
         {"default": "long camel wool coat, black turtleneck, knee boots, sunglasses",
          "cozy": "oversized cream knit sweater, wool blanket, black leggings",
          "dinner": "deep red knit dress, long gold earrings, knee boots"},
         "a tall athletic Brazilian woman aged 31, long straight black hair, camel coat and knee boots"),
    char("erik", "Erik", "1boy", "mature male, muscular, beard, blonde hair, short hair, blue eyes",
         {"default": "navy cable knit fisherman sweater, beanie, dark jeans",
          "evening": "grey henley shirt, dark jeans"},
         "a muscular Norwegian yacht captain aged 35, short blond hair, full beard, navy fisherman sweater"),
], [
    loc("l_deck", "Paluba", "outdoors, yacht deck, fjord, steep cliffs, waterfall, cold, overcast, sea"),
    loc("l_salon", "Salonek", "indoors, yacht cabin lounge, wooden interior, blankets, wine, guitar, lamp, evening"),
    loc("l_fog", "Ranní mlha", "outdoors, yacht deck, morning fog, fjord, coffee mugs, calm water"),
    loc("l_cabin", "Kajuta", "indoors, yacht cabin door, porthole, night, warm lamp"),
]), "Dobrý konec: Tamara zůstává."), [
    panel("establishing", "l_deck", [], "yacht on fjord, cliffs, waterfall", [N("Norské fjordy.")]),
    panel("medium", "l_deck", ["tamara"], "holding camera, taking photo, wind, hair blowing"),
    panel("medium", "l_deck", ["tamara", "erik"], "man at steering wheel, woman lowering camera, looking at each other",
          [("tamara", "Nevypadám tu trochu jako věž?"), ("erik", "Vypadáš jako maják. A já se podle tebe orientuju.")]),
    panel("close-up", "l_deck", ["tamara"], "laughing, wind", [("tamara", "To je hodně kapitánská odpověď.")], gap="large"),
    panel("medium", "l_salon", ["erik:evening"], "playing guitar, sitting, warm lamp light"),
    panel("medium", "l_salon", ["tamara:cozy", "erik:evening"], "sitting on sofa, blanket, wine glasses, looking at each other",
          [("erik", "Tamaro, zůstaň ještě den. Nebo dva."), ("tamara", "Mám letenku."), ("erik", "Já mám loď.")], gap="large"),
    panel("wide", "l_fog", ["tamara:cozy", "erik"], "morning fog, man handing coffee mug, steam",
          [("tamara", "Tak jo. Zůstávám."), ("erik", "To je nejlepší zpráva pro kapitána.")], gap="large"),
    panel("medium", "l_cabin", ["tamara:dinner", "erik:evening"], "embrace, standing at cabin door, warm lamp",
          [N("Kabát na háčku, kozačky pod lavicí.")]),
    panel("medium", "l_cabin", ["tamara:dinner", "erik:evening"], "kiss, closed eyes, porthole, night", gap="small"),
    panel("establishing", "l_cabin", [], "porthole, moonlight on fjord, lamp turned off, darkness", [N("Lampa zhasne.")], gap="large"),
])

# 4. Marrákeš — oil painting ------------------------------------------------------------------------
STORIES["ri_04_marrakes"] = story(ending(world("w_ri_04_marrakes", "Marrákeš – Spa",
    "Sára hledá v Marrákeši klid, mechanik Karim jí nejdřív nabídne čaj a pak kus srdce, které si neodveze.", "painterly_oil", [
    char("sara", "Sára", "1girl", "adult, curvy, red hair, long hair, wavy hair, freckles, green eyes, pale skin",
         {"default": "emerald silk midi dress, low heels, gold necklace, sunglasses on head",
          "robe": "white bathrobe, hair towel",
          "night": "black silk evening dress, gold necklace, pumps"},
         "a curvy Czech woman aged 28, long wavy red hair, freckles, emerald silk dress"),
    char("karim", "Karim", "1boy", "mature male, muscular, tan, short hair, black hair, stubble, dark eyes",
         {"default": "brown leather jacket, white t-shirt, jeans, oil stains",
          "evening": "white linen shirt, dark trousers"},
         "a muscular Moroccan mechanic aged 34, short black hair, stubble, brown leather jacket"),
], [
    loc("l_souk", "Trh", "outdoors, marrakesh souk, market stalls, lanterns, spices, jewelry stall, scooter, sunny"),
    loc("l_spa", "Spa", "indoors, moroccan spa, hammam, tiles, mosaic, steam, arches"),
    loc("l_pool", "Bazén v riadu", "outdoors, riad courtyard, pool, orange trees, lanterns, evening, mosaic tiles"),
    loc("l_door", "Dveře pokoje", "indoors, riad corridor, carved wooden door, lanterns, night"),
    loc("l_street", "Ulice ráno", "outdoors, marrakesh street, morning, taxi, red walls, suitcase"),
]), "Smutný konec: rozejdou se."), [
    panel("wide", "l_souk", ["sara"], "looking at jewelry stall, holding necklace"),
    panel("medium", "l_souk", ["karim"], "repairing scooter, kneeling, wrench, looking up"),
    panel("medium", "l_souk", ["sara", "karim"], "talking, man standing up, wiping hands",
          [("sara", "Nevíte, kde je spa?"), ("karim", "Vím. Ale nejdřív si dejte čaj.")]),
    panel("medium", "l_souk", ["sara", "karim"], "mint tea glasses, smiling, playful",
          [("sara", "To je vydírání."), ("karim", "To je pohostinnost.")], gap="large"),
    panel("medium", "l_spa", ["sara:robe"], "sitting, steam, relaxed, mosaic tiles",
          [("karim", "Proč tady vlastně jste?"), ("sara", "Hledám klid.")]),
    panel("medium", "l_spa", ["karim"], "leaning at arch, holding wrench, smile", [("karim", "Opravuju skútr majitele. A vy?")], gap="large"),
    panel("wide", "l_pool", ["sara:night", "karim:evening"], "sitting by pool, lanterns, talking, woman laughing"),
    panel("close-up", "l_pool", ["karim:evening"], "serious, lantern light", [("karim", "Sáro, jsi krásná.")]),
    panel("close-up", "l_pool", ["sara:night"], "teasing smile, lantern light",
          [("sara", "To říkáš každé turistce?"), ("karim", "Ne. Ale ty odjíždíš.")], gap="large"),
    panel("medium", "l_door", ["sara:night", "karim:evening"], "kiss, embrace, carved door, lanterns", gap="small"),
    panel("establishing", "l_door", [], "carved wooden door closed, lantern, night", [N("Dveře se zavřou.")], gap="large"),
    panel("wide", "l_street", ["sara", "karim"], "woman in taxi window, man waving from distance, morning",
          [N("Ráno Sára odjíždí. Karim mává z dálky. Nedá se nic dělat.")], gap="large"),
])

# 5. Soul — retro city pop ---------------------------------------------------------------------------
STORIES["ri_05_soul"] = story(ending(world("w_ri_05_soul", "Soul – Kavárna a deska",
    "Stážistka Jana pije jen čaj a boxer Minho s monoklem jí to celé obrátí.", "retro_citypop", [
    char("jana", "Jana", "1girl", "adult, mature female, petite, slender, long hair, straight hair, black hair, blunt bangs, glasses, brown eyes",
         {"default": "long camel coat, white blouse, knee boots, glasses",
          "casual": "cream cardigan, pleated skirt, knee boots, glasses"},
         "a petite Czech woman aged 27, straight black hair with blunt bangs, glasses, camel coat"),
    char("minho", "Minho", "1boy", "mature male, athletic, muscular, short hair, black hair, dark eyes",
         {"default": "black track jacket, white t-shirt, black jeans",
          "bruised": "black track jacket, white t-shirt, black eye, bandage on cheek"},
         "an athletic Korean boxer aged 30, short black hair, black track jacket"),
], [
    loc("l_cafe", "Kavárna", "indoors, cafe, seoul, laptop, tea cup, window, plants, daytime"),
    loc("l_roof", "Střecha", "outdoors, rooftop, seoul skyline, evening, string lights, city lights"),
    loc("l_market", "Noční trh", "outdoors, night market, street food stalls, lanterns, crowd, seoul"),
    loc("l_door", "Dveře bytu", "indoors, apartment door, night, warm lamp, shoes at entrance"),
]), "Dobrý konec: zůstanou spolu."), [
    panel("medium", "l_cafe", ["jana"], "typing on laptop, tea cup, concentrated, glasses"),
    panel("medium", "l_cafe", ["jana", "minho"], "man standing at table, woman looking up",
          [("minho", "Můžeš mi doporučit?"), ("jana", "Já piju jen čaj."), ("minho", "Tak mi doporuč čaj.")], gap="large"),
    panel("wide", "l_roof", ["jana:casual", "minho:bruised"], "sitting on rooftop, city skyline, evening"),
    panel("medium", "l_roof", ["jana:casual", "minho:bruised"], "woman pointing at his black eye, both laughing",
          [("jana", "Boxer s monoklem."), ("minho", "A ty s brýlemi. Sedíme si.")], gap="large"),
    panel("wide", "l_market", ["jana", "minho"], "eating street food, lanterns, smiling"),
    panel("medium", "l_market", ["jana", "minho"], "man giving rose, woman holding rose, blush",
          [("minho", "Jano, zůstaň se mnou."), ("jana", "Zůstanu.")], gap="large"),
    panel("medium", "l_door", ["jana", "minho"], "embrace, apartment entrance, coat on hook, boots by door",
          [N("Kabát na věšák, kozačky ke dveřím.")]),
    panel("medium", "l_door", ["jana", "minho"], "kiss, closed eyes, warm lamp", gap="small"),
    panel("establishing", "l_door", [], "city lights through window, night, seoul, lamp off", [N("Soul za oknem svítí dál.")], gap="large"),
])

# 6. Švýcarské Alpy — fantasy colour lines ----------------------------------------------------------
STORIES["ri_06_alpy"] = story(ending(world("w_ri_06_alpy", "Švýcarské Alpy – Horská chata",
    "Marek si připadá jako medvěd, lyžařka Elise mu ukáže, že je víc než svaly.", "fantasy_colorlines", [
    char("marek", "Marek", "1boy", "mature male, muscular, broad shoulders, short hair, brown hair, brown eyes",
         {"default": "brown leather jacket, grey wool sweater, hiking boots",
          "sweater": "grey wool sweater, dark jeans"},
         "a muscular Czech man aged 34, short brown hair, leather jacket over grey wool sweater"),
    char("elise", "Elise", "1girl", "adult, tall female, athletic, slender, long hair, blonde hair, blue eyes",
         {"default": "white long wool coat, white knit hat, knee boots, silver earrings",
          "ski": "red ski jacket, white ski pants, goggles on head",
          "evening": "cream knit dress, silver necklace, knee boots"},
         "a tall athletic Swiss woman aged 30, long blond hair, white wool coat and knee boots"),
], [
    loc("l_gondola", "Lanovka", "indoors, cable car cabin, window, snowy mountains, alps, sunny"),
    loc("l_chalet", "Chata", "indoors, mountain chalet, fireplace, wooden walls, wine glasses, guitar, evening"),
    loc("l_slope", "Svah", "outdoors, ski slope, snow, alps, morning, blue sky, skis"),
    loc("l_door", "Dveře pokoje", "indoors, chalet corridor, wooden door, night, lamp"),
]), "Dobrý konec: zůstanou spolu."), [
    panel("establishing", "l_gondola", [], "cable car over snowy mountains, alps", [N("Švýcarské Alpy.")]),
    panel("medium", "l_gondola", ["marek", "elise"], "sitting in cable car, looking at each other",
          [("marek", "Nevypadám tu trochu jako medvěd?"), ("elise", "Jako medvěd, který se nebojí výšek.")]),
    panel("close-up", "l_gondola", ["elise"], "teasing smile", [("marek", "To je kompliment?"), ("elise", "To je fakt.")], gap="large"),
    panel("medium", "l_chalet", ["marek:sweater"], "playing guitar, fireplace, warm light"),
    panel("medium", "l_chalet", ["marek:sweater", "elise:evening"], "sitting by fireplace, wine glasses, looking at each other",
          [("elise", "Mareku, zůstaň do zítra."), ("marek", "Zůstanu.")], gap="large"),
    panel("wide", "l_slope", ["marek", "elise:ski"], "snow, woman handing glove, smiling",
          [("elise", "Naučím tě lyžovat."), ("marek", "A já tě naučím, jak se nebát.")], gap="large"),
    panel("medium", "l_door", ["marek:sweater", "elise:evening"], "embrace, wooden door, lamp light",
          [N("Bunda, kozačky a šperky zůstanou v předsíni.")]),
    panel("medium", "l_door", ["marek:sweater", "elise:evening"], "kiss, closed eyes, tender", gap="small"),
    panel("establishing", "l_door", [], "snowy window, night, stars over alps, lamp off", [N("Nad Alpami se rozsvítí hvězdy.")], gap="large"),
])

# 7. Bali — watercolour --------------------------------------------------------------------------------
STORIES["ri_07_bali"] = story(ending(world("w_ri_07_bali", "Bali – Plážový resort",
    "Úředník David bloudí mezi rýžovými terasami, Ayu ho zachrání před deštěm a naučí tančit.", "watercolor_paris", [
    char("david", "David", "1boy", "mature male, dark-skinned male, dark skin, slender, short hair, black hair, glasses",
         {"default": "light blue button-up shirt, beige chinos, glasses",
          "evening": "white linen shirt, beige chinos, glasses, sandals"},
         "a slender African American office worker aged 32, short black hair, glasses, light blue shirt"),
    char("ayu", "Ayu", "1girl", "adult, mature female, petite, curvy, tan skin, long hair, black hair, brown eyes",
         {"default": "floral sundress, sandals, frangipani in hair",
          "dance": "golden sarong dress, gold bracelets, frangipani in hair",
          "travel": "white blouse, long floral skirt, straw bag"},
         "a petite curvy Indonesian woman aged 28, long black hair with a frangipani flower, floral sundress"),
], [
    loc("l_rice", "Rýžové terasy", "outdoors, rice terraces, bali, palm trees, rain clouds, green, misty"),
    loc("l_beach", "Pláž", "outdoors, beach, bonfire, night, music, torches, ocean"),
    loc("l_resto", "Restaurace", "outdoors, beach restaurant, candles, lanterns, night, flowers on table"),
    loc("l_bungalow", "Bungalov", "outdoors, bali bungalow door, lanterns, night, palm leaves"),
    loc("l_morning", "Ráno", "outdoors, bungalow terrace, morning, ocean view, seashell"),
]), "Hořkosladký konec: Ayu odjíždí, David zůstává."), [
    panel("wide", "l_rice", ["david"], "lost, holding phone, looking around, rain starting"),
    panel("medium", "l_rice", ["ayu", "david"], "woman holding big banana leaf over man, rain",
          [("ayu", "Vy jste z resortu?"), ("david", "Ano. A vy?"), ("ayu", "Já jsem tady doma.")], gap="large"),
    panel("wide", "l_beach", ["ayu:dance"], "dancing, bonfire, torches, night"),
    panel("medium", "l_beach", ["ayu:dance", "david:evening"], "woman taking man's hands, dancing, awkward, laughing",
          [("david", "Já neumím tančit."), ("ayu", "Já tě naučím.")], gap="large"),
    panel("medium", "l_resto", ["ayu", "david:evening"], "man giving flower, candles, smile",
          [("david", "Ayu, zůstaň se mnou do konce týdne."), ("ayu", "Zůstanu.")], gap="large"),
    panel("medium", "l_bungalow", ["ayu", "david:evening"], "kiss, embrace, lanterns, night", gap="small"),
    panel("establishing", "l_bungalow", [], "closed bungalow door, lanterns, palm leaves, night", [N("Dveře se zavřou.")], gap="large"),
    panel("medium", "l_morning", ["ayu:travel", "david:evening"], "woman with straw bag leaving, man standing on terrace, morning",
          [N("Ráno Ayu odjíždí za rodinou.")]),
    panel("close-up", "l_morning", ["david:evening"], "holding seashell, sad smile, ocean", gap="large"),
])

# 8. Dubaj — western comic ---------------------------------------------------------------------------
STORIES["ri_08_dubaj"] = story(ending(world("w_ri_08_dubaj", "Dubaj – Jachta",
    "Mechanik Omar hledá na veletrhu jachtu pana Hamada a najde Lilu.", "western_comic", [
    char("omar", "Omar", "1boy", "mature male, muscular, beard, short hair, black hair, tan, dark eyes, sunglasses",
         {"default": "crisp white shirt, dark trousers, aviator sunglasses",
          "evening": "black shirt, dark trousers, silver watch"},
         "a muscular Moroccan mechanic aged 35, short black hair, beard, crisp white shirt and aviators"),
    char("lila", "Lila", "1girl", "adult, tall female, athletic, long hair, black hair, wavy hair, brown eyes",
         {"default": "beige wrap dress, stiletto heels, gold jewelry, sunglasses",
          "evening": "black satin evening gown, gold earrings, stiletto heels"},
         "a tall athletic Iranian woman aged 30, long wavy black hair, beige wrap dress and gold jewelry"),
], [
    loc("l_marina", "Marina", "outdoors, dubai marina, yachts, skyscrapers, sunny, palm trees, luxury car"),
    loc("l_yacht", "Jachta", "indoors, luxury yacht lounge, champagne glasses, evening, city lights through windows"),
    loc("l_deck", "Paluba", "outdoors, yacht deck, night, stars, dubai skyline, city lights"),
    loc("l_cabin", "Kajuta", "indoors, yacht cabin door, night, warm light"),
]), "Dobrý konec: zůstanou spolu."), [
    panel("establishing", "l_marina", [], "yachts, skyscrapers, sunny", [N("Dubaj. Marina.")]),
    panel("medium", "l_marina", ["omar"], "looking around, holding paper, confused, sunglasses"),
    panel("medium", "l_marina", ["lila", "omar"], "woman stepping out of luxury car, man turning to her",
          [("omar", "Nevíte, kde je jachta pana Hamada?"),
           ("lila", "Vím. Ale nejdřív mi řekněte, proč máte na veletrh tak dokonalou košili.")]),
    panel("close-up", "l_marina", ["omar"], "grin, confident", [("omar", "Protože mi sluší.")], gap="large"),
    panel("medium", "l_yacht", ["lila:evening", "omar:evening"], "champagne glasses, city lights, smiling",
          [("lila", "Omare, zůstaň na večeři."), ("omar", "Zůstanu.")], gap="large"),
    panel("wide", "l_deck", ["lila:evening", "omar:evening"], "man giving rose, stars, skyline",
          [("omar", "Lilo, jsi nejkrásnější žena v Dubaji."), ("lila", "A ty nejlepší mechanik.")], gap="large"),
    panel("medium", "l_cabin", ["lila:evening", "omar:evening"], "embrace, cabin door, warm light",
          [N("Brýle, lodičky a šperky na stolku.")]),
    panel("medium", "l_cabin", ["lila:evening", "omar:evening"], "kiss, closed eyes", gap="small"),
    panel("establishing", "l_deck", [], "dubai skyline at night, yacht lights, calm water", [N("Dubaj svítí až do rána.")], gap="large"),
])

# 9. Toskánsko — semi-real 2.5D ----------------------------------------------------------------------
STORIES["ri_09_toskansko"] = story(ending(world("w_ri_09_toskansko", "Toskánsko – Cyklistická trasa",
    "Cyklista Jakub píchne mezi vinicemi, Giulia mu podá vodu a na jednu noc i domov.", "semireal_25d", [
    char("jakub", "Jakub", "1boy", "mature male, athletic, slender, short hair, dark hair, brown eyes",
         {"default": "cycling jersey, cycling shorts, sport sunglasses, helmet",
          "evening": "white linen shirt, dark jeans"},
         "an athletic Czech cyclist aged 33, short dark hair, cycling jersey and sport sunglasses"),
    char("giulia", "Giulia", "1girl", "adult, curvy, red hair, long hair, wavy hair, freckles, green eyes",
         {"default": "yellow summer dress, sandals, gold earrings, bicycle basket",
          "evening": "terracotta linen dress, gold necklace, sandals"},
         "a curvy Italian woman aged 29, long wavy red hair, freckles, yellow summer dress"),
], [
    loc("l_path", "Cyklostezka", "outdoors, tuscany, gravel road, cypress trees, vineyard, rolling hills, sunny, bicycle"),
    loc("l_inn", "Penzion", "indoors, italian guesthouse, stone walls, pasta, wine, evening, warm light"),
    loc("l_vineyard", "Vinice v noci", "outdoors, vineyard, night, moonlight, stars, tuscany"),
    loc("l_door", "Dveře pokoje", "indoors, stone corridor, wooden door, night, lamp"),
    loc("l_morning", "Ráno", "outdoors, tuscany, gravel road, morning, mist, cypress trees"),
]), "Smutný konec: Jakub odjíždí."), [
    panel("wide", "l_path", ["jakub"], "kneeling by bicycle, flat tire, frustrated"),
    panel("medium", "l_path", ["giulia", "jakub"], "woman on bicycle stopping, man looking up",
          [("giulia", "Potřebuješ pumpu?"), ("jakub", "Potřebuju hlavně vodu."), ("giulia", "Tak pojď.")], gap="large"),
    panel("medium", "l_inn", ["giulia:evening", "jakub:evening"], "sitting at table, pasta, wine, warm light",
          [("jakub", "Zítra jedu dál."), ("giulia", "Já vím. Ale dnes zůstaň.")], gap="large"),
    panel("wide", "l_vineyard", ["giulia:evening", "jakub:evening"], "walking, holding hands, moonlight"),
    panel("medium", "l_vineyard", ["giulia:evening", "jakub:evening"], "kiss, moonlight", gap="small"),
    panel("medium", "l_vineyard", ["giulia:evening", "jakub:evening"], "looking at each other, sad",
          [("giulia", "Jakube, nechceš zůstat?"), ("jakub", "Musím jet.")], gap="large"),
    panel("establishing", "l_door", [], "wooden door closed, lamp, stone corridor, night", [N("Ještě jedna noc.")], gap="large"),
    panel("wide", "l_morning", ["jakub", "giulia"], "man riding bicycle away, woman waving, morning mist",
          [N("Ráno Jakub odjíždí. Giulia mává.")]),
    panel("close-up", "l_morning", ["giulia"], "sad smile, tear, morning light", gap="large"),
])

# 10. Kapské Město — flat minimalism ------------------------------------------------------------------
STORIES["ri_10_kapske_mesto"] = story(ending(world("w_ri_10_kapske_mesto", "Kapské Město – Les a hora",
    "Michaela hledá v lese cestu a boxer Thabo jí ji ukáže až na Stolovou horu.", "minimal_flat", [
    char("thabo", "Thabo", "1boy", "mature male, dark-skinned male, very dark skin, muscular, short dreadlocks, black hair, brown eyes",
         {"default": "black sport jacket, white t-shirt, running shorts, sneakers",
          "evening": "olive overshirt, white t-shirt, dark jeans"},
         "a muscular South African boxer aged 34, short dreadlocks, black sport jacket"),
    char("michaela", "Michaela", "1girl", "adult, tall female, athletic, slender, long hair, blonde hair, blue eyes",
         {"default": "beige trench coat, white t-shirt, jeans, ankle boots, sunglasses on head, camera",
          "evening": "white knit sweater dress, knee boots, gold necklace"},
         "a tall athletic Czech woman aged 30, long blond hair, beige trench coat and camera"),
], [
    loc("l_forest", "Les", "outdoors, forest, trail, tall trees, sunlight, ferns, south africa"),
    loc("l_mountain", "Stolová hora", "outdoors, table mountain, viewpoint, cape town, ocean, sunset, clouds"),
    loc("l_cabin", "Chata", "indoors, wooden cabin, fireplace, drum, evening, warm light"),
    loc("l_door", "Dveře pokoje", "indoors, cabin door, night, lamp"),
]), "Dobrý konec: zůstanou spolu."), [
    panel("wide", "l_forest", ["michaela"], "holding camera, taking photo, forest trail"),
    panel("medium", "l_forest", ["thabo"], "running, stopping, looking at viewer"),
    panel("medium", "l_forest", ["michaela", "thabo"], "talking, man pointing along trail",
          [("thabo", "Neztratila ses?"), ("michaela", "Ne. Jen hledám cestu."), ("thabo", "Tak pojď, ukážu ti ji.")], gap="large"),
    panel("wide", "l_mountain", ["michaela", "thabo"], "viewpoint, man handing water bottle, sunset, ocean",
          [("thabo", "Michaelo, zůstaň na večeři."), ("michaela", "Zůstanu.")], gap="large"),
    panel("medium", "l_cabin", ["thabo:evening"], "playing drum, fireplace, smile"),
    panel("medium", "l_cabin", ["michaela:evening", "thabo:evening"], "sitting by fireplace, smiling at each other",
          [("thabo", "Jsi nejkrásnější turistka."), ("michaela", "A ty nejlepší průvodce.")], gap="large"),
    panel("medium", "l_door", ["michaela:evening", "thabo:evening"], "embrace, cabin door, lamp light",
          [N("Kabát, kozačky a brýle zůstanou u krbu.")]),
    panel("medium", "l_door", ["michaela:evening", "thabo:evening"], "kiss, closed eyes", gap="small"),
    panel("establishing", "l_cabin", [], "fireplace embers, dark cabin, night window, stars", [N("V krbu dohasíná oheň.")], gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
