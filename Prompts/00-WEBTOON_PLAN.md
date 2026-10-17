# WEBTOON_PLAN.md — Interaktivní nekonečný webtoon (Ol1nLLM)

Handoff pro Claude Code. Projekt: generátor vertikálních webtoonů s nekonečným, čtenářem řízeným pokračováním, zasazeným do světů, které definuje autor ("Dungeon Master"). Běží nad existujícím stackem Ol1n (vLLM/LiteLLM na Sparku, ComfyUI, Go backend, Flutter klient). Rozšíření aplikace Ol1nLLM, ne samostatný produkt.

---

## 1. Cíl a vize

- **Formát:** vertikální scroll (webtoon). Stream panelů na jednom dlouhém plátně, mezery mezi panely = timing.
- **Obsah:** AI generované panely + řečové bubliny renderované jako overlay (ne v obrázku).
- **Interaktivita:** na konci každého dílu čtenář volí, jak to pokračuje (uzavřené volby + volný text). Vygeneruje se nový díl. Nekonečný příběh.
- **Role:**
  - **Autor (DM)** — vlastní *svět*: prostředí, postavy, styl, kánon a mantinely. Pouští do něj čtenáře.
  - **Hráč (čtenář)** — vlastní *kampaň*: vlastní větev příběhu ve světě, vlastní postava, rozhodnutí. Může přidat/odebrat postavu a měnit prostředí jen v mezích, které autor povolil.
- **Rozdíl autor/hráč setřený na úrovni UI** (jeden účet může obojí), ostrý na úrovni dat a práv.

## 2. Doménový model

Hierarchie: **World → Campaign → Episode → Panel**

### World (autor)
- `id, owner_id, title, synopsis, tone, audience (kids/teen/adult), language`
- `style_id` — zamčený výtvarný styl pro celý svět = style preset (artist tagy + sampler), viz §5.4
- `bible` — strukturovaný "world bible" JSON: lokace, frakce, pravidla světa, lore
- `canon` — seznam kanonických uzlů (události, kterými musí každá kampaň projít / které nelze změnit) + zakázané akce (constraints)
- `permissions` — co hráč smí: `can_add_characters, can_create_character, can_change_location, allowed_locations[], max_episodes`, apod.
- `visibility` — private / unlisted / public
- `intro_episode_ids[]` — volitelné společné úvodní díly

### Character (autor nebo hráč v mezích)
- `id, world_id, name, role (npc/playable/player_created), description, personality, speech_style`
- `tag_prompt` — pevný booru-tagový popis designu (vkládá se do každého panelu s postavou); viz §5.4
- `reference_images[]` — character sheet (front/side/3-4, výrazy)
- `identity_level` — `prompt | ip_adapter | lora`
- `identity_asset` — IP-Adapter embedding nebo LoRA cesta na Sparku (nullable)
- `owner_id` — autor světa, nebo hráč (player_created)

### Location (autor)
- `id, world_id, name, description, tag_prompt, reference_images[], mood`

### Campaign (hráč)
- `id, world_id, player_id, title, status`
- `player_character_id`
- `state` — **story state JSON** (viz §4): živé postavy, kde jsou, vztahy, inventář, otevřené zápletky, timeline
- `canon_progress` — které kanonické uzly už proběhly
- `branch_parent_episode_id` — nullable; v1 lineární, pole připravit pro větvení

### Episode
- `id, campaign_id, index, title, status (queued/generating/ready/failed)`
- `storyboard` — JSON z LLM (viz §5)
- `panels[]`
- `choices[]` — otázky/volby na konci: `{id, text, kind: closed|free|director}`
- `chosen` — co hráč vybral / napsal
- `state_diff` — změna story state, kterou díl způsobil
- `credits_cost`

### Panel
- `id, episode_id, index, image_url, prompt, seed, aspect (w/h), gap_after`
- `characters[]` — id + bbox/mask (pro umístění ocásků bublin)
- `bubbles[]` — `{speaker_id, text, kind: speech|thought|shout|narration, anchor: {x,y}, tail: bool}`
- `sfx[]` — `{text, position, style}`

## 3. Architektura

