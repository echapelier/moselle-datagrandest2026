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
  const sites = profilSites.map((s) => ({...s, km: +s.distance_km, mediane: +s.debit_median}));
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
  return {sites, debits, semaines, classees, haut: classees[0], bas: classees[classees.length - 1]};
}

// Curseur de semaine avec boutons « précédente / suivante ». Sa valeur est
// l'indice de la semaine dans la liste.
export function choixSemaine(semaines, valeur = semaines.length - 1) {
  const form = document.createElement("form");
  form.className = "choix-semaine";
  form.innerHTML = `<label>Semaine du</label>
    <button type="button" title="Semaine précédente">◀</button>
    <input type="range" min="0" max="${semaines.length - 1}" step="1" value="${valeur}">
    <button type="button" title="Semaine suivante">▶</button>
    <output></output>`;
  const [precedent, suivant] = form.querySelectorAll("button");
  const curseur = form.querySelector("input");
  const sortie = form.querySelector("output");
  const maj = () => {
    form.value = +curseur.value;
    sortie.value = new Date(semaines[form.value].date).toLocaleDateString("fr-FR", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"});
  };
  curseur.addEventListener("input", maj);
  precedent.onclick = () => {
    curseur.stepDown();
    curseur.dispatchEvent(new Event("input", {bubbles: true}));
  };
  suivant.onclick = () => {
    curseur.stepUp();
    curseur.dispatchEvent(new Event("input", {bubbles: true}));
  };
  form.onsubmit = (e) => e.preventDefault();
  maj();
  return form;
}

// Les quatre courbes : débit médian, semaines extrêmes, semaine choisie.
function courbesDuProfil(profil, semaine) {
  return [
    {cle: "mediane", nom: "Débit médian de chaque site", couleur: COULEURS_PROFIL.mediane, epaisseur: 1.5, tirets: "4,3"},
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
  // Une courbe = une seule semaine ; un site sans débit cette semaine-là n'a pas de point.
  const points = courbes.flatMap((c) =>
    profil.sites
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

  return Plot.plot({
    width,
    height,
    marginLeft: 64,
    marginRight: 16,
    x: {label: width < 500 ? "Distance depuis l'amont (km) →" : "Distance depuis l'extrémité amont du tracé, dans la région (km) →", grid: true, domain: [0, d3.max(profil.sites, (s) => s.km) * 1.03]},
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
      ...courbes.flatMap((c) => {
        const donnees = points.filter((p) => p.courbe === c.nom);
        return [
          Plot.line(donnees, {x: "km", y: "debit", stroke: "courbe", strokeWidth: c.epaisseur, strokeDasharray: c.tirets}),
          Plot.dot(donnees, {x: "km", y: "debit", fill: "courbe", r: c.cle === "choisie" ? 4 : 2.5})
        ];
      }),
      Plot.tip(
        points,
        Plot.pointer({
          x: "km",
          y: "debit",
          title: (p) => `${p.site}\n${p.courbe}\n${p.km.toLocaleString("fr-FR", {maximumFractionDigits: 1})} km depuis l'amont\n${nombreFr(p.debit)} L/s`
        })
      )
    ]
  });
}

// Phrase sous le graphique : indice et rang de la semaine choisie.
export function resumeSemaine(profil, semaine) {
  if (semaine.nb_sites === 0) return "Aucun débit mesuré cette semaine-là sur la Moselle.";
  const rang = profil.classees.indexOf(semaine);
  const texte = `Indice de la semaine : ${nombreFr(semaine.indice)} (1 = débit habituel aux sites)`;
  return rang >= 0
    ? `${texte}, ${rang + 1}ᵉ sur ${profil.classees.length} semaines classées (1ʳᵉ = la plus élevée).`
    : `${texte} ; semaine non classée (${semaine.nb_sites} sites mesurés sur ${profil.sites.length}).`;
}
