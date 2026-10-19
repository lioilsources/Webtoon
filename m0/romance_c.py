"""Romance set C — ten harlequin "film scripts" (half she searches, half he searches) → data/stories/rc_*/.

    python3 m0/romance_c.py

Same format and helpers as stories_romance.py; one style per story, each style used once.
"""

from common import DATA, save_json
from stories_romance import N, char, loc, panel, story, world

STORIES = {}

# 1. Newyorské písmeno — webtoon with artist tags ------------------------------------------------
STORIES["rc_01_ny"] = story(world("w_rc_01_ny", "Newyorské písmeno",
    "Eliška z Brna přijede na kurz knižní vazby a v antikvariátu potká Daniela.", "webtoon_romance_artist", [
    char("eliska", "Eliška", "1girl", "adult, curvy, small breasts, dark hair, curly hair, medium hair, brown eyes",
         {"default": "floral dress, cardigan, colorful scarf"},
         "a petite curvy Czech woman aged 28, dark curly hair, vintage floral dress, cardigan and a colourful scarf"),
    char("daniel", "Daniel Park", "1boy", "mature male, asian, black hair, short hair, glasses, brown eyes",
         {"default": "dark suit, white shirt"},
         "a Korean-American office worker aged 32, neat short black hair, glasses, dark suit, white shirt"),
    char("maya", "Maya", "1girl", "adult, black hair, ponytail, energetic, smile",
         {"default": "blazer, holding phone"}, "an energetic woman in a blazer talking on the phone"),
], [
    loc("l_street", "Manhattan", "outdoors, manhattan, street, yellow taxi, steam, subway entrance, daytime, crowd"),
    loc("l_books", "Antikvariát", "indoors, antique bookshop, bookshelves, old books, warm light, dust particles"),
    loc("l_bridge", "Brooklynský most", "outdoors, brooklyn bridge, evening, sunset, manhattan skyline, wind"),
    loc("l_rest", "Restaurace", "indoors, small restaurant, candle, pasta, warm light, night"),
]), [
    panel("wide", "l_street", ["eliska"], "walking, pulling suitcase, looking around, nervous smile",
          [N("Manhattan. Pára z kanálů, žluté taxíky."),
           ("eliska", "Tak jsem tady. Malá holka z Brna v největším městě světa.", "thought")]),
    panel("medium", "l_street", ["maya"], "talking on phone, walking, smile",
          [("maya", "Danieli, neboj se. Je to jen podpis smlouvy.")], gap="small"),
    panel("medium", "l_books", ["daniel"], "looking at bookshelf, holding book, glasses",
          [("daniel", "Promiňte, nevíte, kde mají místopis?")]),
    panel("medium", "l_books", ["eliska", "daniel"], "standing between bookshelves, pointing, holding book",
          [("eliska", "Já? Já jsem tu poprvé. Ale zkusila bych tu polici vzadu."),
           ("daniel", "Díky. Jste tu nová? Podle kufru.")]),
    panel("close-up", "l_books", ["daniel"], "gentle smile, looking at viewer",
          [("eliska", "Přijela jsem na kurz. Asi vypadám ztraceně."),
           ("daniel", "Ne. Vypadáte, že něco hledáte. Já taky.")], gap="large"),
    panel("wide", "l_bridge", ["eliska", "daniel"], "walking side by side, man carrying suitcase, wind, hair blowing",
          [("eliska", "Vždycky jsem si myslela, že na tohle město nemám postavu."), ("daniel", "Jakou postavu?")]),
    panel("close-up", "l_bridge", ["eliska"], "looking down, embarrassed, blush",
          [("eliska", "No… malou, kulatou. Tady jsou všichni vysocí a elegantní.")], gap="small"),
    panel("medium", "l_bridge", ["eliska", "daniel"], "laughing, looking at each other, sunset",
          [("daniel", "Já jsem taky spíš kancelářský a nudný. A přesto tu jsem."), ("eliska", "Vy nejste nudný.")],
          gap="large"),
    panel("medium", "l_rest", ["eliska", "daniel"], "sitting across table, candle, man clearing throat, shy",
          [("daniel", "Eliško, můžu vás pozvat znovu? Třeba do knihovny. A pak na kávu."),
           ("eliska", "To zní jako velmi newyorské rande."), ("daniel", "Doufám.")]),
    panel("close-up", "l_street", ["eliska", "daniel"], "kiss, short kiss, hug, night, city lights, closed eyes",
          gap="large"),
])

