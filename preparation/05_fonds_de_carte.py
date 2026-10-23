"""Étape 5 : préparer les fonds de carte de l'application.

1. Cours d'eau : tous les tracés de la région sont gardés, avec seulement
   les propriétés utiles à la carte :
     CdOH, TopoOH  identifiant et nom du tracé ;
     categorie     « moselle » (la Moselle et la Moselle canalisée),
                   « bassin » (autre tracé du bassin, étape 2),
                   « hors_bassin » ;
     mesure        1 si au moins un site de mesure est rattaché au tracé
                   (étape 3, tous les sites de la région), sinon 0.
   Les tracés sont ensuite simplifiés avec mapshaper 0.7.95 (version figée
   dans package.json) :
     -simplify 10% keep-shapes   garde 10 % des sommets supprimables, sans
                                 faire disparaître de tracé ;
     precision=0.0001            coordonnées arrondies à 0,0001° (≈ 10 m) ;
     -filter remove-empty        dans un second passage, retire les objets
                                 devenus vides avec l'arrondi.
2. Région et départements : pas de simplification, seulement le même
   arrondi des coordonnées (precision=0.0001).

Contrôles
---------
  - le nombre de tracés avant et après simplification (les objets retirés
    sont listés) ;
  - tous les tracés du bassin et tous les tracés rattachés à un site sont
    présents après simplification ;
  - nombre de sommets et taille des fichiers, avant et après.

Entrées : donnees-originales/cours-eau-region_1791104972648.geojson
          donnees-originales/region-grand-est.geojson
          donnees-originales/departements-grand-est.geojson
          donnees-intermediaires/02_bassin_moselle.csv (étape 2)
          donnees-intermediaires/03_sites_rattaches.csv (étape 3)
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
ENTREE_SITES = INTERMEDIAIRES / "03_sites_rattaches.csv"
TEMPORAIRE = INTERMEDIAIRES / "05_cours_eau_proprietes.geojson"
TEMPORAIRE_SIMPLIFIE = INTERMEDIAIRES / "05_cours_eau_simplifies.geojson"
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
    with ENTREE_SITES.open(encoding="utf-8", newline="") as f:
        avec_mesure = {r["CdOH"] for r in csv.DictReader(f) if r["CdOH"]}

    # 1. Propriétés utiles seulement, puis simplification.
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
            "mesure": 1 if p["CdOH"] in avec_mesure else 0,
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
              "-o", f"precision={PRECISION}", "format=geojson", str(sortie_traces))

    # 2. Région et départements : arrondi des coordonnées seulement.
    for entree, nom in (("region-grand-est.geojson", "region.geojson"),
                        ("departements-grand-est.geojson", "departements.geojson")):
        mapshaper(str(ORIGINES / entree),
                  "-o", f"precision={PRECISION}", "format=geojson", str(SORTIES / nom))

    # Contrôles.
    simplifies = json.loads(sortie_traces.read_text(encoding="utf-8"))["features"]
    codes_apres = {o["properties"]["CdOH"] for o in simplifies}
    retires = [o["properties"] for o in objets if o["properties"]["CdOH"] not in codes_apres]
    manquants_bassin = bassin - codes_apres
    manquants_sites = avec_mesure - codes_apres
    if manquants_bassin or manquants_sites:
        arreter(f"tracés perdus à la simplification : bassin {sorted(manquants_bassin)}, "
                f"sites {sorted(manquants_sites)}")

    def compte(categorie=None, mesure=None):
        return sum(1 for o in simplifies
                   if (categorie is None or o["properties"]["categorie"] == categorie)
                   and (mesure is None or o["properties"]["mesure"] == mesure))

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
        f"Tracés avec au moins un site de mesure : {compte(mesure=1)} "
        f"(dont {compte('moselle', 1) + compte('bassin', 1)} dans le bassin)",
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
    styles = {
        ("hors_bassin", 0): dict(color="#d5dde3", lw=0.4, zorder=1),
        ("hors_bassin", 1): dict(color="#a9b8c3", lw=0.9, zorder=2),
        ("bassin", 0): dict(color="#9cc3e0", lw=0.5, zorder=3),
        ("bassin", 1): dict(color="#2b7bb9", lw=1.2, zorder=4),
        ("moselle", 0): dict(color="#0b3d66", lw=2.2, zorder=5),
        ("moselle", 1): dict(color="#0b3d66", lw=2.2, zorder=5),
    }
    for o in simplifies:
        style = styles[(o["properties"]["categorie"], o["properties"]["mesure"])]
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
        ("#0b3d66", "Moselle et Moselle canalisée"),
        ("#2b7bb9", "bassin, avec site de mesure"),
        ("#9cc3e0", "bassin, sans site de mesure"),
        ("#a9b8c3", "hors bassin, avec site de mesure"),
        ("#d5dde3", "hors bassin, sans site de mesure"),
    ]
    for couleur, texte in legende:
        ax.plot([], [], color=couleur, lw=2, label=texte)
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.set_title(f"Fond de carte : tracés simplifiés à {POURCENTAGE} (longitude, latitude)")
    # Un degré de longitude est plus court qu'un degré de latitude : on
    # corrige par le cosinus de la latitude moyenne des tracés.
    latitudes = [pt[1] for o in simplifies for ligne in lignes(o["geometry"]) for pt in ligne]
    ax.set_aspect(1 / math.cos(math.radians(sum(latitudes) / len(latitudes))))
    ax.axis("off")
    fig.savefig(SORTIE_CARTE, bbox_inches="tight")
    print(f"Fichiers écrits dans src/data/, {SORTIE_JOURNAL.relative_to(RACINE)}, "
          f"{SORTIE_CARTE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
