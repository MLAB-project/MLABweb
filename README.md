# MLABweb

MLAB home page with the interactive catalog of [MLAB modules](https://github.com/MLAB-modules).


## Použití 

Jednotlivé položky katalogu modulů jsou na webu zobrazovány na základě dvou předpokladů:
 - Modul je umístěn v GitHub organizaci [MLAB-modules](https://github.com/MLAB-modules)
 - Modul obsahuje yaml soubor s metadaty pro zobrazení na webu. Soubor se musí nacházet v `/doc/metadata.yaml`.

Při splnění těchto podmínek bude modul na webu automaticky zobrazen. Zobrazení nebo aktualizace dat může nějakou dobu trvat. Pokud se nic nestane do jedné hodiny od provedení úpravy, je potřeba analyzovat možné problémy popřípadě kontaktovat správce webu. 


### Automatická aktualizace dat
Pro minimalizaci množství kroků potřebných pro zobrazení modulu na webu se snažíme maximum procesů automatizovat. K tomu slouží GitHub actions workflow, které jsme si naprogramovaly pro tyto účely. Actions postupy typicky aktualizujeme způsobem, že v repozitáři modulu máme submodul [/doc/assets/](https://github.com/MLAB-project/documents), který obsahuje jednotlivá actions potřebná pro správné fungování repozitáře. 


### Metadata yaml

Zde je základní struktura yaml souboru.
Flag `<G:` značí, že hodnota je generovaná automaticky na základě github actions. Tato hodnota může být kdykoliv automaticky přepsána. 
Flag `<U:` značí, že je to uživatelsky zadávaná hodnoda. 

```
description: <G: Popis modulu, cca 250 znaků, generovaný z github popisu>
github_branch: <G: Výchozí větev na githubu>
github_branches: 
- <G: Seznam větví v repozitáři>
github_repo: <G: Název repozitáře>
github_url: <G: URL adresa k repozitáři>
homepage: <U: true/false, má být modul zobrazen na úvodní stránce webu? >
image_title: <U: Jaký obrázek má být zobrazen na přehledu modulů? >
images:
- <G: Seznam obrázků v repozitáři>
issues: <G: Počet otevřených issue>
mark: <U: Hodnocení kvality modulu, číslo 0-100)
mod_ibom: <G: Cesta k ibom souboru>
mod_scheme: <G: Cesta ke schématu>
tags:
- <G: Seznam tagů, generovánoz z github toppics>
title: <G: Název modulu - generováno z názvu repozitáře>
updated: <G: čas aktualizace>
```

#### Stav a kvalita modulů
Na webu je zelený proužek a filtr, kterým lze vybírat stav modulů:
![obrazek](https://github.com/MLAB-project/MLABweb/assets/5196729/8b603185-a976-4acb-b256-cd5631cbcdd0)

To je v yaml souboru parametr 'status', který může mít hodnotu 1-5, pokud není uvedena, tak se aplikuje 2.
Hodnota 4 (replaced) se automaticky nastaví ve webserveru v případě, že součástka má nastavený atribut [replaced](https://github.com/mlab-modules/USB232R01/blob/USB232R01B/doc/metadata.yaml#L24)

Pak existuje hodonota 'mark', což by taktéž mělo odrážet stav modulu ve smyslu jak moc má dobrou dokumentaci, jak moc je ten modul kompletní. Neexistuje ale nějaký popis toho, co odpovídá jakému číslu. Je to rozsah 0-100, tuším, že ty moduly s dobrou dokumentací mají hodnocení okolo 80-90 (já tam nechávám nějakou rezervu). Zde předpokládám, že tohle číslo bude způsobovat výchozí řazení na webu.

Další parametr je ```homepage: true/false```, což způsobí, že se to zobrazí na úvodní stránce, Tam mám odhad, že by nemělo být více než cca 12 modulů. 

### Kategorie
Na webu jsou zobrazeny předvybrané kategorie, které jsou provázány z github topics. Seznam kategorií, které jsou zobrazeny v horním menu je [zde](/src/MLABweb/categories.py). V souboru s metadaty to odpovídá položce `tags`. 