# 2. Zlatý obzor — fast photoreal ----------------------------------------------------------------
STORIES["rc_02_la"] = story(world("w_rc_02_la", "Zlatý obzor",
    "Astrid z Dánska fotí na Venice Beach, Mateo hraje plážový volejbal.", "photo_lightning", [
    char("astrid", "Astrid", "1girl", "adult, tall female, athletic, small breasts, blonde hair, ponytail, blue eyes",
         {"default": "white t-shirt, denim shorts, camera", "evening": "white summer dress"},
         "a tall athletic Danish woman aged 27, blonde hair in a ponytail, blue eyes, camera around her neck"),
    char("mateo", "Mateo", "1boy", "mature male, tan skin, athletic, black hair, curly hair, brown eyes, smile",
         {"default": "tank top, sports shorts", "evening": "white linen shirt"},
         "a Mexican-American beach volleyball player aged 29, dark curly hair, tanned, cheerful"),
], [
    loc("l_beach", "Venice Beach", "outdoors, venice beach, palm trees, sunlight, volleyball net, skateboarders"),
    loc("l_walk", "Promenáda", "outdoors, beach boardwalk, palm trees, smoothie cups, sunny"),
    loc("l_cliff", "Útes", "outdoors, cliff above ocean, sunset, golden hour, pacific ocean"),
    loc("l_rest", "Restaurace", "indoors, restaurant, city lights view, los angeles, night, candle"),
]), [
    panel("wide", "l_beach", ["astrid"], "taking photo, holding camera, volleyball rolling at feet"),
    panel("medium", "l_beach", ["mateo"], "waving, running, smile",
          [("mateo", "Promiň! Můžeš mi ho hodit?")], gap="small"),
    panel("medium", "l_beach", ["astrid", "mateo"], "woman holding volleyball, man catching ball, smile",
          [("astrid", "Můžu. Ale nejdřív mi řekni, jestli tady někde nepotkám skutečného prince."),
           ("mateo", "Já jsem jen volejbalista. Ale můžu tě vzít na nejlepší smoothie v LA.")], gap="large"),
    panel("wide", "l_walk", ["astrid", "mateo"], "walking side by side, holding smoothie cups",
          [("astrid", "Lidi si myslí, že vysoká blondýna je automaticky sebevědomá."), ("mateo", "A není?")]),
    panel("close-up", "l_walk", ["astrid"], "looking away, sad smile",
          [("astrid", "Někdy si připadám jako věž, která překáží.")], gap="small"),
    panel("medium", "l_walk", ["mateo"], "grin, looking at viewer",
          [("mateo", "Mně nepřekážíš. Naopak. Jsi první, kdo mě dnes porazil v hádce o míč.")], gap="large"),
    panel("medium", "l_cliff", ["astrid:evening", "mateo:evening"], "woman holding camera, man holding camera, sunset",
          [("mateo", "Můžu tě poprosit o jednu fotku? Ne mě. Tebe."), ("astrid", "Já jsem za objektivem."),
           ("mateo", "Jednou.")]),
    panel("medium", "l_cliff", ["astrid:evening", "mateo:evening"], "kiss, arm around shoulder, sunset, closed eyes",
          gap="large"),
    panel("medium", "l_rest", ["astrid:evening", "mateo:evening"], "man giving flower, holding flower, smile",
          [("mateo", "Astrid, ty nejsi věž. Jsi maják."), ("astrid", "To je nejlepší kompliment od volejbalisty.")]),
    panel("close-up", "l_rest", ["astrid:evening", "mateo:evening"], "laughing, looking at each other, city lights",
          [("mateo", "A příště tě naučím hrát."), ("astrid", "A já tě naučím fotit.")], gap="large"),
])

