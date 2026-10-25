// Graphiques météo : température, pluie et neige moyennes des 12 sites du
// profil, sur une fenêtre glissante de 5 semaines qui se termine par la
// semaine affichée dans le graphique des débits. Une ligne en tirets donne,
// pour les mêmes semaines de l'année, la moyenne 2000-2026.

import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";

export const COULEURS_METEO = {
  temp: "#c4572a",
  pluie: "#2b7bb9",
  neige: "#4fb3a9"
};

// Positions de la fenêtre, de la plus ancienne à la semaine affichée.
const POSITIONS = ["−4 sem.", "−3", "−2", "−1", "sem. affichée"];

// Lit meteo_semaines.csv (même ordre de semaines que le profil) et calcule
// les bornes fixes des axes, sur toute la période.
export function preparerMeteo(meteoSemaines) {
  const semaines = meteoSemaines.map((w) => ({
    semaine: w.semaine,
    temp: +w.temp,
    pluie: +w.pluie,
    neige: +w.neige,
    temp_ref: +w.temp_ref,
    pluie_ref: +w.pluie_ref,
    neige_ref: +w.neige_ref
  }));
  const temp = d3.extent(semaines.flatMap((w) => [w.temp, w.temp_ref]));
  const precipitations = [0, d3.max(semaines.flatMap((w) => [w.pluie, w.neige, w.pluie_ref, w.neige_ref]))];
  return {semaines, domaines: {temp, precipitations}};
}

// Les 5 semaines de la fenêtre qui se termine à l'indice i. Au début de la
// série, les positions sans semaine restent vides.
function fenetre(meteo, i) {
  return POSITIONS.map((position, k) => ({position, ...meteo.semaines[i - 4 + k]})).filter((w) => w.semaine);
}

// Une série : ligne pleine (valeurs de la semaine) et ligne en tirets
// (moyenne 2000-2026 des mêmes semaines de l'année).
function serie(donnees, variable, couleur) {
  return [
    Plot.line(donnees, {x: "position", y: `${variable}_ref`, stroke: couleur, strokeWidth: 1.5, strokeDasharray: "4,3", strokeOpacity: 0.7}),
    Plot.line(donnees, {x: "position", y: variable, stroke: couleur, strokeWidth: 2}),
    Plot.dot(donnees, {x: "position", y: variable, fill: couleur, r: 3})
  ];
}

function options({width, height}) {
  return {
    width,
    height,
    marginLeft: 40,
    marginRight: 30, // place pour le libellé « sem. affichée »
    marginBottom: 26,
    x: {type: "point", domain: POSITIONS, label: null, padding: 0.3}
  };
}

export function graphiqueTemperature(meteo, i, taille) {
  const donnees = fenetre(meteo, i);
  return Plot.plot({
    ...options(taille),
    y: {domain: meteo.domaines.temp, grid: true, label: "↑ °C", nice: true},
    marks: [Plot.ruleY([0], {stroke: "#ccc"}), ...serie(donnees, "temp", COULEURS_METEO.temp)]
  });
}

export function graphiquePrecipitations(meteo, i, taille) {
  const donnees = fenetre(meteo, i);
  return Plot.plot({
    ...options(taille),
    y: {domain: meteo.domaines.precipitations, grid: true, label: "↑ mm", nice: true},
    marks: [
      ...serie(donnees, "pluie", COULEURS_METEO.pluie),
      ...serie(donnees, "neige", COULEURS_METEO.neige)
    ]
  });
}

// Légendes : trait plein de la couleur de la variable, pour la semaine.
export function legendeMeteo(variables) {
  const div = d3.create("div").attr("class", "legende legende-meteo");
  for (const {libelle, couleur} of variables) {
    div.append("span").call((s) => {
      s.append("i").style("background", couleur);
      s.append("span").text(libelle);
    });
  }
  return div.node();
}

// Légende commune aux deux graphiques : tirets pour la moyenne 2000-2026.
export function legendeReference() {
  const div = d3.create("div").attr("class", "legende legende-reference");
  div.append("span").call((s) => {
    s.append("i").attr("class", "tirets");
    s.append("span").text("moyenne 2000-2026");
  });
  return div.node();
}
