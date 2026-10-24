---
title: Annexe technique
---

<a class="retour-dataviz" href="./">← Retour à la dataviz</a>

# Annexe technique


## Outils

Cette application de data visualisation a été développée avec [Observable Framework](https://observablehq.github.io/framework/) et l’assistance de [Claude Code](https://claude.com/fr/product/claude-code). Dans une phase préalable, l’exploration des données a été réalisée dans un [notebook Observable](https://observablehq.com/@observablehq/notebooks-user-guide) avec le soutien de [Claude](https://claude.com/fr/product/overview).

## Données

Conformément au [règlement du concours](https://www.datagrandest.fr/site/concours-de-datavisualisation-2026-informations-et-inscriptions/), seules les données mises à disposition dans le cadre du concours ont été utilisées pour créer cette application. Toutefois, compte tenu de leurs multiples dimensions (temps, site, cours d’eau…), elles ont fait l’objet de transformations significatives afin de pouvoir par exemple produire des valeurs à l’échelle des cours d’eau à partir de valeurs mesurées au niveau des sites.

En conséquence, les valeurs affichées sur les graphiques ne sont pas directement celles contenues dans les jeux de données mis à disposition. Afin de démontrer que le règlement du concours a été respecté, et dans un souci de transparence et de reproductibilité des transformations qui conduisent des données originales aux données affichées, cette annexe présente toutes les étapes de ces transformations. Le code qui permet de reproduire ces transformations a été publié dans un dépôt GitHub privé accessible sur demande. Il sera rendu public après la clôture du concours.

## Étape 0 : Téléchargement et vérification des fichiers d’origine

Toutes les données mises à disposition dans le cadre du concours se trouvent sur [cette page web](https://www.datagrandest.fr/datahub/dataset/a9557bbf-673a-4936-a01e-6f250554b33f). Au 24 octobre 2026, la page listait 5 fichiers de données et 2 fichiers PDF d’explication :
- `communes-grand-est.geojson`
- `departements-grand-est.geojson`
- `region-grand-est.geojson`
- `cours-eau-region_1791104972648.geojson`
- le fichier `donnees.zip` contenant lui-même 2 fichiers - `donnees.csv` et `donnees.xlsx`
- `Me_Lire.pdf`
- `Me_Lire_1791105003994.pdf`

Dans le salon Discord consacré au concours, les organisateurs ont précisé que les valeurs du champ `debit` du fichier `donnees` sont en réalité exprimées en l/s et non en m3/s comme inscrit dans `Me_Lire.pdf`.

Les fichiers de données suivants ont été utilisés pour créer l’application.

| Fichier | Rôle |
| --- | --- |
| `donnees.csv` | mesures hebdomadaires (débit, pluie, température…) par site |
| `cours-eau-region_1791104972648.geojson` | tracé des cours d’eau du Grand Est |
| `region-grand-est.geojson` | contour de la région (fond de carte) |
| `departements-grand-est.geojson` | contours des départements (fond de carte) |

Avant toute transformation, le script `preparation/00_verifier_empreintes.py` calcule l’empreinte SHA-256 de chaque fichier d’origine et la compare à celle notée dans `preparation/empreintes.sha256`. Si un fichier manque ou diffère, le script s’arrête avec un message d’erreur. Les transformations ne sont donc effectuées qu’à partir des fichiers dans leur état d’origine, c’est-à-dire tels que publiés sur [cette page web](https://www.datagrandest.fr/datahub/dataset/a9557bbf-673a-4936-a01e-6f250554b33f).

## Étape 1 : nettoyage de `donnees.csv`

Le script `preparation/01_nettoyer_donnees.py` effectue deux opérations :

1. **Abandon de la colonne `crue`**. Tous les sites de mesure couverts par `donnees.csv` sont utilisés pour la prévision des crues, et la colonne correspondante prend toujours la valeur `1`, donc elle n’apporte pas dinformation utile pour notre analyse. Nous la supprimons.
2. **Rajout du zéro initial pour les codes liés aux Ardennes** : les codes `dept` et `commune` liés aux Ardennes ont un chiffre en moins (`8` au lieu de `08` et par exemple `8090` au lieu de `08090`) car le zéro initial a probablement disparu quand ces codes ont été considérés comme des nombres. Nous le rajoutons.

Les valeurs de débit vides ou égales à -1 (erreur) ne sont pas modifiées à cette étape, et seront traitées au moment des calculs.

Un site de l’Aube est rattaché au libellé de département `AUBE,COTE-D'OR` (1 393 lignes). Ce libellé n’est pas modifié.

## Étape 2 : identification des cours d’eau à rattacher au bassin de la Moselle

Script : `preparation/02_bassin_moselle.py`. Journal : `preparation/journaux/02_bassin_moselle.txt`.

Le fichier des cours d’eau `cours-eau-region_1791104972648.geojson` contient 8 929 tracés, chacun avec un nom (`TopoOH`) et un identifiant unique (`CdOH`). Il ne dit ni quel cours d’eau se jette dans quel autre, ni dans quel sens l’eau s'écoule. Pour identifier les affluents de la Moselle, nous nous appuyons donc sur la géométrie : **un affluent se termine sur le tracé du cours d’eau qui le reçoit**.

1. Les tracés sont reprojetés en Lambert-93 (EPSG:2154 – système de coordonnées de référence officiel en France métropolitaine) pour mesurer les distances en mètres.
2. Pour chaque tracé, on calcule ses extrémités, une fois ses morceaux raccordés.
3. On note « A se termine sur B » quand une extrémité de A est à moins de 1 m du tracé de B. Le tracé est topologiquement propre : les extrémités tombent exactement sur l’autre tracé.
4. On part de la Moselle et de la Moselle canalisée, puis on **remonte** : on ajoute tout tracé qui se termine sur un tracé déjà retenu, et ainsi de suite. On ne fait que remonter : un tracé sur lequel se termine un cours d’eau du bassin n'est pas ajouté.
5. **Exclusions.** La Sarre et son bassin ne sont pas inclus car la Sarre se jette dans la Moselle en Allemagne, en aval du site de mesure le plus en aval sur la partie française de la Moselle. Les tracés dont le nom contient « canal » ou « rigole », appelés ici « ouvrages », ne sont pas traversés à ce stade parce qu’ils peuvent relier des bassins entre eux. En revanche, bien que les tracés font apparaître la Seille comme se terminant sur le « Bras Mort Aval de la Moselle », nous l’incluons avec son bassin car la Seille communique avec la Moselle.

6. **Ouvrages traversés.** Certains ruisseaux n’atteignent le bassin que par un ouvrage. Pour chaque ouvrage qui touche le bassin, on regarde les cours d’eau qu’il apporterait :
   - si **aucun** de ces cours d’eau ne se termine aussi sur un cours d’eau extérieur au bassin, l’ouvrage est traversé et ils sont ajoutés ;
   - sinon, l’ouvrage est refusé.

   On répète jusqu'à ce que plus rien ne change, car un ouvrage traversé peut en faire toucher un autre. Les ouvrages eux-mêmes ne font pas partie du résultat.

Sans traverser d’ouvrage, la remontée retient 1 533 tracés. Sur les 24 ouvrages examinés, 23 sont traversés et 6 d’entre eux apportent des cours d’eau :

| Ouvrage traversé | Cours d’eau apportés | Contact avec le bassin (longitude, latitude) |
| --- | --- | --- |
| Canal de Flottage des Salines | 17 | 6,589 ; 48,786 |
| Canal de l’Est (Branche Sud) | 7 | 6,100 ; 48,608 |
| Canal des Usines | 2 | 6,715 ; 48,187 |
| Canal de Morteau | 1 | 6,370 ; 48,577 |
| Rigole d’Alimentation du Bassin de Virement | 1 | 6,182 ; 48,578 |
| Rigole d’Alimentation du Reservoir de Bouzey | 1 | 6,357 ; 48,167 |

Un seul ouvrage est refusé : le « Canal de l’Est » (contact en 6,304 ; 48,172). Il apporterait 11 ruisseaux, mais l’un d'eux, le « Ruisseau des Sept Pêcheurs », se termine aussi sur « le Coney », qui n’est pas dans le bassin. Le détail de chaque ouvrage est dans le journal.

**Résultat : 1 562 tracés**, soit 1 444 noms distincts, Moselle et Moselle canalisée comprises.

**Contrôle.** On repère dans le tracé tous les « exutoires » hors bassin, c’est-à-dire les cours d’eau qui ne se terminent sur aucun autre : il y en a 599. Pour chacun, on remonte son bassin de la même façon. Aucun de ces bassins n’a de tracé en commun avec celui de la Moselle.

![Carte de contrôle du bassin de la Moselle](./annexe/02_bassin_moselle.png)

**Limites.**
- Le tracé est coupé aux limites du Grand Est. Un affluent qui rejoint la Moselle hors de la région n’est pas détecté.
- Le rattachement suppose que la confluence est dessinée dans le tracé. Un ruisseau qui ne touche aucun autre tracé reste isolé.

## Étape 3 : rapprochement des noms entre le CSV et le GeoJSON

Script : `preparation/03_rapprocher_noms.py`. Journal : `preparation/journaux/03_rapprocher_noms.txt`.

Les fichiers `donnees.csv` et `cours-eau-region_1791104972648.geojson` ne désignent pas les cours d’eau de la même façon. `donnees.csv` utilise un code (`code_cours_eau`) et un libellé (`libelle_cours_eau`), le GeoJSON un nom (`TopoOH`). On rattache donc **chaque site de mesure** à un tracé en combinant le nom et la position. On sait ensuite, grâce à l’étape 2, si le site est dans le bassin de la Moselle.

**Précision des positions.** Les coordonnées des sites sont arrondies à 2 décimales en latitude et à 3 en longitude. La vraie position peut donc être éloignée de la position arrondie d’un demi-pas d’arrondi dans chaque direction, soit 556 m vers le nord ou le sud et 36 m vers l’est ou l’ouest. Le **seuil** de distance accepté entre un site et son tracé en découle : **558 m**.

**Normalisation des noms.** On retire les accents, on met en minuscules, on remplace l’apostrophe typographique par l’apostrophe droite et on réduit les espaces multiples. Exemple : « La Moselle Canalisee » (CSV) et « la Moselle Canalisée » (GeoJSON) deviennent identiques.

**Règles, appliquées site par site :**

1. **Même nom** : parmi les tracés dont le nom normalisé est identique au libellé du cours d’eau, on prend le plus proche du site, s’il est sous le seuil de distance. 262 sites sont rattachés ainsi.
2. **Mot commun** : sinon, on prend le tracé le plus proche, sous le seuil de distance, dont le nom partage un mot distinctif avec le libellé du cours d’eau ou avec le nom écrit dans le libellé du site (la partie avant « à »). Les mots comme « ruisseau », « le », « la » ou « de » sont ignorés. 3 sites sont rattachés ainsi :

| Site | Libellé du cours d'eau | Tracé rattaché | Distance |
| --- | --- | --- | --- |
| La Béhine à Lapoutroie | La Bechine | la Béhine | 100 m |
| L'Eberbach à Leutenheim | Ruisseau l'Eberbach | Eberbach | 34 m |
| Le Veymerange à Thionville | Ruisseau le Veymerange | Ruisseau de Veymerange | 346 m |

3. Sinon, le site reste non rattaché. C'est le cas d'un seul site, « [Source de Flanrupt] à Bourbonne-les-Bains », qui n’a ni code de cours d’eau (`0`) ni libellé.

**Homonymes.** Plusieurs tracés peuvent porter le même nom. C'est la position qui départage. Par exemple, le site « L'Horn à Bousseviller » est rattaché au tracé « la Horn » situé à 271 m, qui n’est pas dans le bassin de la Moselle, et non à son homonyme qui s’y trouve. Un seul site a deux tracés de même nom sous le seuil (« La Marne à Joinville », à 4 m et à 68 m). Le plus proche est retenu, et ce site n’est pas dans le bassin de la Moselle.

**Contrôles.**
- Les coordonnées et libellés de chaque site sont identiques sur toutes ses lignes.
- Tous les sites d'un même code de cours d'eau sont soit tous dans le bassin, soit tous dehors.

**Résultat : 64 sites dans le bassin de la Moselle, sur 31 cours d'eau**, dont 11 sites sur la Moselle et 2 sur la Moselle canalisée. La liste complète est dans le journal.

## Étape 4 : filtrage des mesures

Script : `preparation/04_filtrer_mesures.py`.

On ne garde que les lignes de `donnees.csv` (nettoyé à l'étape 1) dont le site est dans le bassin de la Moselle (étape 3). Ces lignes sont réparties en trois fichiers, pour ne pas répéter à chaque semaine les informations qui ne changent pas. Ce sont les données de l’application, dans `src/data/` :

| Fichier | Une ligne par | Colonnes | Lignes |
| --- | --- | --- | --- |
| `sites.csv` | site | site, libelle_site, code_cours_eau, libelle_commune, commune, dept, libelle_dept, lat, lon, etiage, et le tracé rattaché à l'étape 3 (CdOH, TopoOH, distance_m) | 64 |
| `cours_eau.csv` | cours d'eau | code_cours_eau, uri_cours_eau, libelle_cours_eau | 31 |
| `mesures.csv` | site et semaine | semaine, site, temp, pluie, neige, debit, humidite, date | 89 152 |

Jointures : `mesures.site` → `sites.site`, puis `sites.code_cours_eau` → `cours_eau.code_cours_eau`. Les fichiers sont lus et écrits en texte : les valeurs restent exactement celles de l’étape 1, zéros initiaux compris.

**Contrôles.**
- Les colonnes de `sites.csv` sont constantes pour chaque site, et celles de `cours_eau.csv` pour chaque cours d’eau.
- Chaque site a exactement une ligne par semaine : 1 393 semaines, de 2000W01 à 2026W37, soit 64 × 1 393 = 89 152 lignes.
- **Jointure complète** : en recollant les trois fichiers écrits, on retrouve exactement les 89 152 lignes de l'étape 1 pour ces sites.

**À savoir pour les calculs.** Dans `mesures.csv`, 17 645 valeurs de `debit` sont vides (sites qui n’ont pas de mesures sur toute la période) et 74 valeurs valent 0. Ces débits nuls sont de vraies mesures (cours d’eau à sec, ou « assec ») : ils sont gardés dans toutes les analyses (voir l’étape 6 pour les calculs en logarithme). Ils concernent 4 sites, tous sur des affluents : aucun site de la Moselle n’a de débit nul. La valeur -1 (erreur) n’apparaît pas pour ces sites. Les autres paramètres observés (temp, pluie, neige, humidite) n’ont aucune valeur vide.

## Étape 5 : fond de carte

Script : `preparation/05_fonds_de_carte.py`. Journal : `preparation/journaux/05_fonds_de_carte.txt`.

**Cours d'eau.** Tous les tracés de la région sont gardés pour la carte. On ne conserve que quatre propriétés :

| Propriété | Contenu |
| --- | --- |
| `CdOH`, `TopoOH` | identifiant et nom du tracé |
| `categorie` | `moselle` (la Moselle et la Moselle canalisée), `bassin` (autre tracé du bassin, étape 2) ou `hors_bassin` |
| `mesure` | 1 si au moins un site de mesure de la région est rattaché au tracé (étape 3), sinon 0 |

Pour réduire les temps de chargement, les dessins des tracés sont simplifiés avec l’outil [**mapshaper**](https://github.com/mbloch/mapshaper). La version utilisée (0.7.95) et les paramètres de la simplification sont indiqués dans `package.json` :

- `-simplify 10% keep-shapes` : on garde 10 % des sommets qui peuvent être supprimés, sans faire disparaître de tracé ;
- `precision=0.0001` : les coordonnées sont arrondies à 0,0001°, soit environ 10 m ;
- `-filter remove-empty`, dans un second passage : on retire les objets devenus vides avec l’arrondi. C'est le cas d’un seul tracé, « Ruisseau de Rebais », qui n’a que 2 sommets distants de 0,00001°.

**Regroupement des tracés sans site de mesure.** Ces tracés ne servent que de fond. Après la simplification, on les regroupe en un seul objet (`MultiLineString`) par catégorie, sans identifiant ni nom. Les 123 tracés qui ont au moins un site de mesure restent séparés, avec leur identifiant et leur nom, pour pouvoir les désigner un par un si besoin. Le regroupement ne change aucune coordonnée : le script vérifie que les lignes et le nombre de sommets sont identiques avant et après.

**Région et départements.** Ils ne sont pas simplifiés : leurs coordonnées sont seulement arrondies de la même façon. Avec l’option `gj2008`, mapshaper garde le sens des contours des fichiers d'origine (contour extérieur dans le sens des aiguilles d’une montre), qui est celui qu’attend la bibliothèque d3. Sans cette option, mapshaper suit la norme GeoJSON RFC 7946 (sens inverse), et d3 dessinerait le reste du globe au lieu de la région.

**Résultat** (dans `src/data/`) :

| Fichier | Contenu | Taille |
| --- | --- | --- |
| `traces_cours_eau.geojson` | 8 928 tracés : 2 Moselle, 1 560 bassin, 7 366 hors bassin. 2 regroupements (tracés sans mesure) et 123 tracés avec mesure | 4,2 Mo |
| `region.geojson` | contour de la région | 0,09 Mo |
| `departements.geojson` | 10 départements | 0,31 Mo |

123 tracés ont au moins un site de mesure, dont 31 dans le bassin de la Moselle.

**Contrôles.** Le script vérifie la version de mapshaper. Il vérifie aussi que tous les tracés du bassin et tous les tracés rattachés à un site sont présents après simplification.

![Carte de contrôle du fond de carte](./annexe/05_fond_de_carte.png)

## Étape 6 : profil le long de la Moselle

Script : `preparation/06_profil_moselle.py`. Journal : `preparation/journaux/06_profil_moselle.txt`. Contrôle : `preparation/06b_verifier_indice.py`.

À travers cette étape, nous cherchons à situer les sites de mesure sur la Moselle et à calculer la distance qui les sépare, de façon à pouvoir afficher cette distance quand nous montrons les valeurs des mesures de débit aux différents sites.

**Distance de chaque site le long de la Moselle.**
- Le tracé « la Moselle » est formé de 4 morceaux, avec une petite fourche. On en fait un graphe : les sommets sont les bouts des morceaux, les arêtes les morceaux, pondérées par leur longueur. On garde le plus long des plus courts chemins entre deux bouts libres, soit **314,3 km** dans la région.
- Les sites de la Moselle et de la Moselle canalisée sont projetés sur ce chemin. Ils en sont tous à moins de 420 m, sous le seuil de l'étape 3. Les deux sites de la Moselle canalisée en sont à 0 et 27 m : on mesure donc tout le long du même tracé.
- La distance d'un site est la longueur du chemin entre l'extrémité amont et son point projeté. Elle est mesurée depuis l'extrémité amont **du tracé dans la région**.
- **Sens d'écoulement.** Le fichier ne dit pas de quel côté est l'amont. On le déduit des débits, puisque le débit médian augmente vers l'aval. La corrélation de rang (Spearman) entre la distance depuis la première extrémité et le débit médian vaut **-0,993**. L'amont est donc l'autre extrémité (6,892 ; 47,890), et l'aval est en (6,367 ; 49,467).
- Le site « La Moselle à Metz [Pont des Morts] » n'a **aucun débit valide** sur toute la période : il est écarté. Le profil compte **12 sites**, de 12,1 à 283,0 km.

**Sites retenus pour les calculs.** Un débit est **valide** s'il est renseigné et positif ou nul. Un débit nul est une vraie mesure (cours d'eau à sec, « assec ») et il est gardé dans toutes les analyses ; seuls les débits vides et le code d'erreur -1 sont écartés. Pour que les semaines extrêmes et le débit médian reposent sur des séries comparables, seuls les sites qui ont une série presque complète servent aux calculs. Un site est retenu s'il remplit les trois critères suivants :
1. son premier débit valide date au plus tard de la semaine 2001W01, c'est-à-dire de la première année du jeu de données ;
2. il a un débit valide la dernière semaine du jeu de données (2026W37, 7 septembre 2026), donc pas d'interruption avant la fin ;
3. au moins **97 %** des 1 393 semaines ont un débit valide.

| Site | 1ʳᵉ semaine valide | Dernière | Semaines valides | Retenu |
| --- | --- | --- | --- | --- |
| Fresse-sur-Moselle | 2000W01 | 2026W37 | 100 % | oui |
| Rupt-sur-Moselle | 2000W01 | 2026W37 | 98,1 % | oui |
| Remiremont et Saint-Nabord | 2000W01 | 2026W37 | 99,5 % | oui |
| Épinal | 2000W01 | 2026W37 | 100 % | oui |
| Châtel-sur-Moselle | 2014W42 | 2026W37 | 44,7 % | non |
| Saint-Mard, Tonnoy et Velle-sur-Moselle | 2001W01 | 2026W27 | 95,3 % | non |
| Pont-Saint-Vincent | 2000W01 | 2026W37 | 99,8 % | oui |
| Toul | 2000W01 | 2026W37 | 99,6 % | oui |
| Custines | 2000W01 | 2026W37 | 100 % | oui |
| Corny-sur-Moselle | 2014W17 | 2026W37 | 46,3 % | non |
| Hagondange et Hauconcourt | 2012W48 | 2026W37 | 51,7 % | non |
| Uckange | 2000W01 | 2026W37 | 100 % | oui |

**8 sites sont retenus.** Aucun site n'a une part de semaines valides comprise entre 95,3 % et 98,1 %. Le seuil exact, autour de 97 %, ne change donc pas le résultat.

**Comparaison entre semaines.** Comparer les semaines et identifier les extrêmes à l’échelle d’un cours d’eau suppose de disposer d’une méthode d’agrégation des mesures au niveau des sites correspondant à ce cours d’eau. Pour chaque semaine, on calcule la moyenne géométrique, sur les sites retenus mesurés cette semaine-là, de (débit / débit médian du site). 1 = débit habituel aux sites, 2 = deux fois plus, 0,5 = deux fois moins.
Le débit médian d'un site est la médiane de ses débits valides, zéros compris.

**Débits nuls et logarithme.** La moyenne géométrique se calcule avec le logarithme, qui n'existe pas pour 0. Pour ce calcul uniquement, un débit nul (ou un débit médian nul) est remplacé par un **plancher propre au site** : la moitié de son plus petit débit strictement positif. Chaque remplacement est signalé : le nombre de débits nuls et le plancher de chaque site figurent dans `profil_sites.csv`, et le nombre de remplacements de chaque semaine dans `profil_semaines.csv`. Pour la Moselle, il n'y a aucun débit nul : aucun remplacement n'est fait, et les résultats sont les mêmes qu'en écartant les zéros. La règle a été testée en mettant temporairement deux débits d'Épinal à 0 : le site reste valide à 100 %, les deux semaines sont signalées, et le contrôle numpy retrouve le même indice.

- **Semaine du maximum : 1ᵉʳ janvier 2018** (indice 11,8). **Semaine du minimum : 10 août 2026** (indice 0,083).

**Contrôle.** Le script `06b_verifier_indice.py` refait le calcul autrement, avec numpy, sous forme de tableau semaines × sites retenus. Il recalcule lui-même le plancher de chaque site, et retrouve le même nombre de sites et de remplacements pour chaque semaine, le même indice à 5·10⁻⁷ près (arrondi du fichier à 6 décimales) et les mêmes semaines extrêmes.

**Fichiers produits** (dans `src/data/`) :
- `profil_sites.csv` : site, libellé, distance, débit médian, nombre de débits valides, nombre de débits nuls, plancher pour le logarithme, première et dernière semaines valides, part de semaines valides, site retenu ou non pour les calculs, écart au tracé ;
- `profil_semaines.csv` : semaine, date, nombre de sites mesurés, indice, semaine classée ou non, nombre de débits nuls remplacés par le plancher.

## Étape 7 : température, pluie et neige

Script : `preparation/07_meteo_moselle.py`. Journal : `preparation/journaux/07_meteo_moselle.txt`.

Les deux graphiques météo portent sur les **12 sites du profil des débits** (étape 6). Les trois mesures utilisées sont :
- `temp` : température moyenne hebdomadaire (°C) ;
- `pluie` : hauteur de pluie, cumul hebdomadaire (mm) ;
- `neige` : équivalent en eau des précipitations solides (neige, grêle), cumul hebdomadaire (mm).

La pluie et la neige ont donc la même unité, mais elles ne sont jamais additionnées.

**Valeurs vides.** Le script s'arrête si l'une de ces trois mesures manque pour l'un des 12 sites : la moyenne ne porterait alors pas sur les mêmes sites chaque semaine. Il n'y en a aucune : les 1 393 semaines ont les 12 sites.

**Moyenne hebdomadaire.** Pour chaque semaine, on calcule la moyenne des 12 sites pour chaque mesure.

**Référence pour repérer les écarts.** Pour chaque semaine de l'année (numéro de semaine ISO), on calcule la moyenne des valeurs hebdomadaires de cette semaine sur toutes les années du jeu de données (2000 à 2026), soit 26 ou 27 années selon la semaine. La semaine 53, qui n'existe que certaines années (2004, 2009, 2015 et 2020), est regroupée avec la semaine 52, qui compte ainsi 30 valeurs.

**Contrôle.** Chaque référence, calculée comme la moyenne des moyennes hebdomadaires, est égale à la moyenne directe de toutes les mesures (sites × années) de la même semaine de l'année. C'est possible parce que chaque semaine compte les 12 sites.

**Fichier produit** : `src/data/meteo_semaines.csv`, avec une ligne par semaine : semaine, date, semaine de l'année, moyennes des 12 sites (temp, pluie, neige) et références (temp_ref, pluie_ref, neige_ref).

## La carte

Code : `src/components/carte.js`.

La carte est dessinée en SVG avec la bibliothèque d3, à partir des fichiers de l'étape 5 et de `sites.csv`.

- **Projection** : conique conforme de Lambert, avec les parallèles 44° et 49° et le méridien 3° E.
- **Cadrage** : au départ, la carte est ajustée au bassin de la Moselle (la Moselle et les tracés du bassin, étape 2). On peut dézoomer jusqu'à voir toute la région, à la molette ou avec le bouton « Voir toute la région ».
- **Couleur de la Moselle** : le même bleu sombre (`#0b4f71`) que la courbe de la semaine choisie sur le graphique des débits.

## Le profil des débits

Code : `src/components/profil.js`.

Le graphique montre le débit à chaque site de la Moselle, d'amont en aval, avec la distance en abscisse. **Chaque courbe correspond à une même semaine.** Un site sans mesure cette semaine-là n'a pas de point. Une courbe de semaine (semaine choisie, semaine du maximum, semaine du minimum) montre **tous les débits disponibles** cette semaine-là. Les **calculs**, eux, ne tiennent compte que des 8 sites retenus : l'indice, le classement, le choix des semaines extrêmes et la courbe du débit médian.

| Courbe | Couleur |
| --- | --- |
| semaine choisie avec la barre placée sous la carte (au chargement, la plus ancienne) | `#0b4f71`, trait épais |
| semaine du débit le plus élevé (1ᵉʳ janvier 2018) | `#c77700` |
| semaine du débit le plus faible (10 août 2026) | `#7b6bb0` |
| débit médian de chaque site retenu, toutes semaines confondues (« Débit médian du site* » dans la légende ; l'astérisque renvoie aux sites retenus, voir l'étape 6) | gris, en tirets |

- **Échelle** logarithmique par défaut, avec des graduations 1-3-10, ou linéaire. Les bornes de l'axe sont fixes, quelle que soit la semaine. Un débit nul ne peut pas être placé sur une échelle logarithmique : il y est dessiné au plancher du site (voir l'étape 6), avec un **point creux** pour le signaler. En échelle linéaire, il est placé à 0. Aucun débit nul n'apparaît sur la Moselle.
- **Lignes verticales** : une par site de mesure, à sa distance depuis l'amont. Elles sont pleines pour les 8 sites retenus pour les calculs et en pointillés pour les 4 autres, dont la série est incomplète. Au passage de la souris, la ligne se renforce et le site correspondant est mis en évidence **sur la carte**, comme si la souris passait sur son cercle : le cercle grossit et le nom du site s'affiche. Quand la souris quitte le graphique, la mise en évidence disparaît.
- L'indice des semaines sert à choisir les semaines extrêmes ; il n'est pas affiché.

**Le film.** Au chargement, la page affiche la semaine la plus ancienne (3 janvier 2000), sans les courbes des semaines extrêmes. Le film est d'abord **guidé** :
- le bouton « Lancer le film » fait défiler les semaines **à vitesse variable** : 25 ms par semaine en croisière, puis un ralentissement progressif sur les 20 semaines qui précèdent chaque arrêt, jusqu'à 150 ms par semaine. Le film complet dure ainsi environ **37 s**, sans compter les arrêts (24 s jusqu'au maximum, 12 s jusqu'au minimum, 1 s jusqu'à la fin) ;
- le film s'arrête à la semaine du maximum : la courbe du maximum apparaît et un texte commente cette semaine, avec un bouton pour reprendre le film ;
- il s'arrête de même à la semaine du minimum, puis à la dernière semaine, où s'affiche le texte final ;
- pendant cette phase, le curseur de semaine est bloqué ; seul un bouton lecture / pause est disponible. Un lien « Passer le film » mène directement à la fin.

Une fois le film terminé, la barre de semaine devient **libre** (60 ms par semaine) :
- ▶ lance le défilement vers les semaines suivantes, ◀ vers les précédentes. Le bouton du sens en cours affiche ⏸ : un nouveau clic met en pause, et un clic sur l'autre flèche inverse le sens.
- Déplacer le curseur à la main met le film en pause.
- Le lien « Revoir le film » relance le film guidé depuis le début.
- Les débits affichés viennent directement de `mesures.csv`, et l'indice de `profil_semaines.csv`.

<a class="retour-dataviz" href="./">← Retour à la dataviz</a>

## Les graphiques météo

Code : `src/components/meteo.js`.

Deux graphiques, l'un au-dessus de l'autre : la température, puis la pluie et la neige. Ils montrent une **fenêtre de 5 semaines** qui se termine par la semaine affichée dans le graphique des débits.

- **Fenêtre glissante** : l'axe horizontal a 5 positions fixes, de « −4 sem. » à « sem. affichée ». Au fil des semaines, les points glissent vers la gauche et disparaissent au bout de 5 semaines. Au début de la série, il n'y a pas de semaines précédentes : on ne voit qu'un point, à droite, puis deux, et ainsi de suite.
- **Ligne pleine** : moyenne des 12 sites pour chaque semaine. **Ligne en tirets** : la référence 2000-2026 des mêmes semaines de l'année (étape 7). L'écart entre les deux lignes montre si la semaine est plus chaude, plus froide, plus arrosée ou plus sèche que d'habitude.
- Les **axes sont fixes**, calculés sur toute la période, pour que l'échelle ne bouge pas pendant le film.