# 3. Miamské zastavení — western comic -----------------------------------------------------------
STORIES["rc_03_miami"] = story(world("w_rc_03_miami", "Miamské zastavení",
    "Irka Róisín, rozbité půjčené auto a mechanik Carlos.", "western_comic", [
    char("roisin", "Róisín", "1girl", "adult, curvy, large breasts, red hair, long hair, wavy hair, freckles, green eyes",
         {"default": "wrap dress, wide-brimmed hat"},
         "a curvy Irish woman aged 30, long wavy red hair, freckles, elegant wrap dress and a wide sun hat"),
    char("carlos", "Carlos", "1boy", "mature male, tan skin, broad shoulders, black hair, short hair, brown eyes",
         {"default": "overalls, white t-shirt, oil stains", "clean": "white shirt, jeans"},
         "a broad-shouldered Cuban-American mechanic aged 33, short dark hair, overalls over a white t-shirt"),
    char("rosa", "Tía Rosa", "1girl", "old woman, grey hair, hair bun, apron, smile",
         {"default": "floral blouse, apron"}, "an elderly Cuban woman with a grey bun and an apron, cafe owner"),
], [
    loc("l_gas", "Benzinka", "outdoors, gas station, rental car, smoke from hood, palm trees, sunny, miami"),
    loc("l_shop", "Dílna", "indoors, auto repair shop, garage, tools, car, oil"),
    loc("l_cafe", "Kavárna Tíy Rosy", "indoors, cuban cafe, colorful walls, coffee cups, pastries, music"),
    loc("l_shore", "Nábřeží", "outdoors, seaside promenade, street lamp, evening, ocean, miami"),
]), [
    panel("wide", "l_gas", ["roisin"], "standing by car, smoke, annoyed, holding hat"),
    panel("medium", "l_gas", ["carlos"], "leaning out of pickup truck window, smile",
          [("carlos", "Potřebujete pomoct?")], gap="small"),
    panel("medium", "l_gas", ["roisin", "carlos"], "man walking to car, woman arms crossed, smirk",
          [("roisin", "Jen když umíte opravit auto a nezírat přitom."),
           ("carlos", "Umím obojí. Teda to první.")], gap="large"),
    panel("medium", "l_shop", ["roisin"], "sitting on chair, looking down, sad",
          [("roisin", "V Miami si připadám, že mám špatnou postavu.")]),
    panel("medium", "l_shop", ["carlos"], "repairing car, dirty hands, smile, looking back",
          [("carlos", "Já mám špinavé ruce a taky se tím netrápím."), ("roisin", "To je jiné."),
           ("carlos", "Každý má něco. Vy máte krásný klobouk.")], gap="large"),
    panel("medium", "l_cafe", ["rosa"], "holding tray, pastries, grin",
          [("rosa", "Carlosi, představ mi tu slečnu.")]),
    panel("medium", "l_cafe", ["roisin", "carlos:clean"], "sitting at table, coffee cups, laughing",
          [("carlos", "Teto, to je Róisín. Opravuju jí auto."),
           ("rosa", "A už jsi jí řekl, že jsi nejlepší tanečník v ulici?"), ("roisin", "To bych ráda viděla.")]),
    panel("wide", "l_cafe", ["roisin", "carlos:clean"], "dancing together, salsa, laughing, holding hands",
          gap="large"),
    panel("wide", "l_shore", ["roisin", "carlos:clean"], "walking along sea, evening",
          [("carlos", "Zítra přijdu s hotovým autem. A s kytkou."), ("roisin", "To je hodně oprav."),
           ("carlos", "Nejlepší investice.")]),
    panel("close-up", "l_shore", ["roisin", "carlos:clean"], "kiss, under street lamp, closed eyes, night",
          gap="large"),
])

