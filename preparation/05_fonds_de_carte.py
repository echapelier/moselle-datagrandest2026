"""Étape 5 : préparer les fonds de carte de l'application.

1. Cours d'eau : tous les tracés de la région sont gardés, avec leur
   catégorie :
     « moselle »     la Moselle et la Moselle canalisée ;
     « bassin »      les autres tracés du bassin de la Moselle (étape 2),
                     c'est-à-dire ses affluents ;
     « hors_bassin » tous les autres tracés de la région.
   Les tracés sont ensuite simplifiés avec mapshaper 0.7.95 (version figée
   dans package.json) :
     -simplify 10% keep-shapes   garde 10 % des sommets supprimables, sans
                                 faire disparaître de tracé ;
     precision=0.0001            coordonnées arrondies à 0,0001° (≈ 10 m) ;
     -filter remove-empty        dans un second passage, retire les objets
                                 devenus vides avec l'arrondi.
   Enfin, les tracés d'une même catégorie sont regroupés : un seul objet
   (MultiLineString) par catégorie, sans identifiant ni nom, puisque la
   carte dessine toute une catégorie de la même façon. Les coordonnées ne
   changent pas.
2. Région et départements : pas de simplification, seulement le même
   arrondi des coordonnées (precision=0.0001), en gardant le sens des
   contours des fichiers d'origine (option gj2008), celui qu'attend d3.

Contrôles
---------
  - le nombre de tracés avant et après simplification (les objets retirés
    sont listés) ;
  - tous les tracés du bassin sont présents après simplification ;
  - nombre de sommets et taille des fichiers, avant et après ;
  - le regroupement garde exactement les mêmes lignes et les mêmes sommets.

Entrées : donnees-originales/cours-eau-region_1791104972648.geojson
          donnees-originales/region-grand-est.geojson
          donnees-originales/departements-grand-est.geojson
          donnees-intermediaires/02_bassin_moselle.csv (étape 2)
Sorties : src/data/traces_cours_eau.geojson, src/data/region.geojson,
          src/data/departements.geojson (versionnées)
          preparation/journaux/05_fonds_de_carte.txt
          src/annexe/05_fond_de_carte.png (carte de contrôle)

Lancement, depuis la racine du projet (après « npm install ») :
    uv run preparation/05_fonds_de_carte.py
"""

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RACINE = Path(__file__).resolve().parent.parent
ORIGINES = RACINE / "donnees-originales"
INTERMEDIAIRES = RACINE / "donnees-intermediaires"
ENTREE_TRACES = ORIGINES / "cours-eau-region_1791104972648.geojson"
ENTREE_BASSIN = INTERMEDIAIRES / "02_bassin_moselle.csv"
TEMPORAIRE = INTERMEDIAIRES / "05_cours_eau_proprietes.geojson"
TEMPORAIRE_SIMPLIFIE = INTERMEDIAIRES / "05_cours_eau_simplifies.geojson"
TEMPORAIRE_FILTRE = INTERMEDIAIRES / "05_cours_eau_simplifies_filtres.geojson"
SORTIES = RACINE / "src" / "data"
SORTIE_JOURNAL = RACINE / "preparation" / "journaux" / "05_fonds_de_carte.txt"
SORTIE_CARTE = RACINE / "src" / "annexe" / "05_fond_de_carte.png"

MAPSHAPER = RACINE / "node_modules" / ".bin" / "mapshaper"
VERSION_MAPSHAPER = "0.7.95"
POURCENTAGE = "10%"
PRECISION = "0.0001"
DEPARTS = ["la Moselle", "la Moselle Canalisée"]


