---
title: "Moselle : 26 ans de données hydro et météo"
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
const meteoSemaines = FileAttachment("data/meteo_semaines.csv").csv();
```

```js
import {carte, legende} from "./components/carte.js";
import {preparerProfil, choixSemaine, graphiqueProfil, legendeProfil} from "./components/profil.js";
import {preparerMeteo, graphiqueTemperature, graphiquePrecipitations, legendeMeteo, COULEURS_METEO} from "./components/meteo.js";
```

```js
const profil = preparerProfil({profilSites, profilSemaines, mesures});
// Semaines où le film s'arrête : maximum, minimum, et la dernière.
const iMax = profil.semaines.indexOf(profil.haut);
const iMin = profil.semaines.indexOf(profil.bas);
const iDerniere = profil.semaines.length - 1;
```

```js
// Commandes. Au chargement : la semaine la plus ancienne.
const entreeSemaine = choixSemaine(profil.semaines, {valeur: 0, invalidation});
const iSemaine = Generators.input(entreeSemaine);
const entreeEchelle = Inputs.toggle({label: "Échelle log.", value: true});
const echelleLog = Generators.input(entreeEchelle);
```

```js
// Étape du film guidé, qui décide du texte affiché et des courbes visibles :
//   « intro » : avant le film et jusqu'à la semaine du maximum ;
//   « max »   : arrêt à la semaine du maximum, puis jusqu'au minimum ;
//   « min »   : arrêt à la semaine du minimum, puis jusqu'à la fin ;
//   « fin »   : film terminé (ou passé) ; la barre de semaine est libre.
const etape = Mutable("intro");
const definirEtape = (nouvelle) => (etape.value = nouvelle);
```

```js
// Effets d'une étape sur la page : texte affiché (attribut data-etape, voir
// style.css) et barre de semaine guidée ou libre.
function appliquerEtape(nouvelle) {
  document.documentElement.dataset.etape = nouvelle;
  entreeSemaine.guider(nouvelle !== "fin");
  entreeSemaine.arrets = nouvelle === "fin" ? [] : [iMax, iMin];
}
function allerEtape(nouvelle) {
  definirEtape(nouvelle);
  appliquerEtape(nouvelle);
  // Sur petit écran, le texte est sous le graphique : on le fait apparaître.
  if (nouvelle !== "intro" && matchMedia("(max-width: 900px)").matches) {
    document.querySelector(".zone-texte")?.scrollIntoView({behavior: "smooth", block: "start"});
  }
}
// Au chargement : introduction, film guidé.
appliquerEtape("intro");
```

```js
// Le film s'arrête de lui-même aux semaines du maximum, du minimum et à la
// dernière semaine : on passe alors à l'étape suivante.
entreeSemaine.addEventListener("arret", ({detail: i}) => {
  if (i === iMax) allerEtape("max");
  else if (i === iMin) allerEtape("min");
  else if (i === iDerniere) allerEtape("fin");
});
```

```js
// Boutons et liens des textes (attribut data-action dans le HTML plus bas).
const actions = {
  lancer: () => entreeSemaine.lancer(1),
  reprendre: () => entreeSemaine.lancer(1),
  passer: () => {
    entreeSemaine.allerA(iDerniere);
    allerEtape("fin");
  },
  revoir: () => {
    allerEtape("intro");
    entreeSemaine.allerA(0);
    entreeSemaine.lancer(1);
  },
  annexe: (lien) => ouvrirAnnexe(lien.href)
};
const surClic = (event) => {
  const element = event.target.closest("[data-action]");
  if (!element || !(element.dataset.action in actions)) return;
  event.preventDefault();
  actions[element.dataset.action](element);
};
document.addEventListener("click", surClic);
invalidation.then(() => document.removeEventListener("click", surClic));
```

```js
// Annexe technique affichée dans un panneau, par-dessus la Dataviz, sans
// recharger la page : la Dataviz garde son état. Le bouton « retour » du
// navigateur et les liens « Retour à la dataviz » de l'Annexe referment le
// panneau.
const panneauAnnexe = document.querySelector("#panneau-annexe");
const cadreAnnexe = panneauAnnexe.querySelector("iframe");
function ouvrirAnnexe(adresse) {
  entreeSemaine.pause();
  if (!cadreAnnexe.src) cadreAnnexe.src = adresse;
  panneauAnnexe.hidden = false;
  if (location.hash !== "#annexe") history.pushState({annexe: true}, "", "#annexe");
}
function fermerAnnexe() {
  if (history.state?.annexe) history.back(); // l'événement popstate cache le panneau
  else panneauAnnexe.hidden = true;
}
const surHistorique = () => (panneauAnnexe.hidden = location.hash !== "#annexe");
addEventListener("popstate", surHistorique);
invalidation.then(() => removeEventListener("popstate", surHistorique));
// Dans l'Annexe, les liens « Retour à la dataviz » referment le panneau.
cadreAnnexe.addEventListener("load", () => {
  cadreAnnexe.contentDocument.addEventListener("click", (event) => {
    if (!event.target.closest("a.retour-dataviz")) return;
    event.preventDefault();
    fermerAnnexe();
  });
});
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
// Taille disponible pour un graphique, suivie quand la fenêtre change.
const suivreTaille = (element) =>
  Generators.observe((notifier) => {
    const observateur = new ResizeObserver(([e]) => notifier({width: e.contentRect.width, height: e.contentRect.height}));
    observateur.observe(element);
    return () => observateur.disconnect();
  });
