"""Étape 3 : rattacher chaque site de mesure à un tracé du GeoJSON.

Le CSV identifie les cours d'eau par un code et un libellé, le GeoJSON par un
nom (TopoOH). On rattache chaque site à un tracé en combinant le nom et la
position, puis on sait si le site est dans le bassin de la Moselle (étape 2).

Précision des positions
-----------------------
Les coordonnées des sites sont arrondies (2 décimales en latitude,
3 en longitude ; le script le vérifie). Une position arrondie peut être
éloignée de la vraie d'au plus un demi-pas d'arrondi dans chaque direction.
Ce seuil, calculé en mètres, est la distance maximale acceptée entre un
site et son tracé.

Règles, appliquées site par site
--------------------------------
  Normalisation des noms : accents retirés, minuscules, apostrophe
  typographique remplacée par l'apostrophe droite, espaces multiples réduits.

  a) Même nom : on cherche les tracés dont le nom normalisé est égal au
     libellé du cours d'eau normalisé, et on garde le plus proche du site,
     s'il est à moins du seuil.
  b) Mot commun : sinon, on cherche le tracé le plus proche, à moins du
     seuil, dont le nom partage un mot distinctif avec le libellé du cours
     d'eau ou avec le nom du cours d'eau dans le libellé du site (la partie
     avant « à », par exemple « La Béhine » dans « La Béhine à
     Lapoutroie »). Les mots non distinctifs (ruisseau, ru, le, la, de…)
     sont ignorés.
  c) Sinon, le site reste non rattaché.

Contrôles
---------
  - les coordonnées et libellés sont constants pour chaque site ;
  - avec la règle a), on signale les sites où un deuxième tracé de même nom
    est aussi à moins du seuil (ambiguïté) ;
  - tous les sites d'un même code de cours d'eau doivent avoir la même
    appartenance au bassin.

Entrées : donnees-intermediaires/01_donnees_nettoyees.csv (étape 1)
          donnees-intermediaires/02_bassin_moselle.csv (étape 2)
          donnees-originales/cours-eau-region_1791104972648.geojson
Sorties : donnees-intermediaires/03_sites_rattaches.csv (non versionnée)
          preparation/journaux/03_rapprocher_noms.txt

Lancement, depuis la racine du projet :
    uv run preparation/03_rapprocher_noms.py
"""

import csv
import json
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import shape

RACINE = Path(__file__).resolve().parent.parent
ENTREE_MESURES = RACINE / "donnees-intermediaires" / "01_donnees_nettoyees.csv"
ENTREE_BASSIN = RACINE / "donnees-intermediaires" / "02_bassin_moselle.csv"
ENTREE_TRACES = RACINE / "donnees-originales" / "cours-eau-region_1791104972648.geojson"
SORTIE_CSV = RACINE / "donnees-intermediaires" / "03_sites_rattaches.csv"
SORTIE_JOURNAL = RACINE / "preparation" / "journaux" / "03_rapprocher_noms.txt"

COLONNES_SITE = ["libelle_site", "code_cours_eau", "libelle_cours_eau", "lat", "lon"]
MOTS_NON_DISTINCTIFS = {
    "ruisseau", "ru", "rupt", "le", "la", "les", "l", "de", "du", "des", "d",
    "et", "a", "au", "aux", "en", "sur",
}
RAYON_TERRE_M = 6_371_000

VERS_LAMBERT93 = Transformer.from_crs("OGC:CRS84", "EPSG:2154", always_xy=True)


