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
// Commandes. Par défaut : la semaine la plus récente.
const entreeSemaine = choixSemaine(profil.semaines, {invalidation});
const iSemaine = Generators.input(entreeSemaine);
const entreeEchelle = Inputs.toggle({label: "Échelle log.", value: true});
const echelleLog = Generators.input(entreeEchelle);
```

```js
// La carte ne dépend pas de la semaine : elle n'est dessinée qu'une fois
// (et à nouveau si la fenêtre change de taille).
const blocCarte = resize((width, height) => carte({region, departements, traces, sites, width, height}));
```

```js
// Emplacements du graphique, de sa légende et du résumé. Ils restent en
// place ; seul leur contenu change à chaque semaine (voir plus bas), pour
// que le film reste fluide.
const blocGraphique = document.createElement("div");
blocGraphique.className = "graphique-conteneur";
const blocLegendeProfil = document.createElement("div");
const blocResume = document.createElement("div");
blocResume.className = "resume";
// Taille disponible pour le graphique, suivie quand la fenêtre change.
const tailleGraphique = Generators.observe((notifier) => {
  const observateur = new ResizeObserver(([e]) => notifier({width: e.contentRect.width, height: e.contentRect.height}));
  observateur.observe(blocGraphique);
  return () => observateur.disconnect();
});
```

```js
// Mise à jour à chaque semaine (curseur ou film) et à chaque changement d'échelle.
const semaine = profil.semaines[iSemaine];
if (tailleGraphique.width > 0 && tailleGraphique.height > 0) {
  blocGraphique.replaceChildren(graphiqueProfil(profil, {semaine, echelleLog, ...tailleGraphique}));
}
blocLegendeProfil.replaceChildren(legendeProfil(profil, semaine));
blocResume.textContent = resumeSemaine(profil, semaine);
```

<div class="dataviz">
  <div class="card zone zone-carte">
    <div class="carte-conteneur">${blocCarte}</div>
    ${legende()}
    ${entreeSemaine}
  </div>
  <div class="card zone zone-graphique">
    <h2>Débits le long de la Moselle, d'amont en aval</h2>
    <div class="commandes">${entreeEchelle}</div>
    ${blocLegendeProfil}
    ${blocGraphique}
    ${blocResume}
  </div>
  <div class="card zone zone-texte">
    <h2>Lecture des graphiques</h2>
    <p><em>Texte à venir.</em></p>
  </div>
</div>
