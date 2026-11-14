# Zásady ochrany osobních údajů – Toonfork

*Platné od: 14. listopadu 2026*

Aplikaci Toonfork (dále „aplikace“) vydává ol1n (dále „my“). Tyto zásady popisují, jak aplikace zachází s informacemi o vás. Ve zkratce: **žádné osobní údaje nesbíráme.** Abychom věděli, kde je aplikace nejasná, posílá čtečka anonymní statistiky používání popsané níže. Kdykoli je můžete vypnout. V dětském profilu se neměří nic.

## Co nesbíráme

- Aplikace nemá uživatelské účty ani registraci.
- Neobsahuje reklamy, analytiku třetích stran, sledovací nástroje ani žádné SDK třetích stran pro reklamu nebo měření.
- Neodesílá nám nic, podle čeho by šlo poznat vás, a nic z obsahu toho, co čtete: žádné názvy, bubliny, volby ani nic, co napíšete.
- Nesleduje vás napříč aplikacemi ani webovými stránkami.

## Anonymní statistiky používání

**Co se posílá.** Krátké záznamy o okamžicích v aplikaci: aplikace se otevřela nebo odešla do pozadí (a jak dlouho se používala), která obrazovka se zobrazila a na jak dlouho, díl se začal číst a dočetl nebo opustil (jeho pořadí v příběhu a strávené sekundy), otevřel se gamebook, udělal se krok (druh volby a kolik kroků zatím) nebo se dosáhlo konce, které akce editoru větví se použily, zda prošel rodičovský zámek před nákupem, začal nákup nebo stahování a jak skončil (druh produktu a doba v sekundách), jak dlouho trvalo spuštění, které chyby se zobrazily a které funkce se použily. Každý záznam nese i verzi aplikace, platformu (například iOS nebo Android), jazyk aplikace a bublin a dvě hrubá pásma: zhruba kolikrát se aplikace na tomto zařízení použila (1, 2, 3–5, 6–10, 11+) a zhruba před kolika dny měření začalo (0, 1, 2–6, 7–29, 30+). Úplný seznam je zveřejněný ve zdrojovém repozitáři aplikace ([docs/telemetry.md](https://github.com/lioilsources/Webtoon/blob/main/docs/telemetry.md)).

**Proč.** Abychom viděli, kolik nových čtenářů se od prvního spuštění dostane k prvnímu dočtenému dílu, kde přestávají číst, zda se používají gamebooky a editor větví a kde selhávají nákupy nebo stahování, a mohli to opravit.

**Žádné identifikátory, nic o příbězích.** Statistiky neobsahují jméno, e-mail, účet, identifikátor zařízení ani reklamní identifikátor, ani model zařízení. Neobsahují název ani id příběhu, dílu či balíčku, text bublin ani voleb, nic z toho, co napíšete v editoru větví, a nic o odpovědi v rodičovském zámku. Každá relace dostane náhodné číslo, které existuje jen po dobu běhu aplikace, takže dvě relace nejde spojit spolu ani s vámi. Statistiky se nepoužívají k reklamě ani sledování a neprodávají se ani nesdílejí.

**V dětském profilu ne.** Když je zvolený dětský profil, nic se nezaznamenává ani neposílá, ani to, že se aplikace otevřela. Totéž platí při prvním spuštění, dokud není profil vybraný. Měření začne jen v profilu pro dospělé, který chrání rodičovský zámek.

**Kdo je dostává a kde.** Statistiky přijímáme a ukládáme my, vývojář, na vlastním serveru v EU (Česko). Nikdo další je nedostane; žádná analytická služba třetí strany se nepoužívá. Při odeslání, jako při každém připojení k internetu, uvidí náš server vaši IP adresu. Použije se jen k určení země a neukládá se ani nezapisuje do logů. Země je jediný údaj o poloze, který se uchovává.

**Jak dlouho.** Statistiky uchováváme 12 měsíců, pak je mažeme.

**Offline.** Aplikace funguje plně offline. Bez připojení čeká v zařízení nejvýš 500 posledních záznamů, které se odešlou později; starší se zahazují.

**Jak je vypnout.** V profilu pro dospělé otevřete *Nastavení* a vypněte *Anonymní statistiky*. Platí to hned: záznamy čekající v zařízení se smažou a nic dalšího se neodešle, dokud je znovu nezapnete.

## Co zůstává ve vašem zařízení

Aplikace ukládá pouze do vašeho zařízení:
- zvolený profil čtenáře (Děti / Dospělí) a jazyk;
- postup čtení, stav gamebooků (aktuální uzel, nalezené konce) a vaše vlastní větve vytvořené v editoru;
- seznam zakoupených produktů (nároky) a potvrzení o nákupu od obchodu;
- stažené balíčky příběhů a kopii katalogu;
- pro statistiky: den začátku měření, počitadlo relací, stav vypínače a záznamy čekající na odeslání.

Kromě anonymních statistik popsaných výše tato data neopouštějí zařízení. Smažete je odinstalováním aplikace. Vlastní větev gamebooku odejde ze zařízení jen tehdy, když ji sami odešlete přes systémové sdílení. Komu ji pošlete, je vaše volba.

## Nákupy

Nákupy v aplikaci zpracovává Apple (App Store) nebo Google (Google Play) podle jejich vlastních podmínek a zásad ochrany soukromí. My nevidíme vaše jméno, platební kartu ani e-mail. Aplikace od obchodu dostane jen potvrzení, že produkt vlastníte, a uloží ho ve vašem zařízení.

## Stahování obsahu

Katalog, obálky a balíčky příběhů aplikace stahuje ze služeb GitHub Pages a GitHub Releases (GitHub, Inc.). Jako každý webový server vidí GitHub při stahování IP adresu vašeho zařízení a technické údaje o požadavku. GitHub s nimi nakládá podle svých zásad: https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement. Tyto údaje nedostáváme a nijak je nespojujeme s vámi.

## Děti

Aplikace nabízí dětský profil. Nákupy a přepnutí na profil pro dospělé chrání rodičovský zámek. Od dětí ani od nikoho jiného žádné osobní údaje nesbíráme a v dětském profilu se nezaznamenávají vůbec žádné statistiky.

## Vaše práva

Protože o vás žádné osobní údaje nezpracováváme, nemáme co zpřístupnit, opravit ani vymazat: anonymní statistiky neobsahují nic, podle čeho bychom našli záznamy konkrétního člověka. Statistiky můžete kdykoli vypnout a data uložená v zařízení máte plně pod kontrolou. S dotazy se obracejte na business@olin.now. Máte také právo podat stížnost u dozorového úřadu (v Česku Úřad pro ochranu osobních údajů, https://www.uoou.cz).

## Změny

Pokud se tyto zásady změní, zveřejníme novou verzi na této stránce s novým datem účinnosti.

## Kontakt

ol1n, business@olin.now

---

# Privacy Policy – Toonfork

*Effective date: November 14, 2026*

Toonfork (the "app") is published by ol1n ("we"). This policy explains how the app handles information about you. In short: **we collect no personal data.** To learn where the app is confusing, the reader sends anonymous usage statistics, described below, which you can turn off at any time. In the Kids profile nothing is measured.

## What we do not collect

- The app has no user accounts and no sign-up.
- It contains no advertising, no third-party analytics, no tracking tools and no third-party SDKs for advertising or measurement.
- It sends us nothing that identifies you and nothing about the content of what you read: no titles, no bubbles, no choices, nothing you write.
- It does not track you across other apps or websites.

## Anonymous usage statistics

**What is sent.** Short records of moments in the app: it was opened or went to the background (and how long it was used), which screen was shown and for how long, an episode was started and read to its end or left (its number within the story and the seconds spent), a gamebook was opened, a step was taken (the kind of choice and how many steps so far) or an ending was reached, which actions of the branch editor were used, whether the parental gate before a purchase was passed, a purchase or a download started and how it ended (the kind of product and the seconds it took), how long start-up took, which errors were shown and which features were used. Each record also carries the app version, the platform (for example iOS or Android), the app and bubble language, and two coarse bands: roughly how many times the app has been used on this device (1, 2, 3–5, 6–10, 11+) and roughly how many days ago measuring began (0, 1, 2–6, 7–29, 30+). The full list is published in the app's source repository ([docs/telemetry.md](https://github.com/lioilsources/Webtoon/blob/main/docs/telemetry.md)).

**Why.** To see how many new readers get from the first launch to their first finished episode, where they stop reading, whether gamebooks and the branch editor are used and where purchases or downloads fail, so we can fix it.

**No identifiers, nothing about the stories.** The statistics contain no name, no email, no account, no device or advertising identifier and no device model. They contain no story, episode or pack name or id, no bubble or choice text, nothing you write in the branch editor and nothing about the answer to the parental gate. Each session gets a random number that exists only while the app runs, so two sessions cannot be linked to each other or to you. The statistics are not used for advertising or tracking and are not sold or shared.

**Not in the Kids profile.** While the Kids profile is chosen, nothing is recorded or sent, not even that the app was opened. The same applies on the first launch until a profile is chosen. Measuring starts only in the Adults profile, which is behind the parental gate.

**Who receives them, and where.** The statistics are received and stored by us, the developer, on our own server in the EU (Czech Republic). No one else receives them; no third-party analytics service is involved. Sending them, like any internet connection, reveals your IP address to our server; it is used only to derive your country and is neither stored nor logged. Your country is the only location information kept.

**How long.** Statistics are kept for 12 months and then deleted.

**Offline.** The app works fully offline. Without a connection, up to 500 recent records wait on your device and are sent later; older ones are discarded.

**How to turn them off.** In the Adults profile, open *Settings* and switch off *Anonymous statistics* (the label is translated into your language). This takes effect immediately: records waiting on your device are deleted and nothing more is sent, until you turn it back on.

## What stays on your device

The app stores only on your device:
- your reader profile (Kids / Adults) and language;
- your reading progress, gamebook state (current node, endings found) and any branches you make in the editor;
- the list of products you own (entitlements) and the purchase receipts from the store;
- downloaded story packs and a copy of the catalog;
- for the statistics: the day measuring began, a session counter, the on/off switch and records waiting to be sent.

Apart from the anonymous statistics described above, this data never leaves your device, and uninstalling the app deletes it. A gamebook branch you made leaves the device only if you send it yourself through the system share sheet, to a recipient you choose.

## Purchases

In-app purchases are processed by Apple (App Store) or Google (Google Play) under their own terms and privacy policies. We never see your name, payment card or email address. The app receives only a confirmation from the store that you own a product, and it stores that confirmation on your device.

## Content downloads

The app downloads the catalog, covers and story packs from GitHub Pages and GitHub Releases (GitHub, Inc.). Like any web host, GitHub receives your device's IP address and technical request data when content is downloaded, and handles them under its own policy: https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement. We do not receive this data and do not link it to you.

## Children

The app offers a Kids profile. Purchases and switching to the Adults profile are protected by a parental gate. We collect no personal data from children or from anyone else, and in the Kids profile no statistics are recorded at all.

## Your rights

Because we process no personal data about you, there is nothing for us to access, correct or delete: the anonymous statistics contain nothing that would let us find the records of a particular person. You can turn the statistics off at any time, and you fully control the data stored on your device. For questions, contact business@olin.now. You may also lodge a complaint with a data protection authority (in the Czech Republic: Úřad pro ochranu osobních údajů, https://www.uoou.cz).

## Changes

If this policy changes, we will publish the new version on this page with a new effective date.

## Contact

ol1n, business@olin.now