def arreter(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def mapshaper(*arguments: str) -> None:
    resultat = subprocess.run([str(MAPSHAPER), *arguments], capture_output=True, text=True)
    if resultat.returncode != 0:
        arreter(f"mapshaper a échoué :\n{resultat.stderr}")


def nb_sommets(objets: list) -> int:
    def compter(coordonnees):
        if coordonnees and isinstance(coordonnees[0], (int, float)):
            return 1
        return sum(compter(c) for c in coordonnees)
    return sum(compter(o["geometry"]["coordinates"]) for o in objets if o["geometry"])


def main() -> None:
    if not MAPSHAPER.exists():
        arreter("mapshaper introuvable : lancer « npm install » à la racine du projet")
    version = subprocess.run([str(MAPSHAPER), "-v"], capture_output=True, text=True).stdout.strip()
    if version != VERSION_MAPSHAPER:
        arreter(f"mapshaper {version} trouvé, {VERSION_MAPSHAPER} attendu")

    with ENTREE_BASSIN.open(encoding="utf-8", newline="") as f:
        bassin = {r["CdOH"] for r in csv.DictReader(f)}

    # 1. Catégorie de chaque tracé, puis simplification.
    origine = json.loads(ENTREE_TRACES.read_text(encoding="utf-8"))
    objets = origine["features"]
    for o in objets:
        p = o["properties"]
        if p["TopoOH"] in DEPARTS:
            categorie = "moselle"
        elif p["CdOH"] in bassin:
            categorie = "bassin"
        else:
            categorie = "hors_bassin"
        o["properties"] = {
            "CdOH": p["CdOH"],
            "TopoOH": p["TopoOH"],
            "categorie": categorie,
        }
    INTERMEDIAIRES.mkdir(exist_ok=True)
    TEMPORAIRE.write_text(json.dumps({"type": "FeatureCollection", "features": objets},
                                     ensure_ascii=False), encoding="utf-8")
    SORTIES.mkdir(parents=True, exist_ok=True)
    sortie_traces = SORTIES / "traces_cours_eau.geojson"
    # L'arrondi des coordonnées n'est appliqué qu'à l'écriture : un très petit
    # tracé peut alors devenir vide. On simplifie et arrondit d'abord, puis
    # on retire les objets vides dans un second passage.
    mapshaper(str(TEMPORAIRE), "-simplify", POURCENTAGE, "keep-shapes",
              "-o", f"precision={PRECISION}", "format=geojson", str(TEMPORAIRE_SIMPLIFIE))
    mapshaper(str(TEMPORAIRE_SIMPLIFIE), "-filter", "remove-empty",
              "-o", f"precision={PRECISION}", "format=geojson", str(TEMPORAIRE_FILTRE))

    # 2. Région et départements : arrondi des coordonnées seulement.
    # « gj2008 » garde le sens des contours des fichiers d'origine (sens des
    # aiguilles d'une montre pour le contour extérieur), celui qu'attend d3.
    # Sans cette option, mapshaper suit la norme RFC 7946 (sens inverse) et
    # d3 dessinerait le reste du globe au lieu de la région.
    for entree, nom in (("region-grand-est.geojson", "region.geojson"),
                        ("departements-grand-est.geojson", "departements.geojson")):
        mapshaper(str(ORIGINES / entree),
                  "-o", f"precision={PRECISION}", "format=geojson", "gj2008", str(SORTIES / nom))

    # Contrôles.
    simplifies = json.loads(TEMPORAIRE_FILTRE.read_text(encoding="utf-8"))["features"]
    codes_apres = {o["properties"]["CdOH"] for o in simplifies}
    retires = [o["properties"] for o in objets if o["properties"]["CdOH"] not in codes_apres]
    manquants_bassin = bassin - codes_apres
    if manquants_bassin:
        arreter(f"tracés du bassin perdus à la simplification : {sorted(manquants_bassin)}")

    def compte(categorie):
        return sum(1 for o in simplifies if o["properties"]["categorie"] == categorie)

    # 3. Regroupement des tracés par catégorie.
    def morceaux(geometrie):
        return [geometrie["coordinates"]] if geometrie["type"] == "LineString" else geometrie["coordinates"]

    groupes = {}
    for o in simplifies:
        groupe = groupes.setdefault(o["properties"]["categorie"], {"lignes": [], "nb": 0})
        groupe["lignes"].extend(morceaux(o["geometry"]))
        groupe["nb"] += 1
    final = [
        {"type": "Feature",
         "geometry": {"type": "MultiLineString", "coordinates": g["lignes"]},
         "properties": {"categorie": categorie, "nb_traces": g["nb"]}}
        for categorie, g in sorted(groupes.items())
    ]
    # Contrôle : mêmes lignes et mêmes sommets.
    toutes = lambda liste: [l for o in liste for l in morceaux(o["geometry"])]
    if sorted(map(json.dumps, toutes(simplifies))) != sorted(map(json.dumps, toutes(final))):
        arreter("le regroupement a modifié des lignes")
    if nb_sommets(final) != nb_sommets(simplifies):
        arreter("le regroupement a modifié le nombre de sommets")
    # Écriture : un objet par ligne, comme mapshaper.
    with sortie_traces.open("w", encoding="utf-8") as f:
        f.write('{"type":"FeatureCollection","features":[\n')
        f.write(",\n".join(json.dumps(o, ensure_ascii=False, separators=(",", ":")) for o in final))
        f.write("\n]}\n")

    resume = [
        f"mapshaper {version} : -simplify {POURCENTAGE} keep-shapes, -filter remove-empty, "
        f"precision={PRECISION}",
        f"Tracés : {len(objets)} avant, {len(simplifies)} après",
    ]
    for p in retires:
        resume.append(f"  retiré (vide après arrondi) : {p['CdOH']} « {p['TopoOH'] or '(sans nom)'} »")
    resume += [
        f"Sommets des tracés : {nb_sommets(objets):_} avant, {nb_sommets(simplifies):_} après".replace("_", " "),
        f"Catégories : moselle {compte('moselle')}, bassin {compte('bassin')}, "
        f"hors_bassin {compte('hors_bassin')}",
        "Regroupement des tracés par catégorie : "
        + ", ".join(f"{o['properties']['categorie']} {o['properties']['nb_traces']}" for o in final)
        + f" → {len(final)} objets",
        f"Objets dans src/data/traces_cours_eau.geojson : {len(final)} ; sommets : "
        + f"{nb_sommets(final):_}".replace("_", " "),
        "Tailles des fichiers :",
        f"  tracés d'origine                     {ENTREE_TRACES.stat().st_size / 1e6:6.2f} Mo",
    ]
    for nom in ("traces_cours_eau.geojson", "region.geojson", "departements.geojson"):
        resume.append(f"  src/data/{nom:<27} {(SORTIES / nom).stat().st_size / 1e6:6.2f} Mo")
    SORTIE_JOURNAL.write_text("\n".join(resume) + "\n", encoding="utf-8")
    print("\n".join(resume))

    # Carte de contrôle, à partir des fichiers produits.
    def lignes(geometrie):
        if geometrie["type"] in ("LineString",):
            return [geometrie["coordinates"]]
        if geometrie["type"] in ("MultiLineString", "Polygon"):
            return geometrie["coordinates"]
        if geometrie["type"] == "MultiPolygon":
            return [anneau for polygone in geometrie["coordinates"] for anneau in polygone]
        return []

    fig, ax = plt.subplots(figsize=(12, 11), dpi=100)
    # Mêmes couleurs que la carte de l'application.
    styles = {
        "hors_bassin": dict(color="#2b7bb9", alpha=0.35, lw=0.6, zorder=1),
        "bassin": dict(color="#2b7bb9", lw=1.0, zorder=2),
        "moselle": dict(color="#0b4f71", lw=2.2, zorder=3),
    }
    for o in final:
        style = styles[o["properties"]["categorie"]]
        for ligne in lignes(o["geometry"]):
            x, y = zip(*ligne)
            ax.plot(x, y, **style)
    for nom, couleur, epaisseur in (("departements.geojson", "#bbbbbb", 0.6),
                                    ("region.geojson", "#555555", 1)):
        for o in json.loads((SORTIES / nom).read_text(encoding="utf-8"))["features"]:
            for ligne in lignes(o["geometry"]):
                x, y = zip(*ligne)
                ax.plot(x, y, color=couleur, lw=epaisseur, zorder=6)
    legende = [
        ("moselle", "Moselle et Moselle canalisée"),
        ("bassin", "affluents (bassin de la Moselle)"),
        ("hors_bassin", "autres cours d'eau"),
    ]
    for categorie, texte in legende:
        ax.plot([], [], **{**styles[categorie], "lw": 2}, label=texte)
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.set_title(f"Fond de carte : tracés simplifiés à {POURCENTAGE} (longitude, latitude)")
    # Un degré de longitude est plus court qu'un degré de latitude : on
    # corrige par le cosinus de la latitude moyenne des tracés.
    latitudes = [pt[1] for o in final for ligne in lignes(o["geometry"]) for pt in ligne]
    ax.set_aspect(1 / math.cos(math.radians(sum(latitudes) / len(latitudes))))
    ax.axis("off")
    fig.savefig(SORTIE_CARTE, bbox_inches="tight")
    print(f"Fichiers écrits dans src/data/, {SORTIE_JOURNAL.relative_to(RACINE)}, "
          f"{SORTIE_CARTE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
