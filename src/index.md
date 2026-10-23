---
title: Dataviz
toc: false
---

```js
// Données préparées (voir l'Annexe technique). Les CSV sont lus en texte,
// sans conversion automatique, pour garder les zéros initiaux des codes.
const region = FileAttachment("data/region.geojson").json();
const departements = FileAttachment("data/departements.geojson").json();
const traces = FileAttachment("data/traces_cours_eau.geojson").json();
const sites = FileAttachment("data/sites.csv").csv();
const mesures = FileAttachment("data/mesures.csv").csv();
const profilSites = FileAttachment("data/profil_sites.csv").csv();
const profilSemaines = FileAttachment("data/profil_semaines.csv").csv();
```

```js
import {carte, legende} from "./components/carte.js";
import {preparerProfil, choixSemaine, graphiqueProfil, legendeProfil, resumeSemaine} from "./components/profil.js";
```

```js
const profil = preparerProfil({profilSites, profilSemaines, mesures});
```

```js
// Commandes du profil, placées dans la carte du graphique plus bas.
// Par défaut : la semaine la plus récente.
const entreeSemaine = choixSemaine(profil.semaines);
const iSemaine = Generators.input(entreeSemaine);
const entreeEchelle = Inputs.toggle({label: "Échelle log.", value: true});
const echelleLog = Generators.input(entreeEchelle);
```

```js
const semaine = profil.semaines[iSemaine];
```

<div class="dataviz">
  <div class="card zone zone-carte">
    ${legende()}
    <div class="carte-conteneur">
      ${resize((width, height) => carte({region, departements, traces, sites, width, height}))}
    </div>
  </div>
  <div class="card zone zone-graphique">
    <h2>Débits le long de la Moselle, d'amont en aval</h2>
    <div class="commandes">${entreeSemaine}${entreeEchelle}</div>
    ${legendeProfil(profil, semaine)}
    <div class="graphique-conteneur">
      ${resize((width, height) => graphiqueProfil(profil, {semaine, echelleLog, width, height}))}
    </div>
    <div class="resume">${resumeSemaine(profil, semaine)}</div>
  </div>
  <div class="card zone zone-texte">
    <h2>Lecture des graphiques</h2>
    <p><em>Texte à venir.</em></p>
  </div>
</div>
