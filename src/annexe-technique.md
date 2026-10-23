---
title: Annexe technique
---

# Annexe technique

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
5. **Exclusions.** La Sarre est exclue, et avec elle tout son sous-bassin : il n'est relié à la Moselle que par elle, et la confluence se trouve en Allemagne, hors du tracé. Les tracés dont le nom contient « canal » ou « rigole » sont aussi exclus, car ces ouvrages relient des bassins entre eux. Les **bras sont gardés** : la Seille, par exemple, rejoint la Moselle à Metz par le « Bras Mort Aval de la Moselle ». Exclure les bras ferait perdre tout le sous-bassin de la Seille.
6. **Passages vérifiés.** Six canaux et rigoles sont tout de même traversés, pour rattacher les ruisseaux qui n'atteignent la Moselle que par eux. Ces ouvrages ne font pas eux-mêmes partie du résultat.

| Ouvrage traversé | Ruisseaux rattachés | Justification |
| --- | --- | --- |
| Canal de Flottage des Salines | 17 | près de Dieuze, dans le bassin de la Seille |
| Canal des Usines | 2 | la Lizerne et le ruisseau d'Antilleux, avant la Vologne |
| Canal de Morteau | 1 | ruisseau de Clos Pres, avant la Meurthe |
| Canal de l'Est (branche sud) | 7 | entre le bief de partage, près de Golbey, et la Moselle à Neuves-Maisons : côté Moselle |
| Rigole d'alimentation du bassin de virement | 1 | ruisseau de la Borne, près de Messein |
| Rigole d'alimentation du réservoir de Bouzey | 1 | ruisseau de Pouxeux, dans la vallée de la Moselle |

Le « Canal de l'Est », c'est-à-dire la partie qui descend vers la Saône par la vallée du Coney, n'est **pas** traversé. Les 11 ruisseaux qui s'y terminent sont dans le bassin de la Saône, et l'un d'eux, le ruisseau des Sept Pêcheurs, touche directement le Coney.

**Résultat : 1 562 tracés**, soit 1 444 noms distincts, Moselle et Moselle canalisée comprises.

**Contrôle.** Les bassins voisins sont calculés de la même façon, en partant de la Sarre, de la Meuse, du Rhin, de l'Ill, de la Marne, de la Seine, de la Saône, de la Nied et de la Nied allemande. Aucun n'a de tracé en commun avec celui de la Moselle.

![Carte de contrôle du bassin de la Moselle](./annexe/02_bassin_moselle.png)

**Limites.**
- Le tracé est coupé aux limites du Grand Est. Un affluent qui rejoint la Moselle hors de la région n'est pas détecté, comme la Sûre au Luxembourg.
- Le rattachement suppose que la confluence est bien dessinée. Un ruisseau qui se perd avant d'atteindre un autre tracé reste isolé.

## Étape 3 : rapprochement des noms entre le CSV et le GeoJSON

<!-- À venir. -->

## Étape 4 : filtrage des mesures

<!-- À venir. -->
