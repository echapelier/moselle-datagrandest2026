"""Étape 2 : rechercher les cours d'eau du bassin de la Moselle.

Principe
--------
Le GeoJSON ne dit ni quel cours d'eau se jette dans quel autre, ni le sens
d'écoulement. On s'appuie sur la géométrie : un affluent se termine sur le
tracé du cours d'eau qui le reçoit. Le tracé est topologiquement propre :
les extrémités tombent exactement sur l'autre tracé (tolérance de 1 m).

  1. Chaque objet du GeoJSON (un tracé, identifié par CdOH) est reprojeté en
     Lambert-93 (EPSG:2154), pour mesurer les distances en mètres.
  2. Ses extrémités sont calculées après avoir raccordé ses morceaux
     (linemerge) : ce sont les bouts libres du tracé.
  3. On note « A se termine sur B » quand une extrémité de A est à moins
     de 1 m du tracé de B.
  4. On part de la Moselle et de la Moselle canalisée, puis on remonte :
     on ajoute tout tracé qui se termine sur un tracé déjà retenu, et ainsi
     de suite (parcours en largeur). On ne fait que remonter : un tracé
     sur lequel se termine un cours d'eau du bassin n'est pas ajouté.
  5. Exclusions : la Sarre (et donc tout son sous-bassin, qui n'est atteint
     que par elle), et les tracés dont le nom contient « canal » ou
     « rigole » : ces ouvrages relient des bassins entre eux. Les « bras »
     sont gardés : la Seille, par exemple, rejoint la Moselle par le
     « Bras Mort Aval de la Moselle ».
  6. Passages vérifiés à la main : quelques canaux et rigoles sont traversés,
     pour rattacher les ruisseaux qui n'atteignent la Moselle que par eux
     (liste PASSAGES ci-dessous, avec la justification de chacun). Ces
     ouvrages ne font pas eux-mêmes partie du résultat. Le « Canal de l'Est »
     (partie qui descend vers la Saône par la vallée du Coney) n'est pas
     traversé : ses ruisseaux sont dans le bassin de la Saône.

Contrôles
---------
  - la Moselle, la Moselle canalisée et la Sarre existent chacune une fois ;
  - le résultat n'a aucun tracé en commun avec les bassins voisins
    (Sarre, Meuse, Rhin, Ill, Marne, Seine, Saône, Nied) calculés de la
    même façon ;
  - le journal liste les canaux et rigoles touchant le bassin, et ce qui
    serait ajouté si on les traversait.

Entrée  : donnees-originales/cours-eau-region_1791104972648.geojson
          donnees-originales/region-grand-est.geojson (carte de contrôle)
          donnees-originales/departements-grand-est.geojson (carte de contrôle)
Sorties : donnees-intermediaires/02_bassin_moselle.csv (non versionnée)
          preparation/journaux/02_bassin_moselle.txt
          src/annexe/02_bassin_moselle.png (carte de contrôle)

Lancement, depuis la racine du projet :
    uv run preparation/02_bassin_moselle.py
"""

import csv
import json
import re
import sys
from collections import Counter, deque
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import linemerge

RACINE = Path(__file__).resolve().parent.parent
ORIGINES = RACINE / "donnees-originales"
ENTREE = ORIGINES / "cours-eau-region_1791104972648.geojson"
SORTIE_CSV = RACINE / "donnees-intermediaires" / "02_bassin_moselle.csv"
SORTIE_JOURNAL = RACINE / "preparation" / "journaux" / "02_bassin_moselle.txt"
SORTIE_CARTE = RACINE / "src" / "annexe" / "02_bassin_moselle.png"

TOLERANCE_M = 1.0
DEPARTS = ["la Moselle", "la Moselle Canalisée"]
EXCLUS = ["la Sarre"]
OUVRAGES = re.compile(r"\b(canal|rigole)\b", re.IGNORECASE)

# Canaux et rigoles traversés malgré tout (étape 6 du principe).
PASSAGES = [
    # Près de Dieuze, dans le bassin de la Seille : 17 ruisseaux.
    "Canal de Flottage des Salines",
    # Reçoit la Lizerne et le ruisseau d'Antilleux, avant la Vologne.
    "Canal des Usines",
    # Reçoit le ruisseau de Clos Pres, avant la Meurthe.
    "Canal de Morteau",
    # Branche du canal des Vosges entre son bief de partage (près de Golbey)
    # et la Moselle à Neuves-Maisons : ses ruisseaux descendent côté Moselle
    # (Étang Garroy, Laumont, Bainville-aux-Miroirs, Bois Sarrasin, Clamées,
    # Deuille, Rupt dit Miné).
    "Canal de l'Est (Branche Sud)",
    # Près de Messein, côté Moselle : reçoit le ruisseau de la Borne.
    "Rigole d'Alimentation du Bassin de Virement",
    # Prend l'eau de la Moselle en amont d'Épinal : reçoit le ruisseau de Pouxeux.
    "Rigole d'Alimentation du Reservoir de Bouzey",
]
BASSINS_VOISINS = [
    "la Sarre", "la Meuse", "le Rhin", "l'Ill", "la Marne",
    "la Seine", "la Saône", "la Nied", "la Nied Allemande",
]

