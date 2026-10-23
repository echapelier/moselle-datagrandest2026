// Profil des débits le long de la Moselle : le débit à chaque site, d'amont
// en aval, pour une même semaine (reprise du graphique des essais dans le
// notebook).

import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";

export const COULEURS_PROFIL = {
  choisie: "#0b4f71",
  haut: "#c77700",
  bas: "#7b6bb0",
  mediane: "#8a8a8a"
};

const dateFr = (date) =>
  new Date(date).toLocaleDateString("fr-FR", {day: "numeric", month: "long", year: "numeric", timeZone: "UTC"});
const nombreFr = (x) => x.toLocaleString("fr-FR", {maximumSignificantDigits: 3});

// Prépare les données une fois pour toutes : sites dans l'ordre amont → aval,
// débits valides (> 0) par site et par semaine, semaines extrêmes.
export function preparerProfil({profilSites, profilSemaines, mesures}) {
  // « retenu » : site qui sert au calcul de l'indice, des semaines extrêmes
  // et de la courbe du débit médian (série presque complète, voir l'Annexe).
  const sites = profilSites.map((s) => ({...s, km: +s.distance_km, mediane: +s.debit_median, retenu: s.retenu_calcul === "1"}));
  const ensemble = new Set(sites.map((s) => s.site));
  const debits = new Map(sites.map((s) => [s.site, new Map()]));
  for (const m of mesures) {
    if (ensemble.has(m.site) && m.debit !== "" && +m.debit > 0) debits.get(m.site).set(m.semaine, +m.debit);
  }
  const semaines = profilSemaines.map((w) => ({
    ...w,
    nb_sites: +w.nb_sites,
    indice: w.indice === "" ? null : +w.indice,
    classee: w.classee === "1"
  }));
  const classees = d3.sort(semaines.filter((w) => w.classee), (w) => -w.indice);
  const nbRetenus = sites.filter((s) => s.retenu).length;
  return {sites, nbRetenus, debits, semaines, classees, haut: classees[0], bas: classees[classees.length - 1]};
}

// Durée d'affichage de chaque semaine pendant le film : 1 393 semaines en
// 2 min 47 s, ce qui laisse de la marge pour des arrêts plus longs.
export const DUREE_SEMAINE_MS = 120;