# 4. Pařížský kovboj — art nouveau ---------------------------------------------------------------
STORIES["rc_04_pariz"] = story(world("w_rc_04_pariz", "Pařížský kovboj",
    "Priya kreslí u Seiny, texaský kovboj Logan hledá výstaviště.", "art_nouveau_mucha", [
    char("priya", "Priya", "1girl", "adult, indian, brown skin, small breasts, long hair, black hair, brown eyes",
         {"default": "silk blouse, long skirt, holding sketchbook"},
         "a petite Indian woman aged 29, long black hair, silk blouse and a sari-inspired skirt, sketchbook"),
    char("logan", "Logan", "1boy", "mature male, tall, tan, brown hair, stubble, cowboy hat",
         {"default": "denim jacket, jeans, cowboy boots", "nohat": "denim jacket, jeans, holding cowboy hat"},
         "a tall tanned Texan cowboy aged 34, stetson, denim jacket, cowboy boots"),
], [
    loc("l_seine", "Nábřeží Seiny", "outdoors, seine, riverbank, paris, bookstalls, daytime"),
    loc("l_fair", "Veletrh", "indoors, agricultural fair, exhibition hall, hay bales, crowd"),
    loc("l_cafe", "Kavárna", "indoors, small parisian cafe, rain on window, coffee"),
    loc("l_bridge", "Pont des Arts", "outdoors, pont des arts, bridge, seine, night, city lights"),
]), [
    panel("wide", "l_seine", ["priya"], "sitting, drawing in sketchbook, riverbank"),
    panel("medium", "l_seine", ["logan"], "holding map, confused, cowboy hat",
          [("logan", "Promiňte, nevíte, kde je výstaviště?")], gap="small"),
    panel("medium", "l_seine", ["priya", "logan"], "looking up at man, smile, sketchbook",
          [("priya", "Vy jste kovboj v Paříži?"), ("logan", "A vy jste princezna, která kreslí?"),
           ("priya", "Já? Princezna? Ani ne.")], gap="large"),
    panel("wide", "l_fair", ["logan"], "swinging lasso, lasso, crowd watching",
          [("logan", "Tady si připadám jako atrakce.")]),
    panel("medium", "l_fair", ["priya"], "holding camera, taking photo, small smile",
          [("priya", "A já si tady připadám moc malá.")], gap="small"),
    panel("close-up", "l_fair", ["logan"], "gentle smile, tipping hat",
          [("logan", "Mně nepřipadáte malá. Připadáte mi akorát.")], gap="large"),
    panel("medium", "l_cafe", ["priya", "logan:nohat"], "sitting across table, rain on window, man holding hat",
          [("logan", "Priyo, můžu tě pozvat na večeři? Neumím francouzsky, ale umím mlčet."),
           ("priya", "To je nabídka k nezaplacení.")], gap="large"),
    panel("medium", "l_bridge", ["priya", "logan"], "man giving small sheriff star badge, holding badge, night",
          [("logan", "Pro mou múzu."), ("priya", "Pro mého kovboje.")]),
    panel("wide", "l_bridge", ["priya", "logan"], "hug, kiss, closed eyes, night, city lights", gap="large"),
])

# 5. Londýnský déšť — noir monochrome ------------------------------------------------------------
STORIES["rc_05_londyn"] = story(world("w_rc_05_londyn", "Londýnský déšť",
    "Kurátorka Mei bez deštníku a boxer Marcus.", "noir_mono", [
    char("mei", "Mei", "1girl", "adult, asian, slender, small breasts, black hair, bob cut, dark eyes",
         {"default": "dark trench coat", "evening": "dark trench coat, colorful scarf"},
         "a slender Chinese-Singaporean woman aged 27, sleek black bob, dark trench coat"),
    char("marcus", "Marcus", "1boy", "mature male, dark-skinned male, dark skin, athletic, bald, brown eyes",
         {"default": "hoodie, sports jacket", "evening": "dress shirt"},
         "an athletic Black British boxer aged 31, shaved head, hoodie and sports jacket, calm and kind"),
], [
    loc("l_gym", "Před boxernou", "outdoors, london street, boxing gym entrance, rain, puddles, brick wall"),
    loc("l_cafe", "Kavárna", "indoors, cafe, wet coats, hot chocolate, window, rain"),
    loc("l_park", "Hyde Park", "outdoors, hyde park, wet grass, trees, squirrel, evening"),
    loc("l_rest", "Restaurace", "indoors, restaurant, candle, night, warm light"),
]), [
    panel("wide", "l_gym", ["mei"], "standing in rain, no umbrella, wet hair, hugging self", [N("Londýn. Prší.")]),
    panel("medium", "l_gym", ["marcus"], "walking out of door, holding umbrella",
          [("marcus", "Potřebujete deštník?")], gap="small"),
    panel("medium", "l_gym", ["mei", "marcus"], "sharing umbrella, rain, shy",
          [("mei", "Já… ano. Ale nechci zdržovat."), ("marcus", "Já zrovna končím. Můžu vás doprovodit.")],
          gap="large"),
    panel("medium", "l_cafe", ["mei"], "holding cup, hot chocolate, looking down",
          [("mei", "Lidi si myslí, že když jsem tichá, nemám názor.")]),
    panel("medium", "l_cafe", ["marcus"], "smile, holding cup",
          [("marcus", "Já mluvím hlavně pěstmi. Ale taky mám názor.")], gap="small"),
    panel("close-up", "l_cafe", ["mei"], "laughing, closed eyes",
          [("mei", "To je poprvé, co mi to někdo řekl takhle.")], gap="large"),
    panel("wide", "l_park", ["mei", "marcus"], "walking, wet grass, squirrel",
          [("marcus", "Zítra mám zápas. Přijdeš?"), ("mei", "Nikdy jsem box neviděla."),
           ("marcus", "Tak to bude tvůj první. A pak tě vezmu na večeři.")], gap="large"),
    panel("medium", "l_rest", ["mei:evening", "marcus:evening"], "sitting across table, candle, smile",
          [("mei", "Vyhrál jsi?"), ("marcus", "Ale ty jsi tu. To je výhra.")]),
    panel("close-up", "l_rest", ["mei:evening", "marcus:evening"], "hug, kiss, closed eyes", gap="large"),
])

