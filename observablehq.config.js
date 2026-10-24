// Configuration de l'app Observable Framework.
// Documentation : https://observablehq.com/framework/config

export default {
  // Titre de l'app, repris dans le titre de l'onglet du navigateur.
  title: "Moselle : 26 ans de données hydro et météo",
  lang: "fr",
  root: "src",

  // Feuille de style propre au projet (elle importe le thème de Framework).
  style: "style.css",

  // Ni barre de navigation, ni barre latérale, ni liens « page précédente /
  // suivante », ni recherche : la page Dataviz occupe tout l'écran, et
  // l'Annexe technique s'ouvre depuis le texte de la Dataviz.
  header: null,
  sidebar: false,
  pager: false,
  search: false,
  footer: null,

  // Sommaire à droite des pages longues (désactivé sur la page Dataviz).
  toc: {show: true, label: "Sommaire"},

  // Les liens finissent par « .html » : ils fonctionnent tels quels sur un
  // hébergement statique, sans règle de réécriture d'adresses.
  preserveExtension: true,

  pages: [
    {name: "Dataviz", path: "/"},
    {name: "Annexe technique", path: "/annexe-technique"}
  ]
};
