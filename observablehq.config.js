// Configuration de l'app Observable Framework.
// Documentation : https://observablehq.com/framework/config

// Onglets de la barre de navigation horizontale.
const onglets = [
  {nom: "Dataviz", chemin: "/"},
  {nom: "Annexe technique", chemin: "/annexe-technique"}
];

export default {
  title: "Débits de la Moselle",
  lang: "fr",
  root: "src",

  // Feuille de style propre au projet (elle importe le thème de Framework).
  style: "style.css",

  // Pas de barre latérale, de liens « page précédente / suivante »,
  // ni de champ de recherche : la navigation se fait par les onglets.
  sidebar: false,
  pager: false,
  search: false,
  footer: null,

  // Sommaire à droite des pages longues (désactivé sur la page Dataviz).
  toc: {show: true, label: "Sommaire"},

  // Les liens finissent par « .html » : ils fonctionnent tels quels sur un
  // hébergement statique, sans règle de réécriture d'adresses.
  preserveExtension: true,

  // Barre de navigation : l'onglet de la page courante est mis en évidence.
  // Framework transforme ces chemins en liens relatifs à la construction.
  header: ({path}) => `<nav class="onglets">
  <span class="onglets-titre">Débits de la Moselle</span>
  ${onglets
    .map(({nom, chemin}) => {
      const actif = path === chemin || (chemin === "/" && path === "/index");
      return `<a href="${chemin}"${actif ? ' aria-current="page"' : ""}>${nom}</a>`;
    })
    .join("\n  ")}
</nav>`,

  // Pages connues de Framework (la barre latérale est désactivée).
  pages: onglets.map(({nom, chemin}) => ({name: nom, path: chemin}))
};
