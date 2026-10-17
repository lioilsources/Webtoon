# Webtoon

Interaktivní nekonečný webtoon: autor (DM) definuje svět, čtenář na konci každého dílu volí, jak příběh pokračuje, a nový díl se vygeneruje (LLM storyboard → SDXL panely → bubliny jako overlay).

Plán: [`Prompts/00-WEBTOON_PLAN.md`](Prompts/00-WEBTOON_PLAN.md)

| adresář | co to je |
|---|---|
| `m0/` | M0 spike v Pythonu (stdlib + Pillow): postava → booru tagy, storyboard + validátor, story state, ComfyUI render, WD14 kontrola obsahu a identity, skládání stripu |
| `backend/` | M1 Go backend: API, Postgres fronta (`SKIP LOCKED`), worker pipeline — viz `backend/README.md` |
| `app/` | Flutter klient (čtečka + později editor autora) |
| `data/` | testovací svět, style presety, slovník WD14 tagů |
| `assets/fonts/` | fonty bublin (OFL, z cute_kid_fonts) |

## M0 výsledky (2026-10-17)

- Identita postavy drží **jen z promptu** (booru `tag_prompt`) → výchozí `identity_level = prompt`.
- NoobAI-XL eps; tagy umělců neškodí. IP-Adapter v prvním nastavení rozbil obraz (k přeměření).
- WD14 rating jako NSFW klasifikátor: 39/39 obrázků `general`.

Generování obrázků běží na vlastním GPU serveru (ComfyUI + vLLM) a není součástí repa; endpointy se nastavují env proměnnými (`WEBTOON_LLM`, `WEBTOON_COMFY`, `WEBTOON_WD14`).
