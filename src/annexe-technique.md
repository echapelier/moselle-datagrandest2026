---
title: Annexe technique
---

# Annexe technique

Toutes les étapes s'appuient uniquement sur les fichiers d'origine listés ci-dessous. Les données sont transformées par calcul, sans recours à une autre source.

## Sources des données

<!-- À compléter : liens vers la source, date de téléchargement, version. -->

## Étape 0 : vérification des fichiers d'origine

Avant toute préparation, le script `preparation/00_verifier_empreintes.py` calcule l'empreinte SHA-256 de chaque fichier d'origine et la compare à celle notée dans `preparation/empreintes.sha256`. Si un fichier manque ou diffère, le script s'arrête avec un message d'erreur : la suite de la préparation n'est donc faite qu'à partir des fichiers de référence.

| Fichier | Rôle |
| --- | --- |
| `donnees.csv` | mesures hebdomadaires (débit, pluie, température…) par site |
| `cours-eau-region_1791104972648.geojson` | tracé des cours d'eau du Grand Est |
| `region-grand-est.geojson` | contour de la région (fond de carte) |
| `departements-grand-est.geojson` | contours des départements (fond de carte) |

## Étape 1 : nettoyage de `donnees.csv`

Script : `preparation/01_nettoyer_donnees.py`. Le fichier est lu et écrit en texte, sans conversion automatique des types : les autres valeurs restent exactement celles d'origine. Deux corrections seulement :

1. **Abandon de la colonne `crue`** : elle vaut 1 sur les 370 538 lignes et n'apporte donc aucune information. Le script vérifie cette constance et s'arrête sinon.
2. **Zéro initial des Ardennes** : pour les 30 646 lignes du département des Ardennes (seul département concerné), le code `dept` vaut `8` au lieu de `08` et le code `commune` n'a que 4 chiffres (par exemple `8090` au lieu de `08090`). Le zéro est rétabli. Le script vérifie la forme attendue avant de corriger, puis que tous les codes ont ensuite leur longueur normale (2 caractères pour `dept`, 5 pour `commune`).