// Curseur de semaine et film. Sa valeur est l'indice de la semaine dans la
// liste.
//   ▶ lance le défilement vers les semaines suivantes, ◀ vers les
//     précédentes ; un nouveau clic sur la même flèche met en pause, un clic
//     sur l'autre flèche inverse le sens.
//   Le film s'arrête à la première ou à la dernière semaine ; relancé depuis
//   ce bout, il repart de l'autre bout.
//   Déplacer le curseur à la main met le film en pause.
export function choixSemaine(semaines, {valeur = semaines.length - 1, invalidation} = {}) {
  const form = document.createElement("form");
  form.className = "choix-semaine";
  form.innerHTML = `<label>Semaine du</label>
    <button type="button" data-sens="-1"></button>
    <input type="range" min="0" max="${semaines.length - 1}" step="1" value="${valeur}" aria-label="Semaine">
    <button type="button" data-sens="1"></button>
    <output></output>`;
  const boutons = [...form.querySelectorAll("button")];
  const curseur = form.querySelector("input");
  const sortie = form.querySelector("output");
  const dernier = semaines.length - 1;
  let sens = 0; // 0 = en pause, 1 = vers les semaines suivantes, -1 = vers les précédentes
  let film = 0; // numéro du film en cours ; change à chaque pause, pour ignorer les étapes déjà prévues
  let prochaine = 0; // heure prévue de la prochaine semaine (ms)

  const afficher = () => {
    form.value = +curseur.value;
    sortie.value = new Date(semaines[form.value].date).toLocaleDateString("fr-FR", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"});
  };
  // Le bouton du sens en cours affiche « pause ».
  const majBoutons = () => {
    for (const b of boutons) {
      const actif = +b.dataset.sens === sens;
      b.textContent = actif ? "⏸" : +b.dataset.sens > 0 ? "▶" : "◀";
      b.title = actif ? "Pause" : +b.dataset.sens > 0 ? "Défiler vers les semaines suivantes" : "Défiler vers les semaines précédentes";
      b.setAttribute("aria-pressed", actif);
    }
  };
  const pause = () => {
    film++;
    sens = 0;
    majBoutons();
  };
  // Passe à la semaine suivante dans le sens du film et prévient la page.
  const avancer = () => {
    const i = +curseur.value + sens;
    if (i < 0 || i > dernier) return pause();
    curseur.value = i;
    afficher();
    form.dispatchEvent(new Event("input", {bubbles: true}));
    if (i === 0 || i === dernier) pause();
  };
  // Une étape toutes les DUREE_SEMAINE_MS, calée sur une heure prévue pour
  // ne pas accumuler de retard. Chaque étape attend aussi que le navigateur
  // ait dessiné l'image précédente (requestAnimationFrame) : sur une machine
  // lente, le film ralentit au lieu de laisser le graphique en retard sur
  // le curseur.
  const planifier = (numero) => {
    prochaine += DUREE_SEMAINE_MS;
    setTimeout(() => requestAnimationFrame(() => {
      if (numero !== film) return; // film mis en pause entre-temps
      avancer();
      if (sens !== 0) planifier(numero);
    }), Math.max(0, prochaine - performance.now()));
  };
  const lancer = (nouveauSens) => {
    pause();
    sens = nouveauSens;
    // Depuis le bout du film, on repart de l'autre bout.
    if (sens > 0 && +curseur.value === dernier) curseur.value = 0;
    if (sens < 0 && +curseur.value === 0) curseur.value = dernier;
    majBoutons();
    afficher();
    form.dispatchEvent(new Event("input", {bubbles: true}));
    prochaine = performance.now();
    planifier(film);
  };

  for (const b of boutons) {
    b.onclick = () => (+b.dataset.sens === sens ? pause() : lancer(+b.dataset.sens));
  }
  // Curseur déplacé à la main : pause, puis mise à jour.
  curseur.addEventListener("input", () => {
    pause();
    afficher();
  });
  form.onsubmit = (e) => e.preventDefault();
  invalidation?.then(pause);
  majBoutons();
  afficher();
  return form;
}

// Les quatre courbes : débit médian, semaines extrêmes, semaine choisie.
function courbesDuProfil(profil, semaine) {
  return [
    {cle: "mediane", nom: "Débit médian du site*", couleur: COULEURS_PROFIL.mediane, epaisseur: 1.5, tirets: "4,3"},
    {cle: "bas", nom: `Plus faible (${dateFr(profil.bas.date)})`, semaine: profil.bas.semaine, couleur: COULEURS_PROFIL.bas, epaisseur: 1.8},
    {cle: "haut", nom: `Plus élevé (${dateFr(profil.haut.date)})`, semaine: profil.haut.semaine, couleur: COULEURS_PROFIL.haut, epaisseur: 1.8},
    {cle: "choisie", nom: `Semaine du ${dateFr(semaine.date)}`, semaine: semaine.semaine, couleur: COULEURS_PROFIL.choisie, epaisseur: 3}
  ];
}

// Légende, affichée à part pour que le graphique garde la hauteur prévue.
export function legendeProfil(profil, semaine) {
  const courbes = courbesDuProfil(profil, semaine);
  return Plot.legend({color: {domain: courbes.map((c) => c.nom), range: courbes.map((c) => c.couleur)}, swatchSize: 12});
}

export function graphiqueProfil(profil, {semaine, echelleLog, width, height}) {
  const courbes = courbesDuProfil(profil, semaine);
  // Une courbe de semaine (choisie, maximum, minimum) montre tous les débits
  // disponibles cette semaine-là ; un site sans débit n'a pas de point. Seule
  // la courbe du débit médian, qui est un calcul, se limite aux sites retenus.
  const points = courbes.flatMap((c) =>
    profil.sites
      .filter((s) => c.cle !== "mediane" || s.retenu)
      .map((s) => ({
        courbe: c.nom,
        site: s.libelle_site,
        km: s.km,
        debit: c.cle === "mediane" ? s.mediane : profil.debits.get(s.site).get(c.semaine)
      }))
      .filter((p) => p.debit !== undefined)
  );

  // Bornes fixes (toutes semaines confondues) pour que l'axe ne bouge pas
  // d'une semaine à l'autre ; en log, puissances de 10 et graduations 1-3-10.
  const tous = [...profil.debits.values()].flatMap((m) => [...m.values()]);
  const [mini, maxi] = d3.extent(tous);
  const bas = 10 ** Math.floor(Math.log10(mini));
  const haut = 10 ** Math.ceil(Math.log10(maxi));
  const gradLog = d3.range(Math.log10(bas), Math.log10(haut) + 1).flatMap((e) => [10 ** e, 3 * 10 ** e]).filter((t) => t <= haut);

  const kmMax = d3.max(profil.sites, (s) => s.km) * 1.03;
  const milieu = kmMax / 2;

  return Plot.plot({
    width,
    height,
    marginLeft: 64,
    marginRight: 16,
    // Place au-dessus de la zone des courbes pour l'info-bulle des sites.
    marginTop: 52,
    x: {label: width < 500 ? "Distance depuis l'amont (km) →" : "Distance depuis l'extrémité amont du tracé, dans la région (km) →", grid: true, domain: [0, kmMax]},
    y: {
      type: echelleLog ? "log" : "linear",
      domain: echelleLog ? [bas, haut] : [0, maxi * 1.05],
      ticks: echelleLog ? gradLog : undefined,
      grid: true,
      label: "↑ Débit (L/s)",
      tickFormat: (d) => d.toLocaleString("fr-FR")
    },
    color: {domain: courbes.map((c) => c.nom), range: courbes.map((c) => c.couleur)},
    marks: [
      // Une ligne verticale par site de mesure : pleine pour les sites
      // retenus, en pointillés pour les autres. Au passage de la souris, la
      // ligne se renforce.
      Plot.ruleX(profil.sites.filter((s) => s.retenu), {x: "km", stroke: "#b5b5b5", strokeWidth: 1}),
      Plot.ruleX(profil.sites.filter((s) => !s.retenu), {x: "km", stroke: "#b5b5b5", strokeWidth: 1, strokeDasharray: "3,3"}),
      Plot.ruleX(profil.sites, Plot.pointerX({x: "km", stroke: "#555", strokeWidth: 1.5, maxRadius: 10})),
      ...courbes.flatMap((c) => {
        const donnees = points.filter((p) => p.courbe === c.nom);
        return [
          Plot.line(donnees, {x: "km", y: "debit", stroke: "courbe", strokeWidth: c.epaisseur, strokeDasharray: c.tirets}),
          Plot.dot(donnees, {x: "km", y: "debit", fill: "courbe", r: c.cle === "choisie" ? 4 : 2.5})
        ];
      }),
      // Nom du site, au-dessus de la zone des courbes (dans la marge du haut),
      // dessiné en dernier pour passer devant tout le reste. L'info-bulle
      // s'ouvre vers la droite pour les sites de la première moitié du
      // graphique, vers la gauche pour les autres, pour ne pas être coupée.
      ...[
        {sites: profil.sites.filter((s) => s.km <= milieu), anchor: "bottom-left"},
        {sites: profil.sites.filter((s) => s.km > milieu), anchor: "bottom-right"}
      ].map(({sites, anchor}) =>
        Plot.tip(
          sites,
          Plot.pointerX({
            x: "km",
            frameAnchor: "top",
            anchor,
            maxRadius: 10,
            title: (s) => `${s.libelle_site}\n${s.km.toLocaleString("fr-FR", {maximumFractionDigits: 1})} km depuis l'amont`
          })
        )
      )
    ]
  });
}