def arreter(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFD", texte or "").encode("ascii", "ignore").decode()
    texte = texte.lower().replace("’", "'")
    return re.sub(r"\s+", " ", texte).strip()


def mots_distinctifs(texte: str) -> set[str]:
    return {m for m in re.split(r"[^a-z0-9]+", normaliser(texte)) if m and m not in MOTS_NON_DISTINCTIFS}


def nb_decimales(valeur: str) -> int:
    return len(valeur.split(".")[1]) if "." in valeur else 0


def main() -> None:
    # Sites : une ligne par site, avec contrôle de constance.
    sites = defaultdict(set)
    with ENTREE_MESURES.open(encoding="utf-8", newline="") as f:
        for ligne in csv.DictReader(f):
            sites[ligne["site"]].add(tuple(ligne[c] for c in COLONNES_SITE))
    incoherents = [s for s, v in sites.items() if len(v) > 1]
    if incoherents:
        arreter(f"sites dont les coordonnées ou libellés varient : {incoherents}")
    sites = {s: dict(zip(COLONNES_SITE, next(iter(v)))) for s, v in sites.items()}
    print(f"{len(sites)} sites")

    # Seuil de distance tiré de la précision des coordonnées. Les zéros
    # finaux ne sont pas écrits (48.8 pour 48.80) : on prend le nombre
    # maximal de décimales comme précision.
    dec_lat = max(nb_decimales(s["lat"]) for s in sites.values())
    dec_lon = max(nb_decimales(s["lon"]) for s in sites.values())
    lat_max = max(abs(float(s["lat"])) for s in sites.values())
    demi_pas_lat = 0.5 * 10 ** -dec_lat
    demi_pas_lon = 0.5 * 10 ** -dec_lon
    ecart_nord_m = math.radians(demi_pas_lat) * RAYON_TERRE_M
    ecart_est_m = math.radians(demi_pas_lon) * RAYON_TERRE_M * math.cos(math.radians(lat_max - demi_pas_lat))
    seuil_m = math.ceil(math.hypot(ecart_nord_m, ecart_est_m))
    print(f"Précision : {dec_lat} décimales en latitude, {dec_lon} en longitude → seuil {seuil_m} m")

    # Tracés.
    objets = json.loads(ENTREE_TRACES.read_text(encoding="utf-8"))["features"]
    noms = [o["properties"]["TopoOH"] for o in objets]
    codes = [o["properties"]["CdOH"] for o in objets]
    traces = [
        shapely.transform(shape(o["geometry"]),
                          lambda xy: np.column_stack(VERS_LAMBERT93.transform(xy[:, 0], xy[:, 1])))
        for o in objets
    ]
    with ENTREE_BASSIN.open(encoding="utf-8", newline="") as f:
        bassin = {ligne["CdOH"] for ligne in csv.DictReader(f)}
    par_nom = defaultdict(list)
    for i, n in enumerate(noms):
        par_nom[normaliser(n)].append(i)
    index = shapely.STRtree(traces)

    # Rattachement, site par site.
    resultats, ambiguites = [], []
    for site, s in sorted(sites.items()):
        x, y = VERS_LAMBERT93.transform(float(s["lon"]), float(s["lat"]))
        point = shapely.Point(x, y)
        choix, methode = None, "non rattaché"

        # a) même nom.
        candidats = sorted((traces[i].distance(point), i) for i in par_nom.get(normaliser(s["libelle_cours_eau"]), []))
        proches = [(d, i) for d, i in candidats if d <= seuil_m]
        if proches:
            choix, methode = proches[0], "même nom"
            if len(proches) > 1:
                ambiguites.append((site, s, proches))
        else:
            # b) mot commun avec le libellé du cours d'eau ou du site.
            nom_dans_site = s["libelle_site"].split(" à ")[0]
            mots = mots_distinctifs(s["libelle_cours_eau"]) | mots_distinctifs(nom_dans_site)
            voisins = sorted((traces[i].distance(point), int(i))
                             for i in index.query(point, predicate="dwithin", distance=seuil_m))
            for d, i in voisins:
                if mots & mots_distinctifs(noms[i]):
                    choix, methode = (d, i), "mot commun"
                    break

        d, i = choix if choix else (None, None)
        resultats.append({
            "site": site,
            "libelle_site": s["libelle_site"],
            "code_cours_eau": s["code_cours_eau"],
            "libelle_cours_eau": s["libelle_cours_eau"],
            "CdOH": codes[i] if i is not None else "",
            "TopoOH": noms[i] if i is not None else "",
            "distance_m": f"{d:.0f}" if d is not None else "",
            "methode": methode,
            "dans_bassin": "1" if i is not None and codes[i] in bassin else "0",
        })

    # Contrôle : appartenance au bassin homogène par code de cours d'eau.
    par_code = defaultdict(set)
    for r in resultats:
        par_code[r["code_cours_eau"]].add(r["dans_bassin"])
    melanges = [c for c, v in par_code.items() if len(v) > 1]
    if melanges:
        arreter(f"cours d'eau dont les sites sont en partie dans le bassin : {melanges}")

    SORTIE_CSV.parent.mkdir(exist_ok=True)
    with SORTIE_CSV.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(resultats[0]), lineterminator="\n")
        ecrivain.writeheader()
        ecrivain.writerows(resultats)

    # Journal.
    compte = defaultdict(int)
    for r in resultats:
        compte[r["methode"]] += 1
    dans = [r for r in resultats if r["dans_bassin"] == "1"]
    codes_dans = sorted({(r["code_cours_eau"], r["libelle_cours_eau"]) for r in dans})
    distances = sorted(int(r["distance_m"]) for r in resultats if r["distance_m"])
    resume = [
        f"Sites : {len(resultats)}",
        f"Précision des coordonnées : {dec_lat} décimales en latitude, {dec_lon} en longitude",
        f"Seuil de distance site → tracé : {seuil_m} m",
        f"Rattachés par le même nom : {compte['même nom']}",
        f"Rattachés par un mot commun : {compte['mot commun']}",
        f"Non rattachés : {compte['non rattaché']}",
        f"Distance au tracé rattaché : médiane {distances[len(distances) // 2]} m, maximum {distances[-1]} m",
        f"Sites dans le bassin de la Moselle : {len(dans)}, sur {len(codes_dans)} cours d'eau",
        "",
    ]
    journal = ["Rattachements par un mot commun"]
    for r in resultats:
        if r["methode"] == "mot commun":
            journal.append(f"  {r['site']} « {r['libelle_site']} » ({r['libelle_cours_eau']}) "
                           f"→ « {r['TopoOH']} » à {r['distance_m']} m"
                           + (" [bassin]" if r["dans_bassin"] == "1" else ""))
    journal.append("")
    journal.append("Sites non rattachés")
    for r in resultats:
        if r["methode"] == "non rattaché":
            journal.append(f"  {r['site']} « {r['libelle_site']} » (code « {r['code_cours_eau']} », "
                           f"libellé « {r['libelle_cours_eau']} »)")
    journal.append("")
    journal.append("Ambiguïtés (plusieurs tracés du même nom à moins du seuil ; le plus proche est retenu)")
    for site, s, proches in ambiguites:
        detail = ", ".join(f"{codes[i]} à {d:.0f} m" + (" [bassin]" if codes[i] in bassin else "")
                           for d, i in proches)
        journal.append(f"  {site} « {s['libelle_site']} » : {detail}")
    if not ambiguites:
        journal.append("  aucune")
    journal.append("")
    journal.append("Cours d'eau mesurés dans le bassin de la Moselle (code, libellé, nombre de sites)")
    for code, libelle in codes_dans:
        n = sum(1 for r in dans if r["code_cours_eau"] == code)
        journal.append(f"  {code:<10} {libelle:<30} {n}")
    journal.append("")
    journal.append("Tous les sites (site, tracé rattaché, distance, méthode, bassin)")
    for r in resultats:
        journal.append(f"  {r['site']:<9} {r['libelle_cours_eau']:<28} → {r['TopoOH'] or '-':<30} "
                       f"{r['distance_m'] or '-':>5} m  {r['methode']:<12} {r['dans_bassin']}")
    SORTIE_JOURNAL.write_text("\n".join(resume + journal) + "\n", encoding="utf-8")
    print("\n".join(resume))
    print(f"Fichiers écrits : {SORTIE_CSV.relative_to(RACINE)}, {SORTIE_JOURNAL.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
