// Carte de la région : fond (région, départements), cours d'eau et sites de
// mesure du bassin de la Moselle. Rendu en SVG avec d3, zoom à la molette ou
// au pincement, déplacement en faisant glisser.
//
// Au départ, la carte est cadrée sur le bassin de la Moselle ; on peut
// dézoomer jusqu'à voir toute la région (bouton ou molette).

import * as d3 from "npm:d3";
import {BLEU_MOSELLE} from "./couleurs.js";

// Couleurs (mêmes conventions que les essais dans le notebook).
export const COULEURS = {
  avecMesure: "#2b7bb9", // cours d'eau avec au moins un site de mesure
  sansMesure: "#8fa1ae", // cours d'eau sans site de mesure
  moselle: BLEU_MOSELLE, // la Moselle et la Moselle canalisée
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

const MARGE = 10; // pixels autour du bassin (ou de la région) cadré

export function carte({region, departements, traces, sites, width, height}) {
  // Projection conique conforme de Lambert (parallèles 44° et 49°, méridien
  // 3° E), ajustée au bassin de la Moselle (la Moselle et ses affluents).
  const bassin = {
    type: "FeatureCollection",
    features: traces.features.filter((f) => f.properties.categorie !== "hors_bassin")
  };
  const projection = d3
    .geoConicConformal()
    .parallels([44, 49])
    .rotate([-3, 0])
    .fitExtent([[MARGE, MARGE], [width - MARGE, height - MARGE]], bassin);
  const chemin = d3.geoPath(projection);
  // Zoom minimal : celui où toute la région tient dans la carte.
  const [[x0, y0], [x1, y1]] = chemin.bounds(region);
  const zoomRegion = Math.min(1, (width - 2 * MARGE) / (x1 - x0), (height - 2 * MARGE) / (y1 - y0));

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

  // Info-bulle : nom du site au survol (ou au toucher sur écran tactile).
  const bulle = d3.create("div").attr("class", "bulle-carte").style("display", "none");
  let echelle = 1; // facteur de zoom courant
  // Met en évidence un cercle (élément SVG) et affiche le nom de son site.
  const montrer = (element, s) => {
    const cadre = conteneur.node().getBoundingClientRect();
    const cercle = element.getBoundingClientRect();
    d3.select(element).attr("r", (RAYON_SITE * 1.6) / echelle);
    bulle
      .style("display", null)
      .text(s.libelle_site)
      .style("left", `${cercle.left + cercle.width / 2 - cadre.left}px`)
      .style("top", `${cercle.top - cadre.top}px`);
  };
  const cacher = () => {
    points.attr("r", RAYON_SITE / echelle);
    bulle.style("display", "none");
  };
  // Souris : la bulle suit le survol. Écran tactile : elle apparaît au
  // toucher d'un site et disparaît au toucher ailleurs sur la carte.
  points
    .style("cursor", "pointer")
    .on("pointerenter", (event, s) => event.pointerType !== "touch" && montrer(event.currentTarget, s))
    .on("pointerleave", (event) => event.pointerType !== "touch" && cacher())
    .on("pointerdown", (event, s) => {
      if (event.pointerType !== "touch") return;
      event.stopPropagation();
      cacher();
      montrer(event.currentTarget, s);
    });
  svg.on("pointerdown.bulle", (event) => event.pointerType === "touch" && cacher());
  svg.on("pointerleave.bulle", (event) => event.pointerType !== "touch" && cacher());

  // Zoom : du cadrage de toute la région (zoomRegion) à 12 fois le cadrage
  // du bassin, sans sortir de la région. Sur écran tactile, il faut deux
  // doigts : un seul doigt fait défiler la page.
  const zoom = d3
    .zoom()
    .filter((event) => (event.touches ? event.touches.length > 1 : !event.ctrlKey || event.type === "wheel") && !event.button)
    .scaleExtent([zoomRegion, 12])
    .translateExtent([[x0 - MARGE, y0 - MARGE], [x1 + MARGE, y1 + MARGE]])
    .on("start", () => svg.style("cursor", "grabbing"))
    .on("end", () => svg.style("cursor", "grab"))
    .on("zoom", ({transform}) => {
      g.attr("transform", transform);
      echelle = transform.k;
      points.attr("r", RAYON_SITE / echelle);
      bulle.style("display", "none");
      majBouton();
    });
  svg.call(zoom);
  // d3 bloque tous les gestes tactiles du navigateur ; on rend le défilement.
  svg.style("touch-action", "pan-x pan-y");

  // Le SVG et l'info-bulle sont réunis dans un même bloc.
  const conteneur = d3
    .create("div")
    .attr("class", "carte")
    .style("width", `${width}px`)
    .style("height", `${height}px`);
  conteneur.append(() => svg.node());
  conteneur.append(() => bulle.node());

  // Bouton : voir toute la région, ou revenir au bassin.
  const bouton = conteneur.append("button").attr("type", "button").attr("class", "bouton-carte");
  const vueRegion = () => echelle < (1 + zoomRegion) / 2;
  function majBouton() {
    bouton.text(vueRegion() ? "Revenir au bassin" : "Voir toute la région");
  }
  bouton.on("click", () => {
    const cible = vueRegion()
      ? d3.zoomIdentity
      : d3.zoomIdentity
          .translate(width / 2, height / 2)
          .scale(zoomRegion)
          .translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
    svg.transition().duration(600).call(zoom.transform, cible);
  });
  majBouton();

  // Mise en évidence commandée de l'extérieur (survol d'une ligne du
  // graphique des débits) : code du site, ou null pour tout effacer.
  conteneur.node().surligner = (code) => {
    cacher();
    if (code == null) return;
    const cercle = points.filter((s) => s.site === code);
    if (!cercle.empty()) montrer(cercle.node(), cercle.datum());
  };
  return conteneur.node();
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
