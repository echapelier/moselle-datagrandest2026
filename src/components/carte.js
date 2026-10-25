// Carte de la région : fond (région, départements), cours d'eau et sites de
// mesure de la Moselle. Rendu en SVG avec d3, zoom à la molette ou
// au pincement, déplacement en faisant glisser.
//
// Au départ, la carte est cadrée sur le bassin de la Moselle ; on peut
// dézoomer jusqu'à voir toute la région (bouton ou molette).

import * as d3 from "npm:d3";
import {BLEU_MOSELLE} from "./couleurs.js";

// Couleurs.
export const COULEURS = {
  cours: "#2b7bb9", // affluents de la Moselle et autres cours d'eau
  moselle: BLEU_MOSELLE, // la Moselle et la Moselle canalisée
  fondRegion: "#f3efe6",
  contourRegion: "#3C3C3C",
  contourDepartements: "#090909"
};

// Couches de cours d'eau, de bas en haut (une par catégorie du fichier des
// tracés). Les tracés hors du bassin sont estompés pour mettre en avant la
// Moselle et ses affluents.
const COUCHES = [
  {categorie: "hors_bassin", couleur: COULEURS.cours, epaisseur: 0.9, opacite: 0.35},
  {categorie: "bassin", couleur: COULEURS.cours, epaisseur: 1.2, opacite: 1},
  {categorie: "moselle", couleur: COULEURS.moselle, epaisseur: 2.6, opacite: 1}
];

// Repères de la Moselle : extrémité du tracé (fichier moselle_extremites.csv,
// étape 6), texte et côté du texte par rapport au triangle.
const REPERES = [
  {extremite: "amont", texte: ["Source"], sous: true},
  {extremite: "aval", texte: ["Tripoint", "Allemagne-France-Luxembourg"], sous: false}
];

const RAYON_SITE = 3.2; // en pixels, quel que soit le zoom

const MARGE = 10; // pixels autour du bassin (ou de la région) cadré

export function carte({region, departements, traces, sites, extremites, width, height}) {
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
    .attr("aria-label", "Carte du Grand Est : la Moselle, ses sites de mesure et ses affluents et sous-affluents")
    .style("display", "block")
    .style("cursor", "grab");

  const g = svg.append("g");
  // L'épaisseur des traits ne change pas avec le zoom.
  const traitFixe = (s) => s.style("vector-effect", "non-scaling-stroke");

  // Fond : région puis départements.
  g.append("path").datum(region).attr("d", chemin).attr("fill", COULEURS.fondRegion);
  traitFixe(
    g.append("path").datum(departements).attr("d", chemin)
      .attr("fill", "none").attr("stroke", COULEURS.contourDepartements).attr("stroke-width", 0.4)
  );
  traitFixe(
    g.append("path").datum(region).attr("d", chemin)
      .attr("fill", "none").attr("stroke", COULEURS.contourRegion).attr("stroke-width", 0.9)
  );

  // Cours d'eau : un seul chemin SVG par couche, pour rester léger
  // (plus de 8 900 tracés).
  for (const c of COUCHES) {
    const objets = traces.features.filter((f) => f.properties.categorie === c.categorie);
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

  // Sites de mesure de la Moselle et de la Moselle canalisée (les sites des
  // affluents ne sont pas dessinés).
  const surMoselle = (s) => s.TopoOH === "la Moselle" || s.TopoOH === "la Moselle Canalisée";
  const points = g
    .append("g")
    .selectAll("circle")
    .data(sites.filter(surMoselle))
    .join("circle")
    .attr("transform", (s) => `translate(${projection([+s.lon, +s.lat])})`)
    .attr("r", RAYON_SITE)
    .attr("fill", COULEURS.moselle)
    .attr("stroke", "white")
    .attr("stroke-width", 1.2);
  traitFixe(points);

  // Repères aux deux extrémités du tracé de la Moselle : sa source (amont) et
  // l'endroit où elle sort du territoire français (aval). Triangle et texte
  // gardent la même taille à l'écran quel que soit le zoom.
  const reperes = g
    .append("g")
    .style("pointer-events", "none")
    .selectAll("g")
    .data(REPERES.map((r) => {
      const e = extremites.find((x) => x.extremite === r.extremite);
      return {...r, xy: projection([+e.lon, +e.lat])};
    }))
    .join("g");
  reperes
    .append("path")
    .attr("d", d3.symbol(d3.symbolTriangle, 70)())
    .attr("fill", COULEURS.moselle)
    .attr("stroke", "white")
    .attr("stroke-width", 1);
  reperes
    .append("text")
    .attr("text-anchor", (r) => (r.xy[0] < width * 0.3 ? "start" : r.xy[0] > width * 0.7 ? "end" : "middle"))
    .style("font", "11px var(--sans-serif)")
    .style("fill", "var(--theme-foreground)")
    // Contour de la couleur du fond de page, pour lire le texte sur les tracés.
    .style("paint-order", "stroke")
    .style("stroke", "var(--theme-background)")
    .style("stroke-width", "3px")
    .style("stroke-linejoin", "round")
    .selectAll("tspan")
    .data((r) => r.texte.map((ligne, i) => ({ligne, i, r})))
    .join("tspan")
    .attr("x", ({r}) => (r.xy[0] < width * 0.3 ? 6 : r.xy[0] > width * 0.7 ? -6 : 0))
    // Sous le triangle, ou au-dessus (les lignes se lisent de haut en bas).
    .attr("y", ({i, r}) => (r.sous ? 18 + i * 13 : -9 - (r.texte.length - 1 - i) * 13))
    .text(({ligne}) => ligne);
  const placerReperes = (k) => reperes.attr("transform", (r) => `translate(${r.xy}) scale(${1 / k})`);
  placerReperes(1);

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
      placerReperes(echelle);
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
    {texte: "affluents et sous-affluents", trait: COULEURS.cours},
    {texte: "autres cours d’eau", trait: COULEURS.cours, opacite: COUCHES[0].opacite},
    {texte: "site de mesure", cercle: COULEURS.moselle}
  ];
  for (const e of elements) {
    const span = div.append("span");
    if (e.trait) span.append("i").style("background", e.trait).style("opacity", e.opacite ?? 1);
    else span.append("b").style("background", e.cercle).style("border-color", "white");
    span.append("span").text(e.texte);
  }
  return div.node();
}