Les valeurs de débit nulles ou égales à -1 (code d'erreur) ne sont pas modifiées à cette étape : elles sont traitées au moment des calculs.

Contrôle : comparaison valeur par valeur du fichier produit avec l'original. Les seules différences sont l'absence de la colonne `crue` et le zéro ajouté aux codes des Ardennes ; l'écart de taille entre les deux fichiers (679 789 octets) correspond exactement à ces changements.

Remarque : un site de l'Aube est rattaché au libellé de département `AUBE,COTE-D'OR` (1 393 lignes). Ce libellé n'est pas modifié.

## Étape 2 : bassin de la Moselle

Script : `preparation/02_bassin_moselle.py`. Journal : `preparation/journaux/02_bassin_moselle.txt`.

Le fichier des cours d'eau contient 8 929 tracés, chacun avec un nom (`TopoOH`) et un identifiant unique (`CdOH`). Il ne dit ni quel cours d'eau se jette dans quel autre, ni dans quel sens l'eau s'écoule. On s'appuie donc sur la géométrie : **un affluent se termine sur le tracé du cours d'eau qui le reçoit**.

1. Les tracés sont reprojetés en Lambert-93 (EPSG:2154) pour mesurer les distances en mètres.
2. Pour chaque tracé, on calcule ses extrémités, une fois ses morceaux raccordés.
3. On note « A se termine sur B » quand une extrémité de A est à moins de 1 m du tracé de B. Le tracé est topologiquement propre : les extrémités tombent exactement sur l'autre tracé.
4. On part de la Moselle et de la Moselle canalisée, puis on **remonte** : on ajoute tout tracé qui se termine sur un tracé déjà retenu, et ainsi de suite. On ne fait que remonter : un tracé sur lequel se termine un cours d'eau du bassin n'est pas ajouté.
5. **Exclusions.** La Sarre est exclue (choix du projet), et avec elle tout son sous-bassin, qui n'est atteint que par elle. Les tracés dont le nom contient « canal » ou « rigole », appelés ici « ouvrages », ne sont pas traversés à ce stade, parce qu'ils peuvent relier des bassins entre eux. Les **bras sont gardés** : dans le tracé, la Seille se termine sur le « Bras Mort Aval de la Moselle ». Exclure les bras ferait perdre tout le sous-bassin de la Seille (224 tracés).
6. **Ouvrages traversés.** Certains ruisseaux n'atteignent le bassin que par un ouvrage. Pour chaque ouvrage qui touche le bassin, on regarde les cours d'eau qu'il apporterait :
   - si **aucun** de ces cours d'eau ne se termine aussi sur un cours d'eau extérieur au bassin, l'ouvrage est traversé et ils sont ajoutés ;
   - sinon, l'ouvrage est refusé.

   On répète jusqu'à ce que plus rien ne change, car un ouvrage traversé peut en faire toucher un autre. Les ouvrages eux-mêmes ne font pas partie du résultat.

Sans traverser d'ouvrage, la remontée retient 1 533 tracés. Sur les 24 ouvrages examinés, 23 sont traversés et 6 d'entre eux apportent des cours d'eau :

| Ouvrage traversé | Cours d'eau apportés | Contact avec le bassin (longitude, latitude) |
| --- | --- | --- |
| Canal de Flottage des Salines | 17 | 6,589 ; 48,786 |
| Canal de l'Est (Branche Sud) | 7 | 6,100 ; 48,608 |
| Canal des Usines | 2 | 6,715 ; 48,187 |
| Canal de Morteau | 1 | 6,370 ; 48,577 |
| Rigole d'Alimentation du Bassin de Virement | 1 | 6,182 ; 48,578 |
| Rigole d'Alimentation du Reservoir de Bouzey | 1 | 6,357 ; 48,167 |

Un seul ouvrage est refusé : le « Canal de l'Est » (contact en 6,304 ; 48,172). Il apporterait 11 ruisseaux, mais l'un d'eux, le « Ruisseau des Sept Pêcheurs », se termine aussi sur « le Coney », qui n'est pas dans le bassin. Le détail de chaque ouvrage est dans le journal.

**Résultat : 1 562 tracés**, soit 1 444 noms distincts, Moselle et Moselle canalisée comprises.

**Contrôle.** On repère dans le tracé tous les « exutoires » hors bassin, c'est-à-dire les cours d'eau qui ne se terminent sur aucun autre : il y en a 599. Pour chacun, on remonte son bassin de la même façon. Aucun de ces bassins n'a de tracé en commun avec celui de la Moselle.

![Carte de contrôle du bassin de la Moselle](./annexe/02_bassin_moselle.png)

**Limites.**
- Le tracé est coupé aux limites du Grand Est. Un affluent qui rejoint la Moselle hors de la région n'est pas détecté.
- Le rattachement suppose que la confluence est dessinée dans le tracé. Un ruisseau qui ne touche aucun autre tracé reste isolé.

## Étape 3 : rapprochement des noms entre le CSV et le GeoJSON

Script : `preparation/03_rapprocher_noms.py`. Journal : `preparation/journaux/03_rapprocher_noms.txt`.

Les deux fichiers ne désignent pas les cours d'eau de la même façon. `donnees.csv` utilise un code (`code_cours_eau`) et un libellé (`libelle_cours_eau`), le GeoJSON un nom (`TopoOH`). On rattache donc **chaque site de mesure** à un tracé en combinant le nom et la position. On sait ensuite, grâce à l'étape 2, si le site est dans le bassin de la Moselle.

**Précision des positions.** Les coordonnées des sites sont arrondies à 2 décimales en latitude et à 3 en longitude. La vraie position peut donc être éloignée de la position arrondie d'un demi-pas d'arrondi dans chaque direction, soit 556 m vers le nord ou le sud et 36 m vers l’est ou l’ouest. Le **seuil** de distance accepté entre un site et son tracé en découle : **558 m**.

**Normalisation des noms.** On retire les accents, on met en minuscules, on remplace l'apostrophe typographique par l'apostrophe droite et on réduit les espaces multiples. Exemple : « La Moselle Canalisee » (CSV) et « la Moselle Canalisée » (GeoJSON) deviennent identiques.

**Règles, appliquées site par site :**

1. **Même nom** : parmi les tracés dont le nom normalisé est égal au libellé du cours d'eau, on prend le plus proche du site, s'il est à moins du seuil. 262 sites sont rattachés ainsi.
2. **Mot commun** : sinon, on prend le tracé le plus proche, à moins du seuil, dont le nom partage un mot distinctif avec le libellé du cours d'eau ou avec le nom écrit dans le libellé du site (la partie avant « à »). Les mots comme « ruisseau », « le », « la » ou « de » sont ignorés. 3 sites sont rattachés ainsi :

| Site | Libellé du cours d'eau | Tracé rattaché | Distance |
| --- | --- | --- | --- |
| La Béhine à Lapoutroie | La Bechine | la Béhine | 100 m |
| L'Eberbach à Leutenheim | Ruisseau l'Eberbach | Eberbach | 34 m |
| Le Veymerange à Thionville | Ruisseau le Veymerange | Ruisseau de Veymerange | 346 m |

3. Sinon, le site reste non rattaché. C'est le cas d'un seul site, « [Source de Flanrupt] à Bourbonne-les-Bains », qui n'a ni code de cours d'eau (`0`) ni libellé.

Pour les sites rattachés, la distance au tracé est de 135 m en médiane et de 538 m au maximum. Elle reste sous le seuil.

**Homonymes.** Plusieurs tracés peuvent porter le même nom. C'est la position qui départage. Par exemple, le site « L'Horn à Bousseviller » est rattaché au tracé « la Horn » situé à 271 m, qui n'est pas dans le bassin de la Moselle, et non à son homonyme qui s'y trouve. Un seul site a deux tracés de même nom à moins du seuil (« La Marne à Joinville », à 4 m et à 68 m). Le plus proche est retenu, et ce site est hors du bassin.

**Contrôles.**
- Les coordonnées et libellés de chaque site sont identiques sur toutes ses lignes.
- Tous les sites d'un même code de cours d'eau sont soit tous dans le bassin, soit tous dehors.

**Résultat : 64 sites dans le bassin de la Moselle, sur 31 cours d'eau**, dont 11 sites sur la Moselle et 2 sur la Moselle canalisée. La liste complète est dans le journal.

## Étape 4 : filtrage des mesures

Script : `preparation/04_filtrer_mesures.py`.

On ne garde que les lignes de `donnees.csv` (nettoyé à l'étape 1) dont le site est dans le bassin de la Moselle (étape 3). Ces lignes sont réparties en trois fichiers, pour ne pas répéter à chaque semaine les informations qui ne changent pas. Ce sont les données de l'application, dans `src/data/` :

| Fichier | Une ligne par | Colonnes | Lignes |
| --- | --- | --- | --- |
| `sites.csv` | site | site, libelle_site, code_cours_eau, libelle_commune, commune, dept, libelle_dept, lat, lon, etiage, et le tracé rattaché à l'étape 3 (CdOH, TopoOH, distance_m) | 64 |
| `cours_eau.csv` | cours d'eau | code_cours_eau, uri_cours_eau, libelle_cours_eau | 31 |
| `mesures.csv` | site et semaine | semaine, site, temp, pluie, neige, debit, humidite, date | 89 152 |

Jointures : `mesures.site` → `sites.site`, puis `sites.code_cours_eau` → `cours_eau.code_cours_eau`. Les fichiers sont lus et écrits en texte : les valeurs restent exactement celles de l'étape 1, zéros initiaux compris.

**Contrôles.**
- Les colonnes de `sites.csv` sont constantes pour chaque site, et celles de `cours_eau.csv` pour chaque cours d'eau.
- Chaque site a exactement une ligne par semaine : 1 393 semaines, de 2000W01 à 2026W37, soit 64 × 1 393 = 89 152 lignes.
- **Jointure complète** : en recollant les trois fichiers écrits, on retrouve exactement les 89 152 lignes de l'étape 1 pour ces sites.

**À savoir pour les calculs.** Dans `mesures.csv`, 17 645 valeurs de `debit` sont vides (sites qui ne mesurent pas sur toute la période) et 74 valeurs valent 0. La valeur -1 (code d'erreur) n'apparaît pas pour ces sites. Les autres mesures (temp, pluie, neige, humidite) n'ont aucune valeur vide.

## Étape 5 : fonds de carte

Script : `preparation/05_fonds_de_carte.py`. Journal : `preparation/journaux/05_fonds_de_carte.txt`.

**Cours d'eau.** Tous les tracés de la région sont gardés pour la carte. On ne conserve que quatre propriétés :

| Propriété | Contenu |
| --- | --- |
| `CdOH`, `TopoOH` | identifiant et nom du tracé |
| `categorie` | `moselle` (la Moselle et la Moselle canalisée), `bassin` (autre tracé du bassin, étape 2) ou `hors_bassin` |
| `mesure` | 1 si au moins un site de mesure de la région est rattaché au tracé (étape 3), sinon 0 |

Les tracés sont ensuite simplifiés avec **mapshaper 0.7.95**, dont la version est figée dans `package.json` :

- `-simplify 10% keep-shapes` : on garde 10 % des sommets qui peuvent être supprimés, sans faire disparaître de tracé ;
- `precision=0.0001` : les coordonnées sont arrondies à 0,0001°, soit environ 10 m ;
- `-filter remove-empty`, dans un second passage : on retire les objets devenus vides avec l'arrondi. C'est le cas d'un seul tracé, « Ruisseau de Rebais », qui n'a que 2 sommets distants de 0,00001°.

**Région et départements.** Ils ne sont pas simplifiés : leurs coordonnées sont seulement arrondies de la même façon. Avec l'option `gj2008`, mapshaper garde le sens des contours des fichiers d'origine (contour extérieur dans le sens des aiguilles d'une montre), qui est celui qu'attend la bibliothèque d3. Sans cette option, mapshaper suit la norme GeoJSON RFC 7946 (sens inverse), et d3 dessinerait le reste du globe au lieu de la région.

**Résultat** (dans `src/data/`) :

| Fichier | Contenu | Taille |
| --- | --- | --- |
| `traces_cours_eau.geojson` | 8 928 tracés : 2 Moselle, 1 560 bassin, 7 366 hors bassin. 250 163 sommets au lieu de 2 217 086 | 5,8 Mo (98 Mo à l'origine) |
| `region.geojson` | contour de la région | 0,09 Mo |
| `departements.geojson` | 10 départements | 0,31 Mo |

123 tracés ont au moins un site de mesure, dont 31 dans le bassin de la Moselle.

**Contrôles.** Le script vérifie la version de mapshaper. Il vérifie aussi que tous les tracés du bassin et tous les tracés rattachés à un site sont présents après simplification.

![Carte de contrôle du fond de carte](./annexe/05_fond_de_carte.png)

## Étape 6 : profil le long de la Moselle

Script : `preparation/06_profil_moselle.py`. Journal : `preparation/journaux/06_profil_moselle.txt`. Contrôle : `preparation/06b_verifier_indice.py`.

**Distance de chaque site le long de la Moselle.**
- Le tracé « la Moselle » est formé de 4 morceaux, avec une petite fourche. On en fait un graphe : les sommets sont les bouts des morceaux, les arêtes les morceaux, pondérées par leur longueur. On garde le plus long des plus courts chemins entre deux bouts libres, soit **314,3 km** dans la région.
- Les sites de la Moselle et de la Moselle canalisée sont projetés sur ce chemin. Ils en sont tous à moins de 420 m, sous le seuil de l'étape 3. Les deux sites de la Moselle canalisée en sont à 0 et 27 m : on mesure donc tout le long du même tracé.
- La distance d'un site est la longueur du chemin entre l'extrémité amont et son point projeté. Elle est mesurée depuis l'extrémité amont **du tracé dans la région**.
- **Sens d'écoulement.** Le fichier ne dit pas de quel côté est l'amont. On le déduit des débits, puisque le débit médian augmente vers l'aval. La corrélation de rang (Spearman) entre la distance depuis la première extrémité et le débit médian vaut **-0,993**. L'amont est donc l'autre extrémité (6,892 ; 47,890), et l'aval est en (6,367 ; 49,467).
- Le site « La Moselle à Metz [Pont des Morts] » n'a **aucun débit valide** sur toute la période : il est écarté. Le profil compte **12 sites**, de 12,1 à 283,0 km.

**Indice des semaines.** On reprend la méthode des essais faits dans le notebook :
- Seuls les débits strictement positifs sont pris en compte : les débits vides et les 0 sont écartés.
- Le débit médian d'un site est la médiane de ses débits valides.
- L'**indice** d'une semaine est la moyenne géométrique, sur les sites mesurés cette semaine-là, de (débit / débit médian du site). 1 = débit habituel aux sites, 2 = deux fois plus, 0,5 = deux fois moins.
- Les **semaines classées** sont celles où les 12 sites ont un débit valide : il y en a 605. Comme ce nombre dépasse 20, la règle qui tolère des sites manquants n'est pas utilisée.
- **Semaine du maximum : 1ᵉʳ janvier 2018** (indice 11,3). **Semaine du minimum : 8 août 2022** (indice 0,10).

**Contrôle.** Le script `06b_verifier_indice.py` refait le calcul autrement, avec numpy, sous forme de tableau semaines × sites. Il retrouve le même nombre de sites pour chaque semaine, le même indice à 5·10⁻⁷ près (arrondi du fichier à 6 décimales) et les mêmes semaines extrêmes.

**Fichiers produits** (dans `src/data/`) :
- `profil_sites.csv` : site, libellé, distance, débit médian, nombre de débits valides, écart au tracé ;
- `profil_semaines.csv` : semaine, date, nombre de sites mesurés, indice, semaine classée ou non.

## La carte

Code : `src/components/carte.js`.

La carte est dessinée en SVG avec la bibliothèque d3, à partir des fichiers de l'étape 5 et de `sites.csv`.

- **Projection** : conique conforme de Lambert, avec les parallèles 44° et 49° et le méridien 3° E, ajustée au contour de la région.
- **Couches**, de bas en haut :

| Couche | Couleur | Remarque |
| --- | --- | --- |
| région, puis départements | fond `#f3efe6`, contours `#555` et `#b8b3a6` | |
| cours d'eau hors bassin | sans mesure `#a9b8c3`, avec mesure `#2b7bb9` | estompés (opacité 45 % et 35 %) |
| cours d'eau du bassin | sans mesure `#a9b8c3`, avec mesure `#2b7bb9` | |
| la Moselle et la Moselle canalisée | `#d6452b` | |
| 64 sites de mesure du bassin | cercle blanc bordé de bleu, rouge pour les 13 sites de la Moselle | le nom du site s'affiche au survol |

- **Zoom** : de 1 à 12 fois, à la molette ou au pincement, et déplacement en faisant glisser. Les traits et les sites gardent la même taille à l'écran quel que soit le zoom. Sur écran tactile, il faut deux doigts, pour qu'un seul doigt continue à faire défiler la page.
- **Poids** : les tracés représentent environ 5,8 Mo à télécharger (1,4 Mo si le serveur compresse les fichiers).

## Le profil des débits

Code : `src/components/profil.js`.

Le graphique montre le débit à chaque site de la Moselle, d'amont en aval, avec la distance en abscisse. **Chaque courbe correspond à une même semaine.** Un site sans mesure cette semaine-là n'a pas de point.

| Courbe | Couleur |
| --- | --- |
| semaine choisie avec le curseur (par défaut, la plus récente) | `#0b4f71`, trait épais |
| semaine du débit le plus élevé (1ᵉʳ janvier 2018) | `#c77700` |
| semaine du débit le plus faible (8 août 2022) | `#7b6bb0` |
| débit médian de chaque site, toutes semaines confondues | gris, en tirets |

- **Échelle** logarithmique par défaut, avec des graduations 1-3-10, ou linéaire. Les bornes de l'axe sont fixes, quelle que soit la semaine.
- Sous le graphique sont affichés l'indice de la semaine choisie et son rang parmi les semaines classées.
- Les débits affichés viennent directement de `mesures.csv`, et l'indice de `profil_semaines.csv`.