# 6. Pražské mosty — pastel shoujo ---------------------------------------------------------------
STORIES["rc_06_praha"] = story(world("w_rc_06_praha", "Pražské mosty",
    "Tunde přijel na fitness expo, Lucie kreslí na Kampě.", "pastel_shoujo", [
    char("tunde", "Tunde", "1boy", "mature male, dark-skinned male, very dark skin, muscular, broad shoulders, short hair, black hair",
         {"default": "tracksuit", "evening": "white shirt"},
         "a muscular Nigerian man aged 34 living in London, broad shoulders, short hair, sports tracksuit"),
    char("lucie", "Lucie", "1girl", "adult, curvy, wide hips, small breasts, brown hair, bob cut, brown eyes",
         {"default": "vintage dress, cardigan, holding sketchbook", "evening": "vintage dress"},
         "a petite curvy Czech woman aged 30, chestnut bob, vintage dress, art teacher with a sketchbook"),
], [
    loc("l_kampa", "Kampa", "outdoors, kampa, riverbank, prague, charles bridge in background, trees, daytime"),
    loc("l_cafe", "Kavárna", "indoors, prague cafe, window, coffee cups"),
    loc("l_bridge", "Karlův most", "outdoors, charles bridge, statues, evening, street lamps, tourists"),
    loc("l_rest", "Restaurace", "indoors, czech restaurant, candles, night, warm light"),
]), [
    panel("wide", "l_kampa", ["lucie"], "sitting, drawing in sketchbook, riverbank"),
    panel("medium", "l_kampa", ["tunde"], "jogging, stopping, slightly out of breath, smile",
          [("tunde", "Promiňte, nevíte, kde je výstaviště?")], gap="small"),
    panel("medium", "l_kampa", ["lucie", "tunde"], "woman looking up, holding sketchbook, man leaning",
          [("lucie", "A vy jste z expa? Podle tracksuitu."), ("tunde", "Ano. A vy kreslíte?"),
           ("lucie", "Jen si hraju.")]),
    panel("close-up", "l_kampa", ["tunde"], "warm smile", [("tunde", "To je nejlepší důvod.")], gap="large"),
    panel("medium", "l_cafe", ["tunde"], "sitting at table, serious, hands together",
          [("tunde", "Lidi si myslí, že když mám svaly, nemám city.")]),
    panel("medium", "l_cafe", ["lucie"], "sitting, looking down, blush",
          [("lucie", "Já si myslím, že když mám kulaté boky, nejsem dost elegantní."),
           ("tunde", "Mně připadáte velmi elegantní.")], gap="large"),
    panel("wide", "l_bridge", ["lucie", "tunde"], "man offering hand, holding hands, evening",
          [("tunde", "Lucie, můžu vás pozvat na večeři? A pak na procházku."), ("lucie", "To zní jako plán.")],
          gap="large"),
    panel("medium", "l_rest", ["lucie:evening", "tunde:evening"], "sitting at table, candles, laughing",
          [("lucie", "Tak co, svalovče, našel jsi v Praze svou múzu?"), ("tunde", "Myslím, že ano.")]),
    panel("medium", "l_kampa", ["lucie:evening", "tunde:evening"], "kiss, goodbye kiss, night, front door, street lamp",
          [N("Polibek na rozloučenou před jejím domem.")], gap="large"),
])

