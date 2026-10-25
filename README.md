# Débits de la Moselle

Application [Observable Framework](https://observablehq.com/framework/) sur les débits de la Moselle et de son bassin dans le Grand Est. Le site produit est entièrement statique (dossier `dist/`).

## Organisation

```
donnees-originales/   fichiers d'origine (non versionnés, voir ci-dessous)
preparation/          scripts Python de préparation des données, numérotés dans l'ordre d'exécution
  empreintes.sha256   empreintes SHA-256 des fichiers d'origine
src/                  pages de l'app (Markdown) et données préparées (src/data/, versionnées)
observablehq.config.js
```

La préparation des données est séparée de la construction du site : les scripts de `preparation/` écrivent des fichiers légers dans `src/data/`, qui sont versionnés. Le site se reconstruit donc sans les fichiers d'origine ; ceux-ci ne servent qu'à refaire la préparation.

## Données d'origine

Les fichiers d'origine ne sont pas dans Git (trop volumineux). Ils ont téléchargeables directement à partir de [cette page web](https://www.datagrandest.fr/datahub/dataset/a9557bbf-673a-4936-a01e-6f250554b33f).

Les fichiers utilisés sont les suivants :

| Fichier | Rôle |
| --- | --- |
| `donnees.csv` | mesures hebdomadaires (débit, pluie, température…) par site |
| `cours-eau-region_1791104972648.geojson` | tracé des cours d’eau du Grand Est |
| `region-grand-est.geojson` | contour de la région (fond de carte) |
| `departements-grand-est.geojson` | contours des départements (fond de carte) |

 Pour refaire la préparation, les les placer dans `donnees-originales/` :

## Prérequis

- [Node.js](https://nodejs.org/) ≥ 18
- [uv](https://docs.astral.sh/uv/) (gère Python et les paquets Python ; versions figées dans `uv.lock`)

```
npm install
uv sync
```

## Préparer les données

Depuis la racine du projet, lancer les scripts dans l'ordre :

```
uv run preparation/00_verifier_empreintes.py
uv run preparation/01_nettoyer_donnees.py
uv run preparation/02_bassin_moselle.py
uv run preparation/03_rapprocher_noms.py
uv run preparation/04_filtrer_mesures.py
uv run preparation/05_fonds_de_carte.py
uv run preparation/06_profil_moselle.py
uv run preparation/06b_verifier_indice.py
uv run preparation/07_meteo_moselle.py
```

Les scripts 04 à 07 écrivent les données de l'application dans `src/data/` (`sites.csv`, `cours_eau.csv`, `mesures.csv`, `traces_cours_eau.geojson`, `region.geojson`, `departements.geojson`, `profil_sites.csv`, `profil_semaines.csv`, `profil_debits.csv`, `moselle_extremites.csv`, `meteo_semaines.csv`), qui sont versionnées. Le script 05 utilise mapshaper, installé par `npm install`.

Chaque script affiche ses contrôles ; certains écrivent aussi un journal dans `preparation/journaux/`.

Les fichiers intermédiaires, trop volumineux pour Git, sont écrits dans `donnees-intermediaires/` (non versionné).

## Construire et prévisualiser le site

```
npm run dev      # prévisualisation sur http://localhost:3000
npm run build    # site statique dans dist/
```

Le contenu de `dist/` se copie tel quel sur l'hébergement.