```
Flutter (Ol1nLLM app, modul "Webtoon")
   │
   ▼
Go backend  (JODA, Docker Compose, Postgres, sqlc, golang-migrate)
   ├─ API: worlds / characters / locations / campaigns / episodes
   ├─ Job queue: episode generation (async, status polling + push)
   ├─ LLM client → LiteLLM (Spark, vLLM)
   └─ Image client → ComfyUI (Spark) workflow API
```

- Generace dílu je **async job**: hráč zvolí → episode `queued` → worker: LLM storyboard → validátor → N× ComfyUI → postprocess → `ready` → push notifikace.
- Progresivní zobrazení: panely se ukládají postupně, klient může číst díl s prvními hotovými panely (`status: generating`, `panels_ready: k/N`).
- Obrázky: object storage (MinIO na JODA nebo FS za Caddy), URL přes `*.ol1n.com`.

## 4. Story state (paměť kampaně)

Nespoléhat na kontext předchozích dílů jako text. Udržovat strukturovaný stav:

```json
{
  "characters": {"<id>": {"alive": true, "location": "<loc_id>", "status": "zraněný", "relations": {"<id>": "spojenec"}, "inventory": []}},
  "current_location": "<loc_id>",
  "open_threads": ["hledá ztracený klíč", "král neví o zradě"],
  "timeline": [{"episode": 3, "event": "..."}],
  "facts": ["most přes řeku je zničený"],
  "mood": "napětí"
}
```

- Po každém dílu LLM vyprodukuje `state_diff`; backend ho aplikuje (merge) a uloží snapshot u episode (umožní pozdější větvení).
- Dlouhé kampaně: `timeline` komprimovat (LLM sumarizace starších dílů), `facts` a `open_threads` držet celé. Případně RAG nad episode summaries (stávající RAG stack Ol1nLLM).

## 5. Generační pipeline dílu

### 5.1 Vstup pro LLM — tři vrstvy promptu
1. **World bible** (statická): tón, publikum, lore, styl vyprávění, pravidla světa.
2. **Kánon + mantinely**: nesplněné kanonické uzly (které smí/má díl posunout), constraints, permissions.
3. **Kampaň**: story state, posledních K dílů (sumarizované), hráčova postava, hráčova volba / volný text.

### 5.2 Výstup: storyboard JSON
```json
{
  "title": "...",
  "panels": [
    {
      "shot": "close-up|medium|wide|over-shoulder|establishing",
      "location_id": "...",
      "characters": [{"id": "...", "emotion": "...", "action": "..."}],
      "visual_prompt": "...",
      "bubbles": [{"speaker_id": "...", "text": "...", "kind": "speech"}],
      "sfx": [],
      "gap_after": "small|medium|large"
    }
  ],
  "choices": [
    {"kind": "closed", "text": "..."},
    {"kind": "closed", "text": "..."},
    {"kind": "free", "text": "Nebo napiš, co uděláš…"}
  ],
  "state_diff": {...},
  "canon_nodes_reached": []
}
```
- v1: pevný počet panelů (6–8), 2–3 uzavřené volby + 1 volná.
- Použít JSON mode / structured output přes LiteLLM; validovat schématem.

### 5.3 Validátor (před ComfyUI)
- Schéma, počet panelů, všechny `character_id`/`location_id` existují ve světě.
- Constraints: druhý LLM call "porušuje díl některé pravidlo světa?" → pokud ano, regenerovat s doplněnou instrukcí (max 2 pokusy).
- Moderace: vstup hráče i výstup (hlavně `audience: kids`).

### 5.4 Obrázky (ComfyUI na Sparku)

**Model:** NoobAI-XL (Illustrious základ) nebo WAI — booru-tagové anime modely. Výhody: nativní Danbooru/e621 tagy, `artist:xxx` tagy pro styl, dobré držení designu postavy popsané tagy, snadný trénink LoRA s 10–20 obrázky. Pozor: NoobAI existuje jako **eps** i **v-prediction** varianta — v-pred vyžaduje jiné nastavení (CFG rescale / `ModelSamplingDiscrete` v-pred, bez Karras samplerů); workflow zafixovat na jednu variantu.

**Struktura promptu** (pořadí dle guidebooku NoobAI): `quality tags, <1girl/1boy/...>, <character prompt>, <artist/style preset>, <scene tags z storyboardu>, <special tags>`. LLM ve storyboardu negeneruje volný text, ale **booru tagy** pro `visual_prompt` (přidat do systémového promptu seznam použitelných tagů / few-shot).

