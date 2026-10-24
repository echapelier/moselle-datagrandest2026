// Profil des débits le long de la Moselle : le débit à chaque site, d'amont
// en aval, pour une même semaine (reprise du graphique des essais dans le
// notebook).

import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {BLEU_MOSELLE} from "./couleurs.js";

export const COULEURS_PROFIL = {
  choisie: BLEU_MOSELLE,
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
  // « plancher » : valeur qui remplace un débit nul sur l'échelle
  // logarithmique (moitié du plus petit débit strictement positif du site).
  const sites = profilSites.map((s) => ({
    ...s,
    km: +s.distance_km,
    mediane: +s.debit_median,
    plancher: s.plancher_log === "" ? null : +s.plancher_log,
    retenu: s.retenu_calcul === "1"
  }));
  const ensemble = new Set(sites.map((s) => s.site));
  // Débits valides : renseignés et positifs ou nuls (un débit nul est une
  // mesure : cours d'eau à sec). Seuls les vides et le code d'erreur -1 sont
  // écartés.
  const debits = new Map(sites.map((s) => [s.site, new Map()]));
  for (const m of mesures) {
    if (ensemble.has(m.site) && m.debit !== "" && +m.debit >= 0) debits.get(m.site).set(m.semaine, +m.debit);
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

// Durée d'affichage de chaque semaine pendant le film (ms).
//   Film guidé : vitesse de croisière rapide, puis ralentissement progressif
//   sur les dernières semaines avant chaque arrêt, pour voir venir la
//   semaine remarquable.
//   Mode libre : vitesse constante.
export const VITESSE = {croisiere: 25, ralenti: 150, semainesDeRalentissement: 20, libre: 60};

// Barre de semaine : curseur et film. Sa valeur est l'indice de la semaine
// dans la liste. Deux modes :
//
//   Mode guidé (film commenté) : le curseur et les flèches sont bloqués ;
//   seul un bouton lecture / pause est proposé. Le film avance vers les
//   semaines suivantes et s'arrête de lui-même aux semaines d'arrêt et à la
//   dernière semaine : la barre émet alors un événement « arret » (detail =
//   indice de la semaine).
//
//   Mode libre : ▶ fait défiler vers les semaines suivantes, ◀ vers les
//   précédentes ; un nouveau clic sur la même flèche met en pause, un clic
//   sur l'autre flèche inverse le sens. Le film s'arrête à la première ou à
//   la dernière semaine ; relancé depuis ce bout, il repart de l'autre bout.
//   Déplacer le curseur à la main met le film en pause.
//
// La page pilote la barre avec form.lancer(sens), form.pause(),
// form.allerA(indice), form.guider(vrai ou faux) et form.arrets (liste
// d'indices).
export function choixSemaine(semaines, {valeur = 0, invalidation} = {}) {
  const form = document.createElement("form");
  form.className = "choix-semaine";
  form.innerHTML = `<label>Semaine du</label>
    <button type="button" data-sens="-1"></button>
    <button type="button" data-role="lecture"></button>
    <input type="range" min="0" max="${semaines.length - 1}" step="1" value="${valeur}" aria-label="Semaine">
    <button type="button" data-sens="1"></button>
    <output></output>`;
  const fleches = [...form.querySelectorAll("button[data-sens]")];
  const lecture = form.querySelector("button[data-role=lecture]");
  const curseur = form.querySelector("input");
  const sortie = form.querySelector("output");
  const dernier = semaines.length - 1;
  let sens = 0; // 0 = en pause, 1 = vers les semaines suivantes, -1 = vers les précédentes
  let film = 0; // numéro du film en cours ; change à chaque pause, pour ignorer les étapes déjà prévues
  let prochaine = 0; // heure prévue de la prochaine semaine (ms)
  let guide = false;
  form.arrets = [];

  const afficher = () => {
    form.value = +curseur.value;
    sortie.value = new Date(semaines[form.value].date).toLocaleDateString("fr-FR", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"});
  };
  const prevenir = () => form.dispatchEvent(new Event("input", {bubbles: true}));
  // Boutons : en mode libre, le bouton du sens en cours affiche « pause » ;
  // en mode guidé, un seul bouton lecture / pause.
  const majBoutons = () => {
    for (const b of fleches) {
      const actif = +b.dataset.sens === sens;
      b.hidden = guide;
      b.textContent = actif ? "⏸" : +b.dataset.sens > 0 ? "▶" : "◀";
      b.title = actif ? "Pause" : +b.dataset.sens > 0 ? "Défiler vers les semaines suivantes" : "Défiler vers les semaines précédentes";
      b.setAttribute("aria-pressed", actif);
    }
    lecture.hidden = !guide;
    lecture.textContent = sens ? "⏸" : "▶";
    lecture.title = sens ? "Pause" : "Lecture";
    lecture.setAttribute("aria-pressed", sens !== 0);
    curseur.disabled = guide;
  };
  const pause = () => {
    film++;
    sens = 0;
    majBoutons();
  };
  const arreter = (i) => {
    pause();
    form.dispatchEvent(new CustomEvent("arret", {detail: i}));
  };
  // Passe à la semaine suivante dans le sens du film et prévient la page.
  const avancer = () => {
    const i = +curseur.value + sens;
    if (i < 0 || i > dernier) return pause();
    curseur.value = i;
    afficher();
    prevenir();
    if (guide && sens > 0 && (form.arrets.includes(i) || i === dernier)) arreter(i);
    else if (i === 0 || i === dernier) pause();
  };
  // Une étape à chaque durée prévue (voir VITESSE), calée sur une heure pour
  // ne pas accumuler de retard. Chaque étape attend aussi que le navigateur
  // ait dessiné l'image précédente (requestAnimationFrame) : sur une machine
  // lente, le film ralentit au lieu de laisser le graphique en retard sur
  // le curseur.
  // Durée d'affichage de la semaine d'indice i, qui va être montrée.
  const duree = (i) => {
    if (!guide || sens < 0) return VITESSE.libre;
    // Nombre de semaines jusqu'au prochain arrêt (0 = c'est l'arrêt).
    const arret = Math.min(dernier, ...form.arrets.filter((a) => a >= i));
    const reste = arret - i;
    if (reste >= VITESSE.semainesDeRalentissement) return VITESSE.croisiere;
    // Ralentissement progressif (quadratique) jusqu'à la durée « ralenti ».
    const t = 1 - reste / VITESSE.semainesDeRalentissement;
    return VITESSE.croisiere + (VITESSE.ralenti - VITESSE.croisiere) * t * t;
  };
  const planifier = (numero) => {
    prochaine += duree(+curseur.value + sens);
    setTimeout(() => requestAnimationFrame(() => {
      if (numero !== film) return; // film mis en pause entre-temps
      avancer();
      if (sens !== 0) planifier(numero);
    }), Math.max(0, prochaine - performance.now()));
  };
  const lancer = (nouveauSens) => {
    pause();
    sens = nouveauSens;
    // En mode libre, depuis le bout du film, on repart de l'autre bout.
    if (!guide && sens > 0 && +curseur.value === dernier) curseur.value = 0;
    if (!guide && sens < 0 && +curseur.value === 0) curseur.value = dernier;
    majBoutons();
    afficher();
    prevenir();
    prochaine = performance.now();
    planifier(film);
  };

  for (const b of fleches) {
    b.onclick = () => (+b.dataset.sens === sens ? pause() : lancer(+b.dataset.sens));
  }
  lecture.onclick = () => (sens ? pause() : lancer(1));
  // Curseur déplacé à la main (mode libre) : pause, puis mise à jour.
  curseur.addEventListener("input", () => {
    pause();
    afficher();
  });
  form.onsubmit = (e) => e.preventDefault();

  form.lancer = lancer;
  form.pause = pause;
  form.allerA = (i) => {
    pause();
    curseur.value = i;
    afficher();
    prevenir();
  };
  form.guider = (actif) => {
    guide = actif;
    majBoutons();
  };

  invalidation?.then(pause);
  majBoutons();
  afficher();
  return form;
}

// Les quatre courbes : débit médian, semaines extrêmes, semaine choisie.
// Pendant le film, les courbes des semaines extrêmes n'apparaissent qu'une
// fois leur semaine atteinte (option « montrer »).
function courbesDuProfil(profil, semaine, montrer = {haut: true, bas: true}) {
  return [
    {cle: "mediane", nom: "Débit médian du site*", couleur: COULEURS_PROFIL.mediane, epaisseur: 1.5, tirets: "4,3"},
    {cle: "bas", nom: `Plus faible (${dateFr(profil.bas.date)})`, semaine: profil.bas.semaine, couleur: COULEURS_PROFIL.bas, epaisseur: 1.8},
    {cle: "haut", nom: `Plus élevé (${dateFr(profil.haut.date)})`, semaine: profil.haut.semaine, couleur: COULEURS_PROFIL.haut, epaisseur: 1.8},
    {cle: "choisie", nom: `Semaine du ${dateFr(semaine.date)}`, semaine: semaine.semaine, couleur: COULEURS_PROFIL.choisie, epaisseur: 3}
  ].filter((c) => montrer[c.cle] !== false);
}

// Légende, affichée à part pour que le graphique garde la hauteur prévue.
export function legendeProfil(profil, semaine, montrer) {
  const courbes = courbesDuProfil(profil, semaine, montrer);
  return Plot.legend({color: {domain: courbes.map((c) => c.nom), range: courbes.map((c) => c.couleur)}, swatchSize: 12});
}

export function graphiqueProfil(profil, {semaine, echelleLog, montrer, width, height}) {
  const courbes = courbesDuProfil(profil, semaine, montrer);
  // Une courbe de semaine (choisie, maximum, minimum) montre tous les débits
  // disponibles cette semaine-là ; un site sans débit n'a pas de point. Seule
  // la courbe du débit médian, qui est un calcul, se limite aux sites retenus.
  // Un débit nul ne peut pas figurer sur une échelle logarithmique : il y
  // est placé au plancher du site et signalé par un point creux.
  const points = courbes.flatMap((c) =>
    profil.sites
      .filter((s) => c.cle !== "mediane" || s.retenu)
      .map((s) => {
        const debit = c.cle === "mediane" ? s.mediane : profil.debits.get(s.site).get(c.semaine);
        const nul = debit === 0;
        return {courbe: c.nom, site: s.libelle_site, km: s.km, nul, y: nul && echelleLog ? s.plancher : debit};
      })
      .filter((p) => p.y !== undefined && p.y !== null)
  );

  // Bornes fixes (toutes semaines confondues) pour que l'axe ne bouge pas
  // d'une semaine à l'autre ; en log, puissances de 10 et graduations 1-3-10
  // (la borne basse tient compte des planchers).
  const tous = [...profil.debits.values()].flatMap((m) => [...m.values()]);
  const positifs = [...tous.filter((q) => q > 0), ...profil.sites.map((s) => s.plancher).filter((v) => v)];
  const mini = d3.min(positifs);
  const maxi = d3.max(tous);
  const bas = 10 ** Math.floor(Math.log10(mini));
  const haut = 10 ** Math.ceil(Math.log10(maxi));
  const gradLog = d3.range(Math.log10(bas), Math.log10(haut) + 1).flatMap((e) => [10 ** e, 3 * 10 ** e]).filter((t) => t <= haut);

  const kmMax = d3.max(profil.sites, (s) => s.km) * 1.03;

  return Plot.plot({
    width,
    height,
    marginLeft: 64,
    marginRight: 16,
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
      // ligne se renforce ; le graphique prend alors pour valeur ce site
      // (événement « input »), ce qui permet de le mettre en évidence sur la
      // carte.
      Plot.ruleX(profil.sites.filter((s) => s.retenu), {x: "km", stroke: "#b5b5b5", strokeWidth: 1}),
      Plot.ruleX(profil.sites.filter((s) => !s.retenu), {x: "km", stroke: "#b5b5b5", strokeWidth: 1, strokeDasharray: "3,3"}),
      Plot.ruleX(profil.sites, Plot.pointerX({x: "km", stroke: "#555", strokeWidth: 1.5, maxRadius: 10})),
      ...courbes.flatMap((c) => {
        const donnees = points.filter((p) => p.courbe === c.nom);
        return [
          Plot.line(donnees, {x: "km", y: "y", stroke: "courbe", strokeWidth: c.epaisseur, strokeDasharray: c.tirets}),
          Plot.dot(donnees.filter((p) => !p.nul), {x: "km", y: "y", fill: "courbe", r: c.cle === "choisie" ? 4 : 2.5}),
          // Débit nul : point creux.
          Plot.dot(donnees.filter((p) => p.nul), {x: "km", y: "y", stroke: "courbe", fill: "white", strokeWidth: 1.5, r: c.cle === "choisie" ? 4 : 2.5})
        ];
      })
    ]
  });
}
