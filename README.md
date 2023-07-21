# MLABweb

MLAB home page with catalogue of [MLAB modules](https://github.com/MLAB-modules).


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


### Kategorie
Na webu jsou zobrazeny předvybrané kategorie, které jsou provázány z github topics. Seznam kategorií, které jsou zobrazeny v horním menu je [zde](/src/MLABweb/categories.py). V souboru s metadaty to odpovídá položce `tags`. 
