"""Étape 6 : données du profil des débits le long de la Moselle.

1. Distance de chaque site le long de la Moselle
------------------------------------------------
Le tracé « la Moselle » est formé de plusieurs morceaux. On en fait un
graphe (sommets = bouts des morceaux, arêtes = morceaux pondérés par leur
longueur) et on garde le plus long des plus courts chemins entre deux
bouts libres : c'est le cours de la Moselle d'une extrémité à l'autre,
dans la région.

Les sites de la Moselle et de la Moselle canalisée sont projetés sur ce
chemin (le script vérifie qu'ils en sont à moins du seuil de l'étape 3) :
la distance d'un site est la longueur du chemin entre l'extrémité amont et
son point projeté. Un site sans aucun débit valide est écarté.

Le fichier ne dit pas de quel côté est l'amont. On le déduit des débits :
le débit médian augmente vers l'aval. On calcule la corrélation de rang
(Spearman) entre la distance depuis une extrémité et le débit médian des
sites : si elle est positive, cette extrémité est l'amont.

2. Indice des semaines (méthode des essais dans le notebook)
-----------------------------------------------------------
Débits valides : strictement positifs (vides et 0 sont écartés).
Débit médian d'un site = médiane de ses débits valides.
Indice d'une semaine = moyenne géométrique, sur les sites qui ont un débit
valide cette semaine-là, de (débit / débit médian du site). 1 = débit
habituel aux sites, 2 = deux fois plus, 0,5 = deux fois moins.
Semaines classées : celles où tous les sites ont un débit valide ; s'il y
en a moins de 20, on tolère un site manquant, puis deux, etc.
Semaine du maximum / du minimum : indice le plus haut / le plus bas parmi
les semaines classées.

Entrées : donnees-originales/cours-eau-region_1791104972648.geojson
          src/data/sites.csv, src/data/mesures.csv (étape 4)
Sorties : src/data/profil_sites.csv, src/data/profil_semaines.csv
          preparation/journaux/06_profil_moselle.txt

Lancement, depuis la racine du projet :
    uv run preparation/06_profil_moselle.py
"""

import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import shape

RACINE = Path(__file__).resolve().parent.parent
ENTREE_TRACES = RACINE / "donnees-originales" / "cours-eau-region_1791104972648.geojson"
ENTREE_SITES = RACINE / "src" / "data" / "sites.csv"
ENTREE_MESURES = RACINE / "src" / "data" / "mesures.csv"
ENTREE_RATTACHEMENT = RACINE / "preparation" / "journaux" / "03_rapprocher_noms.txt"
SORTIE_SITES = RACINE / "src" / "data" / "profil_sites.csv"
SORTIE_SEMAINES = RACINE / "src" / "data" / "profil_semaines.csv"
SORTIE_JOURNAL = RACINE / "preparation" / "journaux" / "06_profil_moselle.txt"

TRACE = "la Moselle"
TRACES_DES_SITES = {"la Moselle", "la Moselle Canalisée"}
MIN_SEMAINES = 20

VERS_LAMBERT93 = Transformer.from_crs("OGC:CRS84", "EPSG:2154", always_xy=True)


