// Carte de la région : fond (région, départements), cours d'eau et sites de
// mesure du bassin de la Moselle. Rendu en SVG avec d3, zoom à la molette ou
// au pincement, déplacement en faisant glisser.

import * as d3 from "npm:d3";

// Couleurs (mêmes conventions que les essais dans le notebook).
export const COULEURS = {
  avecMesure: "#2b7bb9", // cours d'eau avec au moins un site de mesure
  sansMesure: "#a9b8c3", // cours d'eau sans site de mesure
  moselle: "#d6452b", // la Moselle et la Moselle canalisée
  fondRegion: "#f3efe6",
  contourRegion: "#555",
  contourDepartements: "#b8b3a6"
};

// Couches de cours d'eau, de bas en haut. Les tracés hors du bassin sont
// estompés pour mettre en avant la Moselle et ses affluents.
const COUCHES = [
  {categorie: "hors_bassin", mesure: 0, couleur: COULEURS.sansMesure, epaisseur: 0.5, opacite: 0.45},
  {categorie: "hors_bassin", mesure: 1, couleur: COULEURS.avecMesure, epaisseur: 0.9, opacite: 0.35},
  {categorie: "bassin", mesure: 0, couleur: COULEURS.sansMesure, epaisseur: 0.7, opacite: 1},
  {categorie: "bassin", mesure: 1, couleur: COULEURS.avecMesure, epaisseur: 1.5, opacite: 1},
  {categorie: "moselle", mesure: null, couleur: COULEURS.moselle, epaisseur: 2.6, opacite: 1}
];

const RAYON_SITE = 3.2; // en pixels, quel que soit le zoom

export function carte({region, departements, traces, sites, width, height}) {
  // Projection conique conforme de Lambert (parallèles 44° et 49°, méridien
  // 3° E), ajustée à la région avec une marge de 10 pixels.
  const projection = d3
    .geoConicConformal()
    .parallels([44, 49])
    .rotate([-3, 0])
    .fitExtent([[10, 10], [width - 10, height - 10]], region);
  const chemin = d3.geoPath(projection);

  const svg = d3
    .create("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", [0, 0, width, height])
    .attr("role", "img")
    .attr("aria-label", "Carte du Grand Est : la Moselle, ses affluents et les sites de mesure")
    .style("display", "block")
    .style("cursor", "grab");

  const g = svg.append("g");
  // L'épaisseur des traits ne change pas avec le zoom.
  const traitFixe = (s) => s.style("vector-effect", "non-scaling-stroke");

  // Fond : région puis départements.
  g.append("path").datum(region).attr("d", chemin).attr("fill", COULEURS.fondRegion);
  traitFixe(
    g.append("path").datum(departements).attr("d", chemin)
      .attr("fill", "none").attr("stroke", COULEURS.contourDepartements).attr("stroke-width", 0.8)
  );
  traitFixe(
    g.append("path").datum(region).attr("d", chemin)
      .attr("fill", "none").attr("stroke", COULEURS.contourRegion).attr("stroke-width", 1.4)
  );

  // Cours d'eau : un seul chemin SVG par couche, pour rester léger
  // (plus de 8 900 tracés).
  for (const c of COUCHES) {
    const objets = traces.features.filter(
      (f) => f.properties.categorie === c.categorie && (c.mesure === null || f.properties.mesure === c.mesure)
    );
    traitFixe(
      g.append("path")
        .datum({type: "FeatureCollection", features: objets})
        .attr("d", chemin)
        .attr("fill", "none")
        .attr("stroke", c.couleur)
        .attr("stroke-width", c.epaisseur)
        .attr("stroke-opacity", c.opacite)
        .attr("stroke-linejoin", "round")
        .attr("stroke-linecap", "round")
    );
  }

  // Sites de mesure du bassin. Ceux de la Moselle sont dessinés en dernier,
  // au-dessus des autres.
  const surMoselle = (s) => s.TopoOH === "la Moselle" || s.TopoOH === "la Moselle Canalisée";
  const points = g
    .append("g")
    .selectAll("circle")
    .data(d3.sort(sites, surMoselle))
    .join("circle")
    .attr("transform", (s) => `translate(${projection([+s.lon, +s.lat])})`)
    .attr("r", RAYON_SITE)
    .attr("fill", (s) => (surMoselle(s) ? COULEURS.moselle : "white"))
    .attr("stroke", (s) => (surMoselle(s) ? "white" : COULEURS.avecMesure))
    .attr("stroke-width", 1.2);
  traitFixe(points);
  points.append("title").text((s) => s.libelle_site);

  // Zoom : de 1 à 12 fois, sans sortir du cadre de la région. Sur écran
  // tactile, il faut deux doigts : un seul doigt fait défiler la page.
  svg.call(
    d3
      .zoom()
      .filter((event) => (event.touches ? event.touches.length > 1 : !event.ctrlKey || event.type === "wheel") && !event.button)
      .scaleExtent([1, 12])
      .translateExtent([[0, 0], [width, height]])
      .on("start", () => svg.style("cursor", "grabbing"))
      .on("end", () => svg.style("cursor", "grab"))
      .on("zoom", ({transform}) => {
        g.attr("transform", transform);
        points.attr("r", RAYON_SITE / transform.k);
      })
  );
  // d3 bloque tous les gestes tactiles du navigateur ; on rend le défilement.
  svg.style("touch-action", "pan-x pan-y");

  return svg.node();
}

// Légende de la carte (traits pour les cours d'eau, cercle pour les sites).
export function legende() {
  const div = d3.create("div").attr("class", "legende");
  const elements = [
    {texte: "Moselle", trait: COULEURS.moselle},
    {texte: "affluent avec mesure", trait: COULEURS.avecMesure},
    {texte: "sans mesure", trait: COULEURS.sansMesure},
    {texte: "site de mesure", cercle: COULEURS.avecMesure}
  ];
  for (const e of elements) {
    const span = div.append("span");
    if (e.trait) span.append("i").style("background", e.trait);
    else span.append("b").style("border-color", e.cercle);
    span.append("span").text(e.texte);
  }
  return div.node();
}