**Styl — řešeno artist tagy.** Každý `World.style_id` = preset: 1–3 `artist:` tagy s váhami + doplňkové estetické tagy (`flat color`, `screentones`, `monochrome`…) + fixní sampler/CFG. Zamčeno per svět → konzistentní vzhled bez style LoRA. StyleMap picker je nice-to-have pro M4, v1 kurátorovaný seznam presetů s náhledy.

**Identita — tři úrovně, podle toho co vyjde v M0:**
1. **Character prompt (vždy):** `Character.tag_prompt` = pevný booru popis designu (barva/délka vlasů, oči, oblečení kus po kuse, doplňky, tělesné znaky). Vygenerován LLM z popisu + referencí, autor může editovat. Vkládá se doslovně do každého panelu, kde postava je. Pro jednoduché designy často stačí.
2. **IP-Adapter (volitelně per postava):** z character sheetu, pokud prompt neudrží obličej/detaily. Posílat jen postavy přítomné v panelu.
3. **LoRA (premium, M4):** pro hlavní postavy světa, 10–20 obrázků z character sheetu + vygenerovaných variant; trénink na Sparku (navazuje na realeyes-lora pipeline). Autor si ji "koupí" za kredity.
- Character tagy známých postav (Danbooru jména) **nepoužívat** — autorská práva, store review. Model využíváme pro to, že drží *koncept* designu, ne pro cizí IP.

**Konzistence prostředí:** `Location.tag_prompt` stejným způsobem + reference image jako druhý IP-Adapter vstup / img2img s nízkým denoise pro establishing shoty.

**Bezpečnost obsahu:** NoobAI/WAI jsou trénované i na NSFW. Pro `audience: kids` povinné: `rating:general`/`safe` + pevný negativ (`nsfw, nude, ...`), SFW tag preset, a výstupní klasifikátor (NSFW detektor) před uložením panelu; při hitu regenerovat s jiným seedem (max 2×), pak panel označit `failed`.

- Jeden workflow per style preset, parametrizovaný: prompt, aspect (webtoon panely na výšku, např. 832×1216), seed, reference postav.
- **Negativní prompt** vždy obsahuje `text, letters, speech bubble, watermark, signature` — text do obrázku nikdy.
- Postprocess: detekce postav (segmentace, např. GroundingDINO+SAM, nebo jednodušeji bbox z detektoru) → `characters[].bbox` pro ocásky bublin.

### 5.5 Bubliny a text (Flutter overlay)
- Renderovat ve Flutteru nad panelem: bublina, ocásek směrem na bbox mluvčího, font (cute_kid_fonts), typ bubliny (řeč/myšlenka/křik/narace).
- Automatické rozmístění: bublina do volného prostoru panelu (jednoduchá heuristika: rohy mimo bbox postav), přetékání textu zalamovat.
- Text je editovatelný a lokalizovatelný bez regenerace obrázku.

## 6. Flutter klient (modul v Ol1nLLM)

### Čtenář
- Seznam světů (veřejné + moje) → svět detail → "Začít kampaň" (volba/tvorba postavy v mezích) → čtečka.
- **Čtečka:** `CustomScrollView` / `ListView` s panely jako obrázky + `Stack` overlay bublin; mezery podle `gap_after`; na konci dílu blok s volbami + textové pole + "režisérská" sekce (přidat/odebrat postavu, změnit lokaci — jen pokud world.permissions dovolí).
- Stav "generuje se" s progresem panelů; push notifikace po dokončení.
- Historie dílů kampaně, scroll zpět.

### Autor
- Editor světa: synopsis, tón, publikum, styl (v1: seznam style presetů s náhledy; M4: StyleMap picker), lore.
- Knihovna postav: popis → LLM vygeneruje `tag_prompt` → vygenerovat character sheet → autor doladí tagy; role, kdo je playable; volitelně IP-Adapter / LoRA.
- Knihovna lokací.
- Kánon editor: seznam uzlů (pořadí, popis), constraints (volný text → LLM je drží), permissions přepínače.
- Dashboard: počet kampaní, kde hráči skončili, rozložení voleb, player_created postavy (zpětná vazba na design světa).
- Náhled: "zahraj si vlastní svět" = běžná kampaň.

