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
import {preparerProfil, choixSemaine, graphiqueProfil, legendeProfil} from "./components/profil.js";
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
// Emplacements du graphique et de sa légende. Ils restent en
// place ; seul leur contenu change à chaque semaine (voir plus bas), pour
// que le film reste fluide.
const blocGraphique = document.createElement("div");
blocGraphique.className = "graphique-conteneur";
const blocLegendeProfil = document.createElement("div");
// Met en évidence un site sur la carte (code du site, ou null pour effacer).
// La carte est redessinée quand la fenêtre change de taille : on cherche
// donc la carte affichée au moment de l'appel.
const surlignerSurCarte = (code) => blocCarte.querySelector(".carte")?.surligner(code ?? null);
// Quand la souris quitte le graphique, plus rien n'est mis en évidence.
blocGraphique.addEventListener("pointerleave", () => surlignerSurCarte(null));
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
  const graphique = graphiqueProfil(profil, {semaine, echelleLog, ...tailleGraphique});
  // Survol d'une ligne verticale du graphique : le site est mis en évidence
  // sur la carte.
  graphique.addEventListener("input", () => surlignerSurCarte(graphique.value?.site));
  blocGraphique.replaceChildren(graphique);
}
blocLegendeProfil.replaceChildren(legendeProfil(profil, semaine));
```

<div class="dataviz">
  <div class="zone zone-carte">
    <div class="card carte-cadre">
      <div class="carte-conteneur">${blocCarte}</div>
      ${legende()}
    </div>
    ${entreeSemaine}
  </div>
  <div class="card zone zone-graphique">
    <h2>Débits le long de la Moselle, d'amont en aval</h2>
    <div class="commandes">${entreeEchelle}</div>
    ${blocGraphique}
    ${blocLegendeProfil}
  </div>
  <div class="card zone zone-texte">
    <h2>Lecture des graphiques</h2>
    <p><em>Texte à venir.</em></p>
  </div>
</div>