# 7. Šanghajský čaj — ink wash -------------------------------------------------------------------
STORIES["rc_07_sanghaj"] = story(world("w_rc_07_sanghaj", "Šanghajský čaj",
    "Samuel na služební cestě nerozumí menu, Wei učí jógu.", "ink_wash", [
    char("samuel", "Samuel", "1boy", "mature male, dark-skinned male, dark skin, curly hair, short hair, glasses",
         {"default": "tailored suit, white shirt"},
         "an Afro-Brazilian office worker aged 33, short curly hair, glasses, tailored suit"),
    char("wei", "Wei", "1girl", "adult, asian, tall female, athletic, long hair, black hair, straight hair",
         {"default": "minimalist clothes, white top, grey pants"},
         "a tall athletic Chinese woman aged 29, long straight black hair, minimalist clothes, yoga teacher"),
], [
    loc("l_tea", "Čajovna", "indoors, chinese teahouse, wooden tables, teapot, tea cups, lanterns"),
    loc("l_bund", "The Bund", "outdoors, the bund, huangpu river, shanghai skyline, dusk, umbrella"),
    loc("l_rest", "Restaurace", "indoors, chinese restaurant, round table, dishes, evening"),
    loc("l_garden", "Zahrada", "outdoors, chinese garden, lanterns, night, pavilion, pond"),
]), [
    panel("medium", "l_tea", ["samuel"], "holding menu, confused, glasses"),
    panel("medium", "l_tea", ["wei"], "smile, pointing at menu",
          [("wei", "Doporučuji jasmínový.")], gap="small"),
    panel("medium", "l_tea", ["samuel", "wei"], "sitting at table, tea cups, smile",
          [("samuel", "Děkuji. Já jsem tu poprvé."),
           ("wei", "To poznám. Ale nebojte, Šanghaj je milá, když se nepospíchá.")], gap="large"),
    panel("wide", "l_bund", ["samuel", "wei"], "walking along river, man holding umbrella, dusk",
          [("samuel", "Celý den jsem mluvil o číslech. Připadám si nudný."),
           ("wei", "Čísla nejsou nuda. Jen je třeba je říct jako příběh.")]),
    panel("close-up", "l_bund", ["wei"], "gentle smile",
          [("samuel", "A vy umíte příběhy?"), ("wei", "Učím jógu. To je taky příběh.")], gap="large"),
    panel("medium", "l_rest", ["samuel", "wei"], "woman ordering, man laughing, dishes",
          [("samuel", "Wei, můžu vás pozvat znovu? Třeba na procházku."),
           ("wei", "Ano. Ale tentokrát bez deštníku.")], gap="large"),
    panel("wide", "l_garden", ["samuel", "wei"], "hug, lanterns, night",
          [("samuel", "Našel jsem v Šanghaji múzu."), ("wei", "A já prince v obleku.")]),
    panel("close-up", "l_garden", ["samuel", "wei"], "kiss, closed eyes, lanterns", gap="large"),
])