VERS_LAMBERT93 = Transformer.from_crs("OGC:CRS84", "EPSG:2154", always_xy=True)


def arreter(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def lambert93(geometrie):
    """Reprojette une géométrie de longitude/latitude en Lambert-93 (mètres)."""
    return shapely.transform(
        geometrie, lambda xy: np.column_stack(VERS_LAMBERT93.transform(xy[:, 0], xy[:, 1]))
    )


def extremites(geometrie) -> list:
    """Bouts libres d'un tracé, une fois ses morceaux raccordés."""
    fusion = linemerge(geometrie) if geometrie.geom_type == "MultiLineString" else geometrie
    lignes = [fusion] if fusion.geom_type == "LineString" else list(fusion.geoms)
    return [shapely.Point(c) for ligne in lignes for c in (ligne.coords[0], ligne.coords[-1])]


def remonter(depart: list[int], affluents: dict, exclure) -> tuple[set, dict]:
    """Parcours en largeur vers l'amont. Renvoie les tracés atteints et,
    pour chacun, le tracé sur lequel il se termine (celui qui l'a fait entrer)."""
    atteints, recepteur = set(depart), {}
    file = deque(depart)
    while file:
        courant = file.popleft()
        for affluent in sorted(affluents[courant]):
            if affluent in atteints or exclure(affluent):
                continue
            atteints.add(affluent)
            recepteur[affluent] = courant
            file.append(affluent)
    return atteints, recepteur


def main() -> None:
    objets = json.loads(ENTREE.read_text(encoding="utf-8"))["features"]
    noms = [o["properties"]["TopoOH"] for o in objets]
    codes = [o["properties"]["CdOH"] for o in objets]
    traces = [lambert93(shape(o["geometry"])) for o in objets]
    print(f"{len(objets)} tracés lus")

    def indices(nom: str) -> list[int]:
        return [i for i, n in enumerate(noms) if n == nom]

    for nom in DEPARTS + EXCLUS + PASSAGES:
        if len(indices(nom)) != 1:
            arreter(f"« {nom} » devrait exister exactement une fois ({len(indices(nom))} trouvés)")
    depart = [i for nom in DEPARTS for i in indices(nom)]
    exclus = {i for nom in EXCLUS for i in indices(nom)}
    passages = {i for nom in PASSAGES for i in indices(nom)}

    def est_ouvrage(i: int) -> bool:
        return bool(noms[i] and OUVRAGES.search(noms[i]))

    # « affluents[j] » = tracés dont une extrémité est sur le tracé j.
    index = shapely.STRtree(traces)
    affluents = {i: set() for i in range(len(traces))}
    nb_contacts = 0
    for i, trace in enumerate(traces):
        for point in extremites(trace):
            for j in index.query(point, predicate="dwithin", distance=TOLERANCE_M):
                if j != i:
                    affluents[int(j)].add(i)
                    nb_contacts += 1
    print(f"{nb_contacts} contacts extrémité → tracé (tolérance {TOLERANCE_M} m)")

    atteints, recepteur = remonter(
        depart, affluents,
        lambda i: i in exclus or (est_ouvrage(i) and i not in passages),
    )
    # Les passages servent à remonter, mais ne font pas partie du résultat.
    bassin = atteints - passages

    # Contrôle : aucun tracé commun avec les bassins voisins.
    journal = []
    journal.append("Contrôle : recouvrement avec les bassins voisins (même méthode)")
    for nom in BASSINS_VOISINS:
        voisin, _ = remonter(indices(nom), affluents, lambda i: i in depart or est_ouvrage(i))
        commun = voisin & bassin
        journal.append(f"  {nom:<20} {len(voisin):>5} tracés, {len(commun)} en commun")
        if commun:
            arreter(f"le bassin de la Moselle recouvre celui de « {nom} » : "
                    f"{sorted(noms[i] or '(sans nom)' for i in commun)[:10]}")

    # Journal : ouvrages exclus qui touchent le bassin, et ce qu'ils auraient apporté.
    ouvrages = sorted(
        {a for b in atteints for a in affluents[b] if est_ouvrage(a) and (a in passages or a not in atteints)},
        key=lambda i: noms[i],
    )
    perdus = set()
    journal.append("")
    journal.append("Canaux et rigoles qui se terminent sur un tracé du bassin ou sur un passage")
    journal.append("(entre parenthèses : cours d'eau qui n'atteignent le bassin que par eux ;")
    journal.append(" « traversé » : ouvrage de la liste PASSAGES, ses cours d'eau sont retenus)")
    for o in ouvrages:
        if o in passages:
            apportes = sorted({noms[i] for i in bassin if recepteur.get(i) == o})
            journal.append(f"  {noms[o]} [traversé] reçoit directement : {'; '.join(apportes)}")
            continue
        en_amont, _ = remonter([o], affluents, lambda i: i in atteints or i in exclus)
        en_amont = {i for i in en_amont if not est_ouvrage(i)}  # cours d'eau seulement
        perdus |= en_amont
        noms_amont = sorted({noms[i] or "(sans nom)" for i in en_amont})
        journal.append(f"  {noms[o]} ({len(en_amont)}) {'; '.join(noms_amont)}")

    # Sortie CSV : un tracé par ligne, avec celui sur lequel il se termine.
    SORTIE_CSV.parent.mkdir(exist_ok=True)
    with SORTIE_CSV.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.writer(f, lineterminator="\n")
        ecrivain.writerow(["CdOH", "TopoOH", "recepteur_CdOH", "recepteur_TopoOH"])
        for i in sorted(bassin, key=lambda i: codes[i]):
            r = recepteur.get(i)
            ecrivain.writerow([codes[i], noms[i] or "", codes[r] if r is not None else "",
                               (noms[r] or "") if r is not None else ""])

    nb_sans_nom = sum(1 for i in bassin if not noms[i])
    resume = [
        f"Tracés lus : {len(objets)}",
        f"Contacts extrémité → tracé : {nb_contacts}",
        f"Tracés du bassin de la Moselle (Moselle et Moselle canalisée comprises) : {len(bassin)}",
        f"  dont sans nom : {nb_sans_nom}",
        f"  noms distincts : {len({noms[i] for i in bassin if noms[i]})}",
        f"Canaux et rigoles touchant le bassin ou un passage : {len(ouvrages)}, dont {len(passages)} traversés",
        f"Tracés retenus grâce aux passages : {len(bassin) - len(remonter(depart, affluents, lambda i: i in exclus or est_ouvrage(i))[0])}",
        f"Tracés non retenus car atteints seulement par un canal ou une rigole : {len(perdus)}",
        "",
    ]
    SORTIE_JOURNAL.parent.mkdir(exist_ok=True)
    SORTIE_JOURNAL.write_text("\n".join(resume + journal) + "\n", encoding="utf-8")
    print("\n".join(resume))

    # Carte de contrôle.
    def dessiner(ax, geometrie, **style):
        lignes = geometrie.geoms if hasattr(geometrie, "geoms") else [geometrie]
        for ligne in lignes:
            if ligne.geom_type == "Polygon":
                ligne = ligne.exterior
            x, y = ligne.xy
            ax.plot(x, y, **style)

    def contours(fichier):
        # Le fichier de la région est un seul « Feature », celui des
        # départements une « FeatureCollection ».
        contenu = json.loads((ORIGINES / fichier).read_text(encoding="utf-8"))
        objets_fond = contenu["features"] if contenu["type"] == "FeatureCollection" else [contenu]
        return [lambert93(shape(o["geometry"])) for o in objets_fond]

    fig, ax = plt.subplots(figsize=(12, 11), dpi=100)
    for dep in contours("departements-grand-est.geojson"):
        dessiner(ax, dep.boundary, color="#bbbbbb", lw=0.6)
    for reg in contours("region-grand-est.geojson"):
        dessiner(ax, reg.boundary, color="#555555", lw=1)
    for i, trace in enumerate(traces):
        if i in depart:
            continue
        if i in bassin:
            style = dict(color="#2b7bb9", lw=0.7)
        elif i in perdus:
            style = dict(color="#e08a00", lw=1.2)
        elif i in passages:
            style = dict(color="#2b7bb9", lw=1.2, ls=(0, (2, 1)))
        elif i in ouvrages:
            style = dict(color="#d6452b", lw=1.2)
        elif i in exclus:
            style = dict(color="#7a4fa0", lw=1.5)
        else:
            style = dict(color="#d5dde3", lw=0.4)
        dessiner(ax, trace, **style)
    for i in depart:
        dessiner(ax, traces[i], color="#0b3d66", lw=2.2)
    legende = [
        ("#0b3d66", "Moselle et Moselle canalisée"),
        ("#2b7bb9", "bassin de la Moselle retenu"),
        ("#d6452b", "canaux et rigoles exclus"),
        ("#2b7bb9", "canaux et rigoles traversés (pointillés)"),
        ("#e08a00", "non retenus (atteints seulement par un canal ou une rigole)"),
        ("#7a4fa0", "la Sarre (exclue)"),
        ("#d5dde3", "autres cours d'eau"),
    ]
    for couleur, texte in legende:
        tirets = (0, (2, 1)) if "pointillés" in texte else "-"
        ax.plot([], [], color=couleur, lw=2, ls=tirets, label=texte)
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.set_title(f"Bassin de la Moselle dans le Grand Est : {len(bassin)} tracés")
    ax.set_aspect("equal")
    ax.axis("off")
    SORTIE_CARTE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SORTIE_CARTE, bbox_inches="tight")
    print(f"Fichiers écrits : {SORTIE_CSV.relative_to(RACINE)}, "
          f"{SORTIE_JOURNAL.relative_to(RACINE)}, {SORTIE_CARTE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
