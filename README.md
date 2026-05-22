# 🚀 SEO Page Title Optimizer

De AI Page Title Optimizer tool helpt marketing specialisten en website-eigenaren om in bulk paginatitels (meta titles) te optimaliseren op basis van daadwerkelijke prestatiedata uit Google Search Console (GSC) en de gescrapte pagina-inhoud.

## ✨ Functionaliteiten

* Slimme CSV-Invoer: Accepteert zowel door komma (,) als puntkomma (;) gescheiden CSV-bestanden (voorkomt de bekende Nederlandse Excel-exportfouten).
* Datagedreven Keyword Matching: Filtert automatisch de top-3 best presterende zoekwoorden (op basis van clicks) per URL uit de GSC-data en gebruikt dit als context voor de AI.
* Content-Aware Optimalisatie: Neemt de daadwerkelijke kerninhoud van de pagina mee (bijv. gescraped via Screaming Frog Custom Extraction) om titels te genereren die perfect aansluiten bij de zoekintentie.
* Rebranding Proof: Dwingt strikte merkidentiteit en opmaakregels af (zoals een vaste merknaam-suffix en specifieke hoofdletter-restricties).
* Hufterproof & Robuust: Bevat automatische header-validatie (ongevoelig voor hoofdletters in kolomnamen), een OpenAI retry-mechanisme bij API-haperingen og automatische opschoning van AI-ruis (zoals ongewenste markdown-sterretjes).
* Bliksemsnel: Maakt gebruik van parallelle verwerking (ThreadPoolExecutor) om honderden pagina's tegelijkertijd te analyseren.

## 📋 Vereisten & Data-indeling (Input)

Om de applicatie succesvol te draaien, dien je twee losse CSV-bestanden te uploaden. De volgorde van de kolommen maakt niet uit, en de app corrigeert eventuele hoofdletters in de headers automatisch.

### 1. Huidige Paginatitels CSV
Dit bestand bevat de pagina's die je wilt optimaliseren (bijvoorbeeld een export uit Screaming Frog).

| Vereiste Kolomnaam | Type | Beschrijving |
| :--- | :--- | :--- |
| `Address` | Tekst | De volledige URL van de pagina. |
| `Title 1` | Tekst | De huidige meta-titel van de pagina. |
| `H1-1` | Tekst | De huidige primaire H1-kop van de pagina. |
| `Page Content` | Tekst | De (gescrapte) kerninhoud of introductie van de pagina. |

Let op: zorg dat de exacte benamingen zoals hierboven vermeld terugkomen in het .csv bestand.

### 2. Google Search Console Data CSV
Dit bestand bevat de zoekwoordprestaties op paginaniveau (export uit GSC).

| Vereiste Kolomnaam | Type | Beschrijving |
| :--- | :--- | :--- |
| `Page` | Tekst | De URL van de pagina (moet matchen met de Paginatitels CSV). |
| `Query` | Tekst | De zoekterm waarop de pagina vertoond is. |
| `Clicks` | Getal | Het aantal clicks dat dit specifieke zoekwoord heeft gegenereerd. |

Let op: bovenstaande data kun je onder andere met behulp van de _search analytics for sheets_ extensie in Google Sheets ophalen. Gebruik hiervoor de volgende filtering: 
- Afgelopen 3 maanden
- Query + Landingpage
- Optioneel: country filter