# 8. Kingston – Havana — analogue film -----------------------------------------------------------
STORIES["rc_08_kingston"] = story(world("w_rc_08_kingston", "Kingston – Havana",
    "Sprinter Andre a fotografka Camila: od stadionu v Kingstonu po Malecón.", "photo_realvis_film", [
    char("andre", "Andre", "1boy", "mature male, dark-skinned male, very dark skin, tall, athletic, very short hair",
         {"default": "track jacket, running shorts", "evening": "white shirt"},
         "a tall Afro-Caribbean sprinter aged 32, short fade haircut, track jacket"),
    char("camila", "Camila", "1girl", "adult, tan skin, curvy, small breasts, curly hair, brown hair, brown eyes",
         {"default": "summer dress, camera"},
         "a curvy Cuban photographer aged 28, curly brown hair, light summer dress, camera"),
    char("luis", "Luis", "1boy", "mature male, tan skin, black hair, mustache, smile",
         {"default": "guayabera, holding guitar"}, "a Cuban man playing an acoustic guitar, guayabera shirt"),
], [
    loc("l_stadium", "Stadion Kingston", "outdoors, stadium, running track, kingston, sunny, crowd"),
    loc("l_beach", "Pláž", "outdoors, jamaican beach, sand, palm trees, afternoon"),
    loc("l_malecon", "Malecón", "outdoors, malecon, havana, seawall, evening, sunset, vintage cars"),
    loc("l_rest", "Rodinná restaurace", "indoors, family restaurant, havana, lanterns, guitar music, night"),
]), [
    panel("wide", "l_stadium", ["andre"], "running, sprinting, motion blur, determined"),
    panel("medium", "l_stadium", ["camila"], "holding camera, taking photo, smile",
          [("camila", "Můžu tě vyfotit po závodě?")], gap="small"),
    panel("medium", "l_stadium", ["andre", "camila"], "man out of breath, woman holding camera",
          [("andre", "Já jsem jen běžec."), ("camila", "A já jen fotografka. Tak se shodneme.")], gap="large"),
    panel("wide", "l_beach", ["andre", "camila"], "walking on sand, barefoot",
          [("andre", "Lidi vidí jen čas na stopkách."),
           ("camila", "Já vidím, jak se usmíváš, když doběhneš."), ("andre", "To je poprvé.")], gap="large"),
    panel("wide", "l_malecon", ["andre:evening", "camila"], "walking along seawall, sunset",
          [N("Mezizastávka v Havaně."), ("camila", "Tady jsem doma. A ty?"), ("andre", "Teď taky trochu.")],
          gap="large"),
    panel("medium", "l_rest", ["luis"], "playing guitar, singing, smile"),
    panel("medium", "l_rest", ["andre:evening", "camila"], "man giving flower, holding flower, smile",
          [("andre", "Camilo, můžu tě pozvat na procházku? A pak znovu."), ("camila", "Ano.")], gap="small"),
    panel("close-up", "l_rest", ["andre:evening", "camila"], "kiss, under lanterns, closed eyes", gap="large"),
])

# 9. Jakarta – Bombaj — flat minimalism ----------------------------------------------------------
STORIES["rc_09_jakarta"] = story(world("w_rc_09_jakarta", "Jakarta – Bombaj",
    "Plachý úředník Ravi bloudí Jakartou, Ayu mu ukáže cestu. O měsíc později Bombaj.", "minimal_flat", [
    char("ravi", "Ravi", "1boy", "mature male, indian, brown skin, glasses, black hair, short hair, shy",
         {"default": "dark suit, white shirt"},
         "a shy Indian office clerk aged 33, glasses, dark suit"),
    char("ayu", "Ayu", "1girl", "adult, asian, tan skin, curvy, long hair, wavy hair, black hair, smile",
         {"default": "batik blouse, apron", "travel": "batik blouse, long skirt"},
         "a petite curvy Indonesian woman aged 28, long wavy hair, batik blouse, works in a cafe"),
], [
    loc("l_market", "Trh v Jakartě", "outdoors, market, jakarta, stalls, coffee stall, crowd, daytime"),
    loc("l_cafe", "Kavárna", "indoors, small cafe, notebook, coffee cups, afternoon"),
    loc("l_bombay", "Nábřeží v Bombaji", "outdoors, marine drive, mumbai, sea, evening, city lights"),
    loc("l_rest", "Restaurace", "indoors, indian restaurant, candles, spices, night"),
]), [
    panel("wide", "l_market", ["ravi"], "lost, looking around, holding briefcase"),
    panel("medium", "l_market", ["ravi", "ayu"], "woman serving coffee, man holding cup",
          [("ravi", "Prosím, kávu. A cestu k hotelu."), ("ayu", "Kávu dostanete. Cestu vám ukážu."),
           ("ravi", "To je moc milé.")], gap="large"),
    panel("medium", "l_cafe", ["ravi"], "writing notes, notebook, sigh",
          [("ravi", "Celý život jsem v kanceláři. Připadám si nudný.")]),
    panel("close-up", "l_cafe", ["ayu"], "smile, leaning on counter",
          [("ayu", "Nudný člověk by se neptal na cestu. Jen by bloudil.")], gap="large"),
    panel("wide", "l_bombay", ["ayu:travel"], "walking, sea, evening, looking around", [N("O měsíc později. Bombaj.")]),
    panel("medium", "l_bombay", ["ravi", "ayu:travel"], "surprised, meeting, smile",
          [("ayu", "Tak jsme se našli."), ("ravi", "Já jsem doufal.")], gap="large"),
    panel("medium", "l_rest", ["ravi", "ayu:travel"], "sitting at table, candles, laughing",
          [("ravi", "Ayu, můžu tě pozvat na procházku?"), ("ayu", "Ano. A pak znovu.")]),
    panel("close-up", "l_rest", ["ravi", "ayu:travel"], "kiss, closed eyes, candlelight", gap="large"),
])