const tailleGraphique = suivreTaille(blocGraphique);
```

```js
// Graphiques météo : mêmes principes (emplacements fixes, contenu mis à jour
// à chaque semaine).
const meteo = preparerMeteo(meteoSemaines);
const blocTemperature = document.createElement("div");
blocTemperature.className = "graphique-conteneur";
const blocPrecipitations = document.createElement("div");
blocPrecipitations.className = "graphique-conteneur";
const tailleTemperature = suivreTaille(blocTemperature);
const taillePrecipitations = suivreTaille(blocPrecipitations);
```

```js
// Fenêtre de 5 semaines qui se termine par la semaine affichée.
if (tailleTemperature.width > 0 && tailleTemperature.height > 0) {
  blocTemperature.replaceChildren(graphiqueTemperature(meteo, iSemaine, tailleTemperature));
}
if (taillePrecipitations.width > 0 && taillePrecipitations.height > 0) {
  blocPrecipitations.replaceChildren(graphiquePrecipitations(meteo, iSemaine, taillePrecipitations));
}
```

```js
// Mise à jour à chaque semaine (curseur ou film), à chaque changement
// d'échelle et à chaque étape du film.
const semaine = profil.semaines[iSemaine];
// Courbes des semaines extrêmes : visibles une fois leur semaine atteinte.
const montrer = {haut: etape !== "intro", bas: etape === "min" || etape === "fin"};
if (tailleGraphique.width > 0 && tailleGraphique.height > 0) {
  const graphique = graphiqueProfil(profil, {semaine, echelleLog, montrer, ...tailleGraphique});
  // Survol d'une ligne verticale du graphique : le site est mis en évidence
  // sur la carte.
  graphique.addEventListener("input", () => surlignerSurCarte(graphique.value?.site));
  blocGraphique.replaceChildren(graphique);
}
blocLegendeProfil.replaceChildren(legendeProfil(profil, semaine, montrer));
```

<div class="dataviz">
  <div class="zone zone-carte">
    <h2>La Moselle et ses affluents en région Grand Est</h2>
    <div class="carte-cadre">
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
  <div class="card zone cadre-meteo zone-temperature">
    <h2>Température moyenne des 12 sites</h2>
    ${blocTemperature}
    ${legendeMeteo([{libelle: "semaine (°C)", couleur: COULEURS_METEO.temp}])}
  </div>
  <div class="card zone cadre-meteo zone-precipitations">
    <h2>Pluie et neige, moyennes des 12 sites</h2>
    ${blocPrecipitations}
    ${legendeMeteo([{libelle: "pluie (mm)", couleur: COULEURS_METEO.pluie}, {libelle: "neige, équivalent eau (mm)", couleur: COULEURS_METEO.neige}])}
  </div>
  <div class="card zone zone-texte">
    <!--
      Quatre textes, un par étape du film ; un seul est affiché à la fois.
      Boutons et liens d'action : data-action="lancer", "reprendre",
      "passer", "revoir" ou "annexe".
    -->
    <div class="texte-etape" data-etape="intro">
      <h1>Moselle : que nous disent vingt-six ans de données hydro et météo ?</h1>
      <p>Bien que la Moselle ne soit techniquement qu’une rivière puisqu’elle se jette dans un autre cours d’eau – le Rhin - et non dans une mer ou un océan, elle n’en constitue pas moins un cours d’eau central pour la région Grand Est, à la fois par sa localisation, sa longueur (près de 300 km dans la région) et la taille de son bassin.</p>
      <p>Prenant sa source dans le massif des Vosges, elle traverse trois départements (Vosges, Meurthe-et-Moselle et Moselle) et les chefs-lieux d’Épinal et de Metz avant de poursuivre son chemin vers le Luxembourg puis l’Allemagne, où elle rejoint le Rhin à Coblence.</p>
      <p class="actions-texte">
        <button type="button" class="bouton-film" data-action="lancer">▶ Lancer le film</button>
        <button type="button" class="lien lien-discret" data-action="passer">Passer le film</button>
      </p>
    </div>
    <div class="texte-etape" data-etape="max">
      <h2>Semaine du 1<sup>er</sup> janvier 2018 : le débit le plus élevé</h2>
      <p><em>Texte à venir.</em></p>
      <p class="actions-texte">
        <button type="button" class="bouton-film" data-action="reprendre">▶ Reprendre le film</button>
      </p>
    </div>
    <div class="texte-etape" data-etape="min">
      <h2>Semaine du 10 août 2026 : le débit le plus faible</h2>
      <p><em>Texte à venir.</em></p>
      <p class="actions-texte">
        <button type="button" class="bouton-film" data-action="reprendre">▶ Reprendre le film</button>
      </p>
    </div>
    <div class="texte-etape" data-etape="fin">
      <h2>Et maintenant ?</h2>
      <p><em>Texte à venir.</em></p>
      <p class="actions-texte">
        <button type="button" class="lien" data-action="revoir">Revoir le film</button>
        <a href="./annexe-technique" data-action="annexe">Annexe technique</a>
      </p>
    </div>
  </div>
</div>

<div id="panneau-annexe" class="panneau-annexe" hidden>
  <iframe title="Annexe technique"></iframe>
</div>
