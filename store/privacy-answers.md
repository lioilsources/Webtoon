# Odpovědi do formulářů o soukromí: Toonfork

Připravené odpovědi pro **App Store Connect → App Privacy** a **Google Play Console → Data safety** k anonymním
statistikám čtečky (`docs/telemetry.md`, politika `docs/privacy.html`). Vyplňují se až těsně před vydáním buildu s
klíčem `TELEMETRY_KEY`; do té doby platí staré „Data Not Collected“ / „No data collected“. Formuláře vyplňuje Olin.
Před vyplněním ověř aktuální znění otázek, mění se.

Co platí pro obě: statistiky posílá jen čtečka v profilu Dospělí (dětský profil a Studio se neměří), bez jména,
účtu, identifikátoru zařízení a obsahu příběhů, s náhodným ID relace jen v paměti. Přijímá je vývojář na vlastním
serveru v EU (Česko), nikdo další je nedostane. IP adresa se neukládá, uchová se jen země. Uchování 12 měsíců.
Vypínač: Nastavení → Anonymní statistiky.

## App Store Connect → App Privacy

Data Collection: **Yes, we collect data from this app.**

| Typ dat | Účel | Propojeno s uživatelem | Sledování |
|---|---|---|---|
| Usage Data → **Product Interaction** | Analytics | No | No |
| Diagnostics → **Performance Data** (doba načtení balíčků při startu) | Analytics | No | No |

Ostatní typy (Contact Info, Identifiers, Location, User Content, Purchases, Browsing History, Search History,
Sensitive Info, Health, Financial, Contacts, Other) **nesbírá**. Nákupy zpracovává Apple a appka si nárok drží
jen v zařízení; to se jako „collected“ neuvádí.

Shoduje se s `app/ios/Runner/PrivacyInfo.xcprivacy` a `app/macos/Runner/PrivacyInfo.xcprivacy`
(`NSPrivacyTracking` false, žádné tracking domény).

**Otevřená otázka pro Olina:** země z připojení. Kirian ji v App Privacy uvádí jako Location → Coarse Location
(Analytics, nepropojeno). Tady je vynechaná, protože ji neposílá appka, ale odvodí ji příjemce z IP. Pokud chceš
stejný postup jako Kirian, přidej Coarse Location sem i do obou `PrivacyInfo.xcprivacy`.

## Google Play Console → Data safety

Data collection and security:

| Otázka | Odpověď |
|---|---|
| Does your app collect or share any of the required user data types? | **Yes** |
| Is all of the user data collected by your app encrypted in transit? | **Yes** (HTTPS) |
| Do you provide a way for users to request that their data is deleted? | **No**: žádný účet, statistiky jsou anonymní a nejde je přiřadit člověku. Vypínač v Nastavení hned smaže, co čeká v zařízení. |

Data types:

| Kategorie → typ | Collected | Shared | Processed ephemerally | Required / optional | Účel |
|---|---|---|---|---|---|
| App activity → **App interactions** | Yes | No | No | **Optional** (users can turn it off) | Analytics |
| App info and performance → **Diagnostics** (doba načtení) | Yes | No | No | **Optional** | Analytics |

Nic dalšího (Location, Personal info, Financial info, Messages, Photos, Files, Device or other IDs, …) se
nesbírá ani nesdílí. Platby zpracovává Google Play.

Target audience zůstává 16+ (appka není v Designed for Families); dětský profil se neměří.

## Mimo repo, změnit před zapnutím

- App Store Connect → App Privacy (tabulka výše).
- Play Console → Data safety (tabulka výše).
- Stránka appky na olin.now: repo `ol1n.now`, `apps/webtoon/i18n/<jazyk>.md` řádek 33 („No account, no ads, no
  tracking. Toonfork collects no personal data; …“) ve všech jazycích stránky. Doplnit, že čtečka posílá anonymní
  statistiky, které jdou vypnout (vzor: věta v `store/listing/*/description.txt`).