def arreter(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def lambert93(geometrie):
    return shapely.transform(
        geometrie, lambda xy: np.column_stack(VERS_LAMBERT93.transform(xy[:, 0], xy[:, 1]))
    )


def rangs(valeurs: list[float]) -> list[float]:
    """Rangs (1 = plus petit), rang moyen en cas d'égalité."""
    ordre = sorted(range(len(valeurs)), key=lambda i: valeurs[i])
    r = [0.0] * len(valeurs)
    i = 0
    while i < len(ordre):
        j = i
        while j + 1 < len(ordre) and valeurs[ordre[j + 1]] == valeurs[ordre[i]]:
            j += 1
        for k in range(i, j + 1):
            r[ordre[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float:
    return statistics.correlation(rangs(x), rangs(y))


def chemin_principal(trace) -> shapely.LineString:
    """Plus long des plus courts chemins entre deux bouts libres du tracé."""
    graphe = nx.Graph()
    for morceau in trace.geoms:
        debut, fin = morceau.coords[0], morceau.coords[-1]
        # S'il y a plusieurs morceaux entre deux mêmes bouts, on garde le plus court.
        if not graphe.has_edge(debut, fin) or graphe[debut][fin]["longueur"] > morceau.length:
            graphe.add_edge(debut, fin, longueur=morceau.length, morceau=morceau)
    bouts = [n for n in graphe.nodes if graphe.degree(n) == 1]
    meilleur = None
    for i, a in enumerate(bouts):
        longueurs, chemins = nx.single_source_dijkstra(graphe, a, weight="longueur")
        for b in bouts[i + 1:]:
            if b in longueurs and (meilleur is None or longueurs[b] > meilleur[0]):
                meilleur = (longueurs[b], chemins[b])
    if meilleur is None:
        arreter("aucun chemin entre deux bouts libres du tracé")
    # Assemblage des morceaux dans l'ordre du chemin, chacun dans le bon sens.
    points = []
    for u, v in zip(meilleur[1], meilleur[1][1:]):
        coords = list(graphe[u][v]["morceau"].coords)
        if coords[0] != u:
            coords.reverse()
        points.extend(coords if not points else coords[1:])
    return shapely.LineString(points)


def main() -> None:
    # Tracé de la Moselle, en Lambert-93.
    objets = [o for o in json.loads(ENTREE_TRACES.read_text(encoding="utf-8"))["features"]
              if o["properties"]["TopoOH"] == TRACE]
    if len(objets) != 1:
        arreter(f"« {TRACE} » devrait exister exactement une fois")
    trace = lambert93(shape(objets[0]["geometry"]))
    ligne = chemin_principal(trace)

    # Sites de la Moselle et de la Moselle canalisée.
    with ENTREE_SITES.open(encoding="utf-8", newline="") as f:
        sites = [s for s in csv.DictReader(f) if s["TopoOH"] in TRACES_DES_SITES]
    # Seuil de distance site → tracé calculé à l'étape 3 (précision des
    # coordonnées), relu dans son journal.
    seuil_m = int(next(l for l in ENTREE_RATTACHEMENT.read_text(encoding="utf-8").splitlines()
                       if l.startswith("Seuil de distance")).split(":")[1].split()[0])
    for s in sites:
        point = shapely.Point(VERS_LAMBERT93.transform(float(s["lon"]), float(s["lat"])))
        s["ecart_m"] = ligne.distance(point)
        s["position_m"] = ligne.project(point)
        if s["ecart_m"] > seuil_m:
            arreter(f"le site {s['site']} est à {s['ecart_m']:.0f} m du tracé (seuil {seuil_m} m)")

    # Débits valides (> 0) par site et par semaine.
    debits = defaultdict(dict)
    dates = {}
    with ENTREE_MESURES.open(encoding="utf-8", newline="") as f:
        for m in csv.DictReader(f):
            dates[m["semaine"]] = m["date"]
            if m["site"] in {s["site"] for s in sites} and m["debit"] != "" and float(m["debit"]) > 0:
                debits[m["site"]][m["semaine"]] = float(m["debit"])
    semaines = sorted(dates)
    # Un site sans aucun débit valide ne peut pas figurer sur le profil.
    sans_debit = [s for s in sites if not debits[s["site"]]]
    sites = [s for s in sites if debits[s["site"]]]
    for s in sites:
        s["mediane"] = statistics.median(debits[s["site"]].values())
        s["nb_valides"] = len(debits[s["site"]])

    # Sens d'écoulement : la corrélation doit être positive depuis l'amont.
    rho = spearman([s["position_m"] for s in sites], [s["mediane"] for s in sites])
    if rho == 0:
        arreter("impossible de déduire le sens d'écoulement (corrélation nulle)")
    longueur = ligne.length
    for s in sites:
        s["distance_km"] = (s["position_m"] if rho > 0 else longueur - s["position_m"]) / 1000
    amont = ligne.coords[0] if rho > 0 else ligne.coords[-1]
    aval = ligne.coords[-1] if rho > 0 else ligne.coords[0]
    sites.sort(key=lambda s: s["distance_km"])

    # Indice des semaines.
    lignes_semaines = []
    for semaine in semaines:
        rapports = [math.log(debits[s["site"]][semaine] / s["mediane"])
                    for s in sites if semaine in debits[s["site"]]]
        indice = math.exp(sum(rapports) / len(rapports)) if rapports else None
        lignes_semaines.append({"semaine": semaine, "date": dates[semaine],
                                "nb_sites": len(rapports), "indice": indice})
    min_sites = len(sites)
    while min_sites > 2 and sum(1 for w in lignes_semaines if w["nb_sites"] >= min_sites) < MIN_SEMAINES:
        min_sites -= 1
    classees = sorted((w for w in lignes_semaines if w["nb_sites"] >= min_sites),
                      key=lambda w: (w["indice"], w["semaine"]))
    for w in lignes_semaines:
        w["classee"] = 1 if w["nb_sites"] >= min_sites else 0
    bas, haut = classees[0], classees[-1]

    # Sorties.
    with SORTIE_SITES.open("w", encoding="utf-8", newline="") as f:
        e = csv.writer(f, lineterminator="\n")
        e.writerow(["site", "libelle_site", "distance_km", "debit_median", "nb_debits_valides", "ecart_au_trace_m"])
        for s in sites:
            e.writerow([s["site"], s["libelle_site"], f"{s['distance_km']:.2f}", f"{s['mediane']:g}",
                        s["nb_valides"], f"{s['ecart_m']:.0f}"])
    with SORTIE_SEMAINES.open("w", encoding="utf-8", newline="") as f:
        e = csv.writer(f, lineterminator="\n")
        e.writerow(["semaine", "date", "nb_sites", "indice", "classee"])
        for w in lignes_semaines:
            e.writerow([w["semaine"], w["date"], w["nb_sites"],
                        f"{w['indice']:.6f}" if w["indice"] is not None else "", w["classee"]])

    vers_lonlat = Transformer.from_crs("EPSG:2154", "OGC:CRS84", always_xy=True)
    lonlat = lambda p: "{:.3f}, {:.3f}".format(*vers_lonlat.transform(*p))
    resume = [
        f"Tracé « {TRACE} » : {len(trace.geoms)} morceaux, chemin principal de {longueur / 1000:.1f} km",
        f"Corrélation de rang (distance, débit médian) depuis la première extrémité : {rho:+.3f}",
        f"Extrémité amont : {lonlat(amont)} ; extrémité aval : {lonlat(aval)} (longitude, latitude)",
        "",
        *(f"Site écarté (aucun débit valide) : {s['site']} {s['libelle_site']}" for s in sans_debit),
        "Sites, d'amont en aval (distance depuis l'extrémité amont, débit médian, débits valides, écart au tracé)",
    ]
    for s in sites:
        resume.append(f"  {s['site']} {s['libelle_site']:<58} {s['distance_km']:7.1f} km "
                      f"{s['mediane']:>9g} L/s {s['nb_valides']:>5} {s['ecart_m']:>5.0f} m")
    resume += [
        "",
        f"Semaines : {len(semaines)} ; semaines où les {len(sites)} sites ont un débit valide : "
        f"{sum(1 for w in lignes_semaines if w['nb_sites'] == len(sites))}",
        f"Semaines classées (au moins {min_sites} sites sur {len(sites)}) : {len(classees)}",
        f"Semaine du maximum : {haut['semaine']} ({haut['date']}), indice {haut['indice']:.3f}",
        f"Semaine du minimum : {bas['semaine']} ({bas['date']}), indice {bas['indice']:.3f}",
    ]
    SORTIE_JOURNAL.write_text("\n".join(resume) + "\n", encoding="utf-8")
    print("\n".join(resume))


if __name__ == "__main__":
    main()
