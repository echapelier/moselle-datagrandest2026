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

Les fichiers d'origine ne sont pas dans Git (trop volumineux). Pour refaire la préparation, les placer dans `donnees-originales/` :

| Fichier | Source | Date | Version |
| --- | --- | --- | --- |
| `donnees.csv` | _à compléter_ | | |
| `cours-eau-region_1791104972648.geojson` | _à compléter_ | | |
| `region-grand-est.geojson` | _à compléter_ | | |
| `departements-grand-est.geojson` | _à compléter_ | | |

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
```

Chaque script affiche ses contrôles ; certains écrivent aussi un journal dans `preparation/journaux/`.

Les fichiers intermédiaires, trop volumineux pour Git, sont écrits dans `donnees-intermediaires/` (non versionné).

## Construire et prévisualiser le site

```
npm run dev      # prévisualisation sur http://localhost:3000
npm run build    # site statique dans dist/
```

Le contenu de `dist/` se copie tel quel sur l'hébergement.
