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

<!-- À venir. -->

## Étape 3 : rapprochement des noms entre le CSV et le GeoJSON

<!-- À venir. -->

## Étape 4 : filtrage des mesures

<!-- À venir. -->
