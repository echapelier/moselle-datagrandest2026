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

<!-- À venir. -->

## Étape 2 : bassin de la Moselle

<!-- À venir. -->

## Étape 3 : rapprochement des noms entre le CSV et le GeoJSON

<!-- À venir. -->

## Étape 4 : filtrage des mesures

<!-- À venir. -->
