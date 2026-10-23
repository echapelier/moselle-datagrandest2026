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
```

```js
import {carte, legende} from "./components/carte.js";
```

<div class="dataviz">
  <div class="card zone zone-carte">
    ${legende()}
    <div class="carte-conteneur">
      ${resize((width, height) => carte({region, departements, traces, sites, width, height}))}
    </div>
  </div>
  <div class="card zone zone-graphique">
    <div class="emplacement">Profil le long de la Moselle (étape 8)</div>
  </div>
  <div class="card zone zone-texte">
    <h2>Lecture des graphiques</h2>
    <p><em>Texte à venir.</em></p>
  </div>
</div>
