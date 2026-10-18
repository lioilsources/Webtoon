"""Builds kids/stories/21–25 (fifth set). Models from the ones that held up in sets 1–4."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "stories"


def P(shot, loc, chars, tags, scene, bubbles=(), sfx=(), gap="medium", **kw):
    return {"shot": shot, "location_id": loc, "characters": [{"id": c} for c in chars], "visual_tags": tags,
            "scene_en": scene, "bubbles": list(bubbles), "sfx": [{"text": s} for s in sfx], "gap_after": gap, **kw}


def S(t, who=None): return {"kind": "speech", "speaker": who, "text": t}
def SH(t, who=None): return {"kind": "shout", "speaker": who, "text": t}
def N(t): return {"kind": "narration", "speaker": None, "text": t}
def PET(t, icon, who, tr=None):
    b = {"kind": "pet", "speaker": who, "text": t, "icon": icon}
    if tr:
        b["translation"] = tr
    return b
def C(id, name, count, tags, desc): return {"id": id, "name": name, "count_tag": count, "tag_prompt": tags, "desc_en": desc}
def L(id, tags, desc): return {"id": id, "tag_prompt": tags, "desc_en": desc}


def save(name, wid, title, style, chars, locs, panels):
    d = {"world": {"id": wid, "title": title, "audience": "kids", "language": "cs", "style_id": style,
                   "characters": chars, "locations": locs},
         "storyboard": {"title": title, "panels": panels}}
    (OUT / f"{name}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(name, len(panels), "panels")


# --- 21 Koláčová loupež ------------------------------------------------------
save("21_kolacova_loupez", "k_pieheist", "Koláčová loupež na vesnici", "flux_pixar", [
    C("amalka", "Amálka", "1girl", "child, freckles, braids, red hair, blue dress, smile",
      "Amalka, a cheerful freckled 7-year-old girl with two red braids and a blue dress"),
    C("zofka", "Žofka", None, "hen, speckled hen, straw hat", "Zofka, a vain speckled hen wearing a tiny straw hat"),
    C("marjanka", "Bába Marjánka", "1girl", "old woman, plump, white headscarf, apron, flour", "Granny Marjanka, a plump kind village baker in a white headscarf and apron"),
    C("kdepak", "Kdepak", None, "orange cat, fat cat, sleepy", "Kdepak, a lazy fat orange village cat"),
    C("skocik", "Skočík", None, "fawn, young deer, spots", "Skocik, a small shy spotted fawn"),
], [L("yard", "outdoors, farmyard, barn, long table, pies, fence, summer, sunlight", "A sunny Czech village farmyard in front of a barn, a long table with three trays of apricot pies."),
    L("field", "outdoors, golden wheat field, path, hill, afternoon", "A golden wheat field behind the village in the late afternoon breeze."),
    L("shed", "indoors, barn, hay, evening, warm light", "Inside a small barn on a pile of hay in the evening.")], [
    P("establishing", "yard", [], ["no humans", "pies", "table"], "a sunny Czech village farmyard, a long table with three trays of apricot pies in front of a barn",
      [N("Slunce praží. Na stole chladnou tři plechy meruňkových koláčů.")], gap="small"),
    P("wide", "yard", ["amalka", "zofka"], ["leaning over fence", "drooling", "hen", "sign"],
      "Amalka leans over the fence staring at the pies with shining eyes, the speckled hen in a straw hat stands next to her by a sign",
      [S("Žofko… vidíš ty koláče? Tři plechy. TŘI, Žofko!", "amalka"), S("Vidím, vidím. A taky vidím tabuli: NEDOTÝKAT SE — CHLADNOU.", "zofka")]),
    P("medium", "yard", ["zofka", "amalka"], ["hen", "adjusting hat", "grin", "pointing"],
      "the hen adjusts her straw hat, Amalka grins mischievously",
      [S("No dobře, NEDOTÝKAT SE. To chladnou stejně zapomněla napsat.", "zofka"), S("To je jasné znamení! Když někdo napíše NEDOTÝKAT SE, myslí tím: AMÁLKO, JEN TO ZKUS!", "amalka")]),
    P("close-up", "yard", ["kdepak"], ["cat", "one eye open", "sunbathing"], "close-up of the fat orange cat lying in the sun opening one eye",
      [S("Já za vás neručím. Ale když budete kousat potichu, já neuslyším.", "kdepak")]),
    P("wide", "yard", ["amalka", "zofka", "skocik", "kdepak"], ["crawling on table", "fawn", "bumping table", "pies flying", "cat"],
      "Amalka crawls on her belly along the table, a young fawn hops past and bumps the table, three pies slide off and land on the back of the sleeping cat",
      [N("Kolem hopsne mladý srnec — a strčí do stolu!")], ["BUM!"], gap="small"),
    P("medium", "yard", ["kdepak"], ["cat", "pies on back", "angry", "indignant"], "the orange cat sits up furious with three apricot pies stuck on his back",
      [SH("Já jsem KOČKA, ne podnos!", "kdepak")]),
    P("medium", "yard", ["amalka", "zofka"], ["on table", "shocked", "hen", "dramatic"], "Amalka and the hen on the table look at each other dramatically",
      [S("…Žofko. Někdo ukradl koláče. To nejsme my. To je… LOUPEŽ!", "amalka"), S("My jsme na stole, Kdepak má koláče na hřbetu a srnec utíká přes pole. Kdo z nich je zloděj?", "zofka")]),
    P("close-up", "yard", ["kdepak"], ["cat", "deadpan", "crumbs"], "close-up of the cat with crumbs on his fur, deadpan",
      [S("Databáze podezřelých je malá.", "kdepak")]),
    P("wide", "field", ["amalka", "zofka", "kdepak"], ["magnifying glass", "hoof prints", "crumbs", "walking", "wheat field"],
      "in the golden wheat field Amalka follows hoof prints with a magnifying glass, the hen beside her, the cat trailing behind",
      [S("Stopa kopýtková… a vedle ní drobečky! Zločinec jedl za pochodu!", "amalka"), S("Nemohla bys takhle mluvit o srnci? Toho známe. Jmenuje se Skočík a bojí se vlastního mouchačení.", "zofka")]),
    P("wide", "field", ["marjanka"], ["shouting", "hands on hips", "hill", "apron"], "on top of the hill the old baker shouts angrily into the distance",
      [SH("Kdo mi okradl koláče?! Já na ně čekala celou rodinu!", "marjanka")]),
    P("medium", "shed", ["skocik"], ["fawn", "eating", "hay", "shy", "crumbs"], "inside the barn the little fawn sits on the hay shyly nibbling the last pie",
      [S("Já… já jsem ten koláč jen chtěl očichat! A pak… pak jsem ho měl na jazyku!", "skocik")]),
    P("medium", "shed", ["amalka", "zofka", "kdepak"], ["doorway", "soft smile", "hen", "cat writing on paw"],
      "Amalka and the hen peek in through the door, the cat pretends to take notes on his paw",
      [S("Chudáčku malý. Víš co, Žofko? Loupež nebyla. Byla to nouze.", "amalka"), S("Bez komentáře.", "kdepak")]),
    P("wide", "yard", ["marjanka", "skocik", "amalka", "zofka"], ["table full of pies", "sign", "flour in hair", "fawn", "hen", "happy"],
      "next morning the table is full of pies with a sign for everyone who is hungry, the baker, the fawn covered in crumbs, Amalka with flour in her braids and the hen with a cherry on her hat",
      [N("„PRO VŠECHNY, KDO MAJÍ HLAD.“"), S("Další spolu upečeme, děti. A ty, Kdepaku, tys nikdy nepomáhal? Ty jsi jen ležel!", "marjanka")]),
    P("medium", "yard", ["kdepak", "zofka"], ["cat", "holding pie", "hen", "wink"], "the cat holds a pie in his paws, the hen winks at the viewer",
      [S("Dohlížel jsem. To je taky práce.", "kdepak"), S("Někdo musí hlídat i hlídače.", "zofka")]),
])

# --- 22 Ponorné město korálů -------------------------------------------------
save("22_ponorne_mesto", "k_coralcity", "Ponorné město korálů", "flux_manga", [
    C("bara", "Bára", "1girl", "child, black hair, ponytail, diving goggles on forehead, wetsuit", "Bara, a brave 9-year-old diver girl with a black ponytail, a wetsuit and diving goggles pushed up on her forehead"),
    C("kapka", "Kapka", None, "small octopus, purple", "Kapka, a small octopus that changes colour with its mood"),
    C("perlinka", "Perlinka", "1girl", "mermaid, librarian, glasses, shell backpack, books", "Perlinka, a mermaid librarian with glasses carrying books in a seashell backpack"),
    C("sedy", "Táta Šedý", None, "shark, big grey shark, shy", "Grandpa Grey, a huge but shy old grey shark"),
], [L("city", "underwater, coral city, coral towers, shells, fish with lanterns, manta ray, morning", "An underwater city of coral towers and shells, manta rays and little fish carrying lanterns."),
    L("library", "underwater, library, shelves, hole in floor, bubbles", "A coral library with a dark hole in the floor, air bubbles floating around it."),
    L("cave", "underwater, cave, stalactites, seaweed, dim light", "A dim underwater cave with stalactites and swaying seaweed.")], [
    P("establishing", "city", [], ["no humans"], "an underwater city built of coral towers and seashells, manta rays and fish with little lanterns",
      [N("Ponorné město z korálových věží a ulit.")], gap="small"),
    P("wide", "city", ["perlinka", "kapka"], ["mermaid", "panic", "books flying", "octopus", "purple", "corner"],
      "the mermaid librarian swims in a panic with books scattering around her, a small bright purple octopus trembles in a corner",
      [S("Báro! Přiletěla jsem, jak jsem mohla! Knihovna… velká díra… v podlaze! A v ní tma! Nikdo z knihovních už nesmí dovnitř!", "perlinka")]),
    P("medium", "city", ["bara", "kapka"], ["goggles on forehead", "determined", "octopus", "purple"], "Bara pushes her goggles up on her forehead, the purple octopus whispers to her",
      [S("Tak jo. Kdo šel dovnitř?", "bara"), S("Víla Ištkin šla dovnitř pro poslední knihu. A… nevyšla.", "kapka")]),
    P("medium", "city", ["perlinka"], ["mermaid", "glasses", "worried", "holding book"], "the mermaid librarian adjusts her glasses, worried",
      [S("Kolik knih ta díra spolkla?", "bara"), S("Všechny tři tisíce. Včetně té o receptech na chřipku. Ta je teď pod vodou rozhodně nejhorší zpráva dne.", "perlinka")]),
    P("establishing", "library", [], ["hole", "darkness", "bubbles", "books"], "a dark bottomless hole in the floor of the coral library with bubbles drifting around it",
      [N("Díra v podlaze knihovny jako nekonečná ústa.")], gap="small"),
    P("medium", "library", ["bara", "kapka"], ["putting on goggles", "rope", "seaweed rope", "octopus", "purple"], "Bara pulls her goggles down and takes out a rope made of seaweed, the octopus looks at her in alarm",
      [S("Já půjdu dolů. Kapko, ty jsi se mnou. Při nejhorším se zbarvíš fialově a budu vědět, že je čas utíkat.", "bara"), S("To je tvůj plán?! Můj strach jako siréna?!", "kapka")]),
    P("close-up", "library", ["kapka"], ["octopus", "pink", "proud", "blushing"], "close-up of the small octopus turning pink with pride",
      [S("Jsi nejpoctivější ukazatel strachu, jakého znám.", "bara"), N("Kapka zrůžoví — pýchou.")]),
    P("wide", "cave", ["sedy", "bara", "kapka"], ["shark", "holding book", "fairy", "stalactites", "shy"],
      "in the underwater cave sits a huge shy grey shark gently holding a tiny frightened fairy and a book in his fins",
      [S("Já ji nechtěl vystrašit. Já jsem si jen chtěl PŘEČÍST tuhle knihu. O zelenině. Nikdy jsem neuměl číst a stydím se zeptat.", "sedy")]),
    P("medium", "cave", ["bara", "kapka"], ["realization", "octopus", "pink"], "Bara turns to the octopus, realising",
      [S("Tak proto ta tma! Ne zločin — stud!", "bara"), S("A co když ty zmizelé knihy… jen PŘEČÍTAL?", "kapka")]),
    P("medium", "cave", ["bara", "sedy"], ["smile", "pointing", "shark", "deal"], "Bara smiles and offers the shark a deal",
      [S("Táto Šedý, pusť vílu, a my tě naučíme číst. Ale pod jednou podmínkou.", "bara"), S("Jakou?", "sedy")]),
    P("close-up", "cave", ["bara"], ["smile", "goggles", "bubbles"], "close-up of Bara smiling",
      [S("Vrátíš knihovně všechny poházené plovoucí knihy. A pak s námi přijdeš na lekci.", "bara")]),
    P("wide", "library", ["sedy", "bara", "kapka", "perlinka"], ["shark", "tiny glasses", "reading aloud", "clapping", "crying happy", "fairy riding shark"],
      "a week later the shark sits on the library floor wearing tiny glasses reading aloud, Bara and the octopus clap, the mermaid cries happily and a tiny fairy rides on his back",
      [S("Ko-če-ka… Ko-čka pije mléko.", "sedy")]),
    P("close-up", "library", ["kapka"], ["octopus", "golden", "glowing", "happy"], "close-up of the octopus glowing golden with happiness",
      [S("Víš co, Báro? Dnes se barvím do zlatova.", "kapka"), S("Zlatá je tvoje barva pohody.", "bara")]),
])

# --- 23 Cirkus Amárie ---------------------------------------------------------
save("23_cirkus", "k_circus", "Cirkus Amárie", "animagine_storybook", [
    C("terka", "Terka", "1girl", "child, brown hair, bun, acrobat, sparkly leotard, tights", "Terka, an 8-year-old circus acrobat girl with a hair bun and a sparkly leotard"),
    C("bimbo", "Bimbo", None, "chihuahua, curly fur, red jacket, small dog", "Bimbo, a curly chihuahua in a red circus jacket"),
    C("boris", "Silák Boris", "1boy", "muscular, giant man, mustache, striped leotard, crying", "Boris the strongman, a giant with a mustache and a striped leotard who cries at beautiful things"),
    C("whisk", "Madam Whisk", "1girl", "mature female, ringmaster, monocle, top hat, red tailcoat", "Madam Whisk, a strict ringmaster with a monocle, top hat and red tailcoat"),
], [L("ring", "indoors, circus tent, circus ring, spotlight, tightrope, empty seats, red and white stripes", "A red-and-white circus big top, a sand ring, a tightrope and spotlights."),
    L("show", "indoors, circus tent, crowd, spotlight, tightrope, night, drums", "The big top at night, full of audience, spotlights on the tightrope.")], [
    P("establishing", "ring", [], ["no humans", "circus tent"], "a red-and-white circus big top with a sand ring, three spotlights and empty seats",
      [N("Cirkusové šapité. Odpolední zkouška.")], gap="small"),
    P("wide", "ring", ["terka", "bimbo"], ["tightrope walking", "balancing", "dog holding net", "confident"], "Terka walks the tightrope confidently, the chihuahua below holds a safety net",
      [S("Bez publika to umím, Bimbo! Bez publika jsem královna provazů!", "terka")]),
    P("close-up", "ring", ["bimbo"], ["chihuahua", "barking", "red jacket", "looking up"], "close-up of the chihuahua barking up at her",
      [PET("Haf! Haf!", "star", "bimbo", "A co potom, až tam budou stovky očí?")]),
    P("medium", "ring", ["terka"], ["tightrope", "nervous", "wobbly", "sweatdrop"], "Terka on the rope looking nervous",
      [S("Pak se mi motají nohy, hlava je jak balon a lano se mění na hada.", "terka"), PET("Whiiiist…", "star", "bimbo", "Hadi jsou taky jen lana, která se bojí."), S("To nechápu, ale zní to chytře.", "terka")]),
    P("wide", "ring", ["boris", "whisk"], ["strongman", "barbell", "crying", "monocle", "stern"], "the strongman lifts a huge barbell with tears in his eyes, the strict ringmaster with a monocle stands beside him",
      [S("Pardon, madam. Byla to… krása. Já se prostě rozbrečím u krásných věcí.", "boris"), S("Siláku Borisi, dnes večer to má být TO NEJLEPŠÍ PŘEDSTAVENÍ. Návštěvnost klesá. Bez Terky na laně to nepůjde. A Terka se bojí publika.", "whisk")]),
    P("medium", "ring", ["boris", "bimbo"], ["strongman", "kind smile", "chihuahua jumping"], "the strongman smiles kindly, the chihuahua jumps excitedly",
      [S("Co kdybychom jí pomohli? Já se taky bojím velkých věcí. A pak to vyjde.", "boris"), PET("Haf! Whiiiist!", "star", "bimbo")]),
    P("medium", "ring", ["whisk"], ["monocle", "raised eyebrow", "top hat"], "the ringmaster lowers her monocle, intrigued",
      [S("Čivava má nápad? Tak ven s ním. Ráda bych viděla, jak pes vymyslí trik.", "whisk")]),
    P("wide", "ring", ["bimbo", "boris"], ["chihuahua on chair", "holding sign", "paper eyes", "empty seats"],
      "the chihuahua stands on a single chair in the empty seats holding a big sign, the strongman scatters piles of paper cut-out eyes on the seats",
      [S("A to má být co?", "terka"), PET("Haf!", "star", "bimbo", "Natrénovala sis lano tisíckrát naostro. Tak si zagoogluješ plné hlediště… hlediště BIMBŮ!")]),
    P("wide", "ring", ["terka"], ["tightrope walking", "confident", "smile", "spotlight"], "Terka steps onto the rope and walks across without hesitation",
      [S("Krása!", "boris"), S("Tak. Čivava vymyslel trik. Zapsat do kroniky.", "whisk")]),
    P("establishing", "show", [], ["crowd", "spotlights", "drums"], "the big top at night packed with audience, spotlights and drums",
      [N("Večerní premiéra.")], gap="small"),
    P("wide", "show", ["terka", "bimbo"], ["tightrope", "jumping", "spin", "chihuahua on tiny bicycle", "spotlight", "crowd cheering"],
      "Terka spins and leaps on the tightrope under the spotlight while the chihuahua rides a tiny bicycle below whistling",
      [S("Oči. Oči. To jsou jen oči. Oči Bimbů.", "terka")], ["BUM BUM"]),
    P("medium", "show", ["whisk"], ["microphone", "ringmaster", "top hat", "proud", "spotlight"], "the ringmaster announces into the microphone, proud",
      [S("Dámy a pánové… čivava Bimbo a lanochodkyně Terka!", "whisk"), PET("Whiiiiist!", "star", "bimbo")]),
    P("medium", "show", ["boris"], ["strongman", "crying", "tissues", "armchair", "backstage"], "backstage the strongman sits in a tiny armchair with a box of tissues, crying happily",
      [N("Boris v zákulisí s krabicí kapesníků.")], ["fňuk!"]),
])

# --- 24 Ledová zahradka -------------------------------------------------------
save("24_ledova_zahradka", "k_icegarden", "Ledová zahradka", "illustrious_storybook", [
    C("marinka", "Márinka", "1girl", "child, blonde hair, long braid, green eyes, warm jacket, mittens, scarf", "Marinka, a 10-year-old gardener from the north with a long blonde braid, a warm jacket and mittens"),
    C("vlocka", "Vločka", None, "arctic fox, white fox, fluffy tail", "Vlocka, a white arctic fox with a huge fluffy tail"),
    C("ledovec", "Stařešina Ledovec", None, "ice giant, giant, icicles, blue skin, beard of ice", "Elder Glacier, a huge grumpy blue ice giant covered in icicles"),
    C("pippop", "Pip a Pop", None, "two reindeer, young reindeer, racing", "Pip and Pop, two young reindeer cousins always racing"),
], [L("garden", "outdoors, snow, ice greenhouse, silver flower, mountains, morning", "A snowy garden with a greenhouse made of ice and a single round silver flower inside, northern mountains."),
    L("peak", "outdoors, mountain peak, snow, icicles, noon, blue sky", "A snowy mountain peak above the garden at noon.")], [
    P("establishing", "garden", [], ["no humans", "greenhouse"], "a snowy northern garden with a greenhouse made of ice, inside it a single glowing silver flower",
      [N("Sněžná zahrada Márinky. Ráno.")], gap="small"),
    P("medium", "garden", ["marinka"], ["kneeling", "talking to plant", "silver flower", "ice greenhouse"], "Marinka kneels by the ice greenhouse talking softly to the silver flower",
      [S("No tak, zlatíčko, ty to zvládneš. Já tě zahřeju, kdybych měla na tobě spát.", "marinka")]),
    P("wide", "garden", ["vlocka"], ["arctic fox", "writing in snow", "tail", "letters in snow"], "the arctic fox writes letters into the snow with its fluffy tail",
      [N("Ve sněhu: CHLAD NOC PŘIJDE"), S("Chlad noc přijde? Vločko, to jako obyčejná noc?", "marinka")]),
    P("close-up", "garden", ["vlocka"], ["arctic fox", "worried", "writing fast", "snow"], "close-up of the fox writing faster in the snow",
      [N("Ve sněhu: VÍC NEŽ NOC. MRAZÍCÍ OBR.")]),
    P("establishing", "peak", ["ledovec"], ["giant", "icicles", "mountain"], "a huge blue ice giant covered in icicles stands on the mountain peak",
      [SH("KDO SE ODVAŽIL ZAHŘÁT ZEMI? CÍTÍM TEPLÍCHNO. TEPLÍCHNO JE ZAKÁZANÉ!", "ledovec")]),
    P("wide", "peak", ["pippop"], ["two reindeer", "racing", "running", "snow spray"], "two young reindeer race each other in the snow",
      [S("Běžím rychleji!", "pippop"), S("Ne! Já!", "pippop")]),
    P("medium", "peak", ["pippop"], ["two reindeer", "stopping", "shocked", "looking up"], "the two reindeer skid to a stop and look up in shock",
      [SH("…Ledovec!", "pippop")]),
    P("medium", "garden", ["ledovec", "marinka"], ["giant", "looming", "brave", "standing firm"], "the giant looms over the garden, Marinka stands firm",
      [S("Tak hele, malá zahradnice. Ta tvoje květina se má ZASTAVIT. Léto nemá co dělat na severu.", "ledovec"), S("Ta květina není narušitelka. Ta květina je NADĚJE. A ta se nesmí zastavit.", "marinka")]),
    P("wide", "garden", ["marinka", "vlocka"], ["ice wall", "fox writing in snow", "shouting"], "the giant raises a wall of ice around the garden, the fox writes huge letters in the snow",
      [N("Ve sněhu: MŮŽEŠ BÝT I OCHRÁNCE"), SH("Obr Ledovče! Pomoz mi tu květinu chránit — ne zničit! Vždyť ty jsi taky zima. A ta květina zimu PŘEŽIJE, když jí dáš zimu na míru!", "marinka")]),
    P("close-up", "peak", ["ledovec"], ["giant", "sad", "icicles", "soft"], "close-up of the ice giant's face softening, icicles tinkling",
      [S("Nikdo mě nikdy… o pomoc nepožádal. Vždycky jen prchali.", "ledovec")], ["cink cink"]),
    P("wide", "garden", ["ledovec", "marinka", "pippop"], ["giant kneeling", "blowing gently", "sparkling flower", "reindeer with sled"],
      "the next day the giant kneels and gently blows frost on the sparkling silver flower, the reindeer pull a sled of fresh snow",
      [N("Ve sněhu: ZIMA + LÁSKA = KVĚTINA"), S("Vločko, ty jsi génius.", "marinka")]),
    P("medium", "garden", ["ledovec", "marinka"], ["giant", "shy", "bowl of soup", "smile"], "Marinka offers the shy giant a bowl of soup",
      [S("Malá zahradnice, kdybys kdykoli potřebovala kouzlo zimy, jsem k dispozici. Stačí zavolat.", "ledovec"), S("A já ti můžu nabídnout bramborovou polévku.", "marinka")]),
    P("close-up", "garden", ["ledovec"], ["giant", "holding tiny bowl", "embarrassed"], "the giant holds a tiny bowl of soup, embarrassed",
      [S("Polévku neznám. Ale zkusím.", "ledovec")]),
])

# --- 25 Strašidelný čokoládový zámek -----------------------------------------
save("25_cokoladovy_zamek", "k_chococastle", "Strašidelný čokoládový zámek", "flux_schnell_ink", [
    C("klarinka", "Klárinka", "1girl", "child, brown hair, bob cut, detective, trench coat, magnifying glass, flashlight", "Klarinka, an 8-year-old girl detective with a brown bob in a long coat full of tools, holding a magnifying glass"),
    C("cmuchalek", "Čmuchálek", None, "black cat, one white paw", "Cmuchalek, a mysterious black cat with one white paw"),
    C("baron", "Baron Popletal", None, "ghost, translucent, baron, old clothes, wig", "Baron Popletal, a clumsy translucent ghost in an old baron's coat and wig"),
    C("tekleria", "Paní Teklérie", "1girl", "old woman, witch, tall, glasses, dark cloak", "Mrs. Tekleria, a tall old witch in glasses and a dark cloak who sells chocolate"),
], [L("gate", "outdoors, night, castle gate, fog, jack-o'-lantern, bare trees, halloween", "A cracked castle gate on a foggy Halloween evening, pumpkin lanterns, bare black trees."),
    L("hall", "indoors, castle hall, broken candelabra, cobwebs, portrait, shutters", "A great castle hall with broken candelabras, cobwebs and a huge portrait."),
    L("kitchen", "indoors, castle kitchen, cauldron, chocolate wrappers, flashlight", "The castle kitchen, a cauldron full of chocolate wrappers."),
    L("party", "indoors, castle, halloween party, pumpkins, chocolate, children in costumes, night", "The castle decorated with pumpkins for a Halloween party, a table piled with chocolate.")], [
    P("establishing", "gate", [], ["no humans", "castle"], "a cracked castle gate on a foggy Halloween evening with pumpkin lanterns and bare black trees",
      [N("Zámecká brána. Halloweenský večer.")], gap="small"),
    P("wide", "gate", ["klarinka", "cmuchalek"], ["magnifying glass", "detective", "cat sniffing pumpkin"], "Klarinka puts on her magnifying glass in front of the gate, the black cat sniffs a pumpkin",
      [S("Případ číslo 13: zmizelá čokoláda celého městečka. Stopa vede sem. Do zámku, kam nikdo nevkročil sto let.", "klarinka")]),
    P("close-up", "gate", ["cmuchalek"], ["black cat", "mysterious", "glowing eyes"], "close-up of the black cat looking mysterious",
      [S("Něco ti povím, detektivko. Ten zámek straší. Ale straší ho duch, který… jak to říct… který se straší i sám.", "cmuchalek"), S("To znamená co?", "klarinka"), S("Znamená to, že když se v tmě ozve zaúpění, je to buď on… nebo lednička.", "cmuchalek")]),
    P("wide", "hall", ["klarinka", "cmuchalek", "baron"], ["flashlight", "ghost", "stuck in shutter", "portrait", "boo"],
      "in the dusty hall a translucent ghost pops out of a huge portrait with his head stuck in a window shutter, Klarinka shines her flashlight on him",
      [SH("BUUU!", "baron"), S("Aha. Vy jste ten duch. Barone… vy jste zaseknutý v okenici?", "klarinka")]),
    P("medium", "hall", ["baron"], ["ghost", "embarrassed", "stuck", "shutter"], "the ghost baron, stuck in the shutter, looks embarrassed",
      [S("To je dlouhá historie. Strašil jsem, utíkal jsem, zapomněl jsem se otočit. Pomů… pomů… pomůžete mi?", "baron")]),
    P("close-up", "hall", ["cmuchalek"], ["black cat", "deadpan"], "the black cat looks at the viewer deadpan",
      [S("Vidíš, Klárko. Sliboval jsem ti kvalitní zločin, a místo toho máme záchranné práce.", "cmuchalek")]),
    P("wide", "kitchen", ["klarinka", "baron"], ["cauldron", "chocolate wrappers", "flashlight", "pointing"], "Klarinka finds a cauldron full of chocolate wrappers and points at the ghost",
      [S("A tady je čokoláda! Barone, sníst čokoládu celého města, to je… ten zločin, který hledám!", "klarinka"), S("Já jsem ji nejedl! Já jsem ji jen… ukradl. Protože jsem strašil sto let a nikdo se nebál. Tak jsem si řekl — když už straším, alespoň ukradnu čokoládu, aby sem někdo přišel.", "baron")]),
    P("medium", "kitchen", ["baron"], ["ghost", "sad", "lonely"], "the ghost hangs his head sadly",
      [S("Takže vy jste se… NUDIL?", "klarinka"), S("Já jsem osamělý. Sto let jsem strašil a nikdo se mě nebál. Chtěl jsem, aby sem někdo přišel. I kdyby mě chtěl jen chytit.", "baron")]),
    P("wide", "kitchen", ["tekleria", "baron", "klarinka"], ["tall witch", "doorway", "ghost hiding behind girl"], "a tall witch in glasses enters, the ghost tries to hide behind the little detective",
      [S("Tak tady je moje čokoláda! Barone, to vy?", "tekleria"), S("Vrátím vám ji… jen prosím… neříkejte nikomu, že jsem ji neuměl sníst.", "baron")]),
    P("medium", "kitchen", ["tekleria"], ["witch", "taking off glasses", "smile"], "the witch takes off her glasses and smiles kindly",
      [S("Barone, já jsem čarodějnice. Vyrábím čokoládu s kouzlem. Ta se nesní sama od sebe… ta se musí PODĚLIT.", "tekleria"), S("Kouzelná čokoláda, která se musí podělit. To je dneska to nejlepší pravidlo, co jsem slyšel.", "cmuchalek")]),
    P("wide", "party", ["baron", "tekleria", "klarinka", "cmuchalek"], ["halloween party", "children in costumes", "ghost telling stories", "chocolate"],
      "a Halloween party in the castle: the ghost happily tells stories to children in costumes, the witch hands out chocolate",
      [S("A pak jsem se strašil sám! Sto let!", "baron"), SH("Více! Více!", None)]),
    P("medium", "party", ["klarinka", "cmuchalek"], ["detective hat", "chocolate spider", "smile", "black cat"], "Klarinka wearing a detective hat with a chocolate spider whispers to the cat",
      [S("Případ číslo 13 uzavřen. Zločinec nebyl zlý. Byl sám.", "klarinka"), S("To už nejsou detektivní závěry. Tohle je moudrost.", "cmuchalek")]),
])