# 10. Nairobské ráno — oil painting --------------------------------------------------------------
STORIES["rc_10_nairobi"] = story(world("w_rc_10_nairobi", "Nairobské ráno",
    "Mechanik Baraka se vrací z Londýna domů, Wanjiku prodává látky na trhu.", "painterly_oil", [
    char("baraka", "Baraka", "1boy", "mature male, dark-skinned male, very dark skin, burly, short dreadlocks",
         {"default": "work overalls, oil stains", "evening": "button-up shirt"},
         "a broad Kenyan mechanic aged 36, short dreadlocks, work overalls"),
    char("wanjiku", "Wanjiku", "1girl", "adult, dark-skinned female, very dark skin, tall female, athletic, afro",
         {"default": "colorful dress"},
         "a tall athletic Kenyan woman aged 30, natural afro, colourful dress"),
], [
    loc("l_market", "Trh", "outdoors, market, nairobi, fabric stall, colorful fabrics, morning"),
    loc("l_shop", "Dílna", "indoors, auto repair workshop, car, tools, daylight"),
    loc("l_park", "Park", "outdoors, park, acacia tree, flower stall, afternoon, nairobi"),
    loc("l_rest", "Restaurace", "indoors, restaurant, warm light, evening, candle"),
]), [
    panel("wide", "l_market", ["baraka"], "walking through market, looking around, carrying bag"),
    panel("medium", "l_market", ["wanjiku"], "standing at fabric stall, folding fabric, surprised",
          [("baraka", "Promiňte, nevíte, kde mají autodíly?"), ("wanjiku", "Vy jste Baraka? Kamauův bratr?")]),
    panel("medium", "l_market", ["baraka", "wanjiku"], "smile, fabric stall",
          [("baraka", "Ano. Přijel jsem po dlouhé době."), ("wanjiku", "Tak vítejte doma.")], gap="large"),
    panel("medium", "l_shop", ["baraka"], "repairing car, under hood, wiping hands",
          [("baraka", "V Londýně jsem si zvykl, že mě nikdo nezná.")]),
    panel("medium", "l_shop", ["baraka", "wanjiku"], "woman holding cup of tea, giving tea",
          [("wanjiku", "Tady vás znají. To není špatné."),
           ("baraka", "Někdy mám strach, že už sem nepatřím."), ("wanjiku", "Patříte. Jen jste zapomněl.")],
          gap="large"),
    panel("wide", "l_park", ["baraka:evening", "wanjiku"], "walking, man holding flower, giving flower",
          [("baraka", "Wanjiku, můžu vás pozvat na večeři?"),
           ("wanjiku", "Ano. Ale nejdřív mi ukážete, jak opravit kolo.")], gap="large"),
    panel("medium", "l_rest", ["baraka:evening", "wanjiku"], "sitting at table, smile, warm light",
          [("baraka", "Našel jsem v Nairobi svou múzu."), ("wanjiku", "A já svého mechanika.")]),
    panel("close-up", "l_rest", ["baraka:evening", "wanjiku"], "hug, kiss, closed eyes", gap="large"),
])


def main():
    for sid, (w, sb) in STORIES.items():
        d = DATA / "stories" / sid
        save_json(d / "world.json", w)
        save_json(d / "storyboard.json", sb)
        print(f"{sid}: {len(sb['panels'])} panels, style {w['style_id']}")


if __name__ == "__main__":
    main()