### Společné
- Export dílu: dlouhý PNG strip, PDF, share.
- Kredity: cena dílu = počet panelů; zobrazit před potvrzením volby.

## 7. Go backend — endpoints (návrh)

```
POST   /worlds                       create
GET    /worlds?visibility=public
GET    /worlds/{id}
PATCH  /worlds/{id}                  bible, canon, permissions, style
POST   /worlds/{id}/characters       (+ upload reference images)
POST   /worlds/{id}/locations
GET    /worlds/{id}/stats            author dashboard

POST   /campaigns                    {world_id, player_character}
GET    /campaigns/{id}               state, episodes summary
POST   /campaigns/{id}/episodes      {choice_id | free_text, director: {...}} → 202 + episode_id
GET    /episodes/{id}                status, panels_ready, panels, choices
PATCH  /episodes/{id}/panels/{n}     edit bubble text, regenerate panel
GET    /episodes/{id}/export?fmt=png|pdf
```

- Worker: samostatný proces (nebo goroutine pool) tahající z job tabulky (Postgres `SELECT … FOR UPDATE SKIP LOCKED`), stejný pattern jako AiStack job queue.
- Auth: stávající Ol1nLLM účty.

## 8. Milníky

**M0 — Spike (1–2 dny) na NoobAI-XL / WAI**
- Jedna originální postava (ne známá IP) → LLM vygeneruje `tag_prompt` → jeden artist preset → 6 panelů různých záběrů/emocí/lokací, **jen prompt, bez IP-Adapteru**. Změřit, jestli drží obličej, vlasy, oblečení.
- Pokud nedrží: zopakovat s IP-Adapterem z character sheetu. Výsledek určí default `identity_level` pro M1.
- Odstavec → LLM storyboard JSON (booru tagy) → ComfyUI → složit vertikální strip s bublinami (skript).
- Ověřit eps vs. v-pred variantu a NSFW klasifikátor na výstupu.

**M1 — Lineární webtoon**
- Datový model World/Character/Campaign/Episode/Panel, migrace.
- Worker pipeline (LLM → validátor → ComfyUI → postprocess).
- Flutter čtečka s overlay bublinami. Jeden svět natvrdo, jeden styl.

**M2 — Interaktivita**
- Volby na konci dílu, story state + state_diff, nekonečné pokračování, push notifikace, kredity.

**M3 — Autor/DM**
- Editor světa, knihovna postav/lokací, kánon + constraints + permissions, validátor pravidel, veřejné světy, dashboard.

**M4 — Nadstavby**
- Větvení kampaní (strom, fork cizí kampaně), setkání hráčů v jednom světě, StyleMap picker místo seznamu presetů + "přestylovat celý díl", LoRA per postava jako premium pro autory, autorská monetizace (podíl z kreditů), prodej postav/LoRA.

## 9. Otevřené otázky

- Který model na storyboard (Qwen/Llama na Sparku stačí? potřeba dobrý JSON mode a znalost booru tagů — ověřit, případně few-shot).
- NoobAI-XL vs. WAI — který lépe drží design originální postavy jen z tagů (M0 rozhodne); eps vs. v-pred.
- Identita: stačí `tag_prompt`, nebo je default IP-Adapter? Čas tréninku LoRA per postava na Sparku vedle vLLM.
- Licence NoobAI/Illustrious (fair-ai-public-license) — ověřit podmínky pro komerční službu.
- Detekce bbox postav — jaký detektor se vejde vedle vLLM a ComfyUI do 128 GB.
- Moderace pro `kids` — vlastní LLM klasifikátor nebo externí.
- Jak velký má být "díl" (6–8 panelů ≈ 1–2 min čtení?) a cena v kreditech.

## 10. Vazby na existující projekty

- **Ol1nLLM** — hostitelská appka, účty, RAG stack.
- **StyleMap** — výběr stylu světa.
- **realeyes-lora / FineTune** — LoRA per postava, metadata generací.
- **cute_kid_fonts** — fonty bublin.
- **anime-story-videos** — knihovna postav, případně animovaný panel jako M4 bonus.
- **AiStack** — job queue pattern.
- **Discord bot** — notifikace o dokončených dílech / releasech.
