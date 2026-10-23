"""Étape 2 : rechercher les cours d'eau du bassin de la Moselle.

Seul le fichier des cours d'eau est utilisé : toutes les décisions sont
calculées à partir du tracé, sans autre source.

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
     de 1 m du tracé de B. B est alors un « récepteur » de A.
  4. On part de la Moselle et de la Moselle canalisée, puis on remonte :
     on ajoute tout tracé qui se termine sur un tracé déjà retenu, et ainsi
     de suite (parcours en largeur). On ne fait que remonter : un tracé
     sur lequel se termine un cours d'eau du bassin n'est pas ajouté.
     Sont exclus : la Sarre (et donc son sous-bassin, qui n'est atteint que
     par elle) et les « ouvrages », c'est-à-dire les tracés dont le nom
     contient « canal » ou « rigole », parce qu'ils peuvent relier des
     bassins entre eux. Les « bras » sont gardés.
  5. Ouvrages traversés : certains ruisseaux n'atteignent le bassin que par
     un ouvrage. Pour chaque ouvrage qui touche le bassin, on regarde les
     cours d'eau qu'il apporterait (ceux qui le remontent). Si aucun d'eux
     ne se termine aussi sur un cours d'eau extérieur au bassin, l'ouvrage
     est traversé et ces cours d'eau sont ajoutés ; sinon, il est refusé.
     L'opération est répétée jusqu'à ce que plus rien ne change (un ouvrage
     traversé peut en faire toucher un autre). Les ouvrages eux-mêmes ne
     font pas partie du résultat.

Contrôles
---------
  - la Moselle, la Moselle canalisée et la Sarre existent chacune une fois ;
  - bassins voisins : on cherche tous les « exutoires », c'est-à-dire les
    cours d'eau qui ne se terminent sur aucun autre (ils sortent de la
    région ou se perdent). Pour chacun, hors bassin de la Moselle, on
    remonte son bassin de la même façon : aucun ne doit avoir de tracé en
    commun avec le bassin de la Moselle ;
  - le journal liste chaque ouvrage examiné, la décision et sa raison.

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
from collections import deque
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import linemerge, nearest_points

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

VERS_LAMBERT93 = Transformer.from_crs("OGC:CRS84", "EPSG:2154", always_xy=True)
VERS_LONLAT = Transformer.from_crs("EPSG:2154", "OGC:CRS84", always_xy=True)


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

    def nom(i: int) -> str:
        return noms[i] or "(sans nom)"

    for n in DEPARTS + EXCLUS:
        if len(indices(n)) != 1:
            arreter(f"« {n} » devrait exister exactement une fois ({len(indices(n))} trouvés)")
    depart = [i for n in DEPARTS for i in indices(n)]
    exclus = {i for n in EXCLUS for i in indices(n)}

    def est_ouvrage(i: int) -> bool:
        return bool(noms[i] and OUVRAGES.search(noms[i]))

    # « affluents[j] » = tracés qui se terminent sur j ;
    # « recepteurs[i] » = tracés sur lesquels i se termine.
    index = shapely.STRtree(traces)
    affluents = {i: set() for i in range(len(traces))}
    recepteurs = {i: set() for i in range(len(traces))}
    nb_contacts = 0
    for i, trace in enumerate(traces):
        for point in extremites(trace):
            for j in index.query(point, predicate="dwithin", distance=TOLERANCE_M):
                j = int(j)
                if j != i:
                    affluents[j].add(i)
                    recepteurs[i].add(j)
                    nb_contacts += 1
    print(f"{nb_contacts} contacts extrémité → tracé (tolérance {TOLERANCE_M} m)")

    # Étape 4 du principe : remontée sans traverser les ouvrages.
    bassin, recepteur = remonter(depart, affluents, lambda i: i in exclus or est_ouvrage(i))
    nb_sans_ouvrage = len(bassin)

    # Étape 5 du principe : ouvrages traversés, jusqu'à stabilité.
    traverses, refuses, apports = [], {}, {}
    change = True
    while change:
        change = False
        touches = {a for b in bassin | set(traverses) for a in affluents[b]}
        for o in sorted((a for a in touches if est_ouvrage(a) and a not in traverses),
                        key=lambda i: (nom(i), codes[i])):
            amont, rec = remonter(
                [o], affluents, lambda i: i in bassin or i in exclus or est_ouvrage(i)
            )
            amont -= {o}
            fuites = sorted(
                (nom(u), nom(r)) for u in amont for r in recepteurs[u]
                if not est_ouvrage(r) and r not in bassin and r not in amont
            )
            if fuites:
                refuses[o] = (amont, fuites)
                continue
            refuses.pop(o, None)
            traverses.append(o)
            apports[o] = amont
            bassin |= amont
            recepteur.update(rec)
            change = True

    # Contrôle : aucun tracé commun avec les autres bassins (calculés à
    # partir de tous les exutoires hors bassin, sans traverser d'ouvrage).
    exutoires = [
        i for i in range(len(traces))
        if i not in bassin and not est_ouvrage(i)
        and not any(not est_ouvrage(r) for r in recepteurs[i])
    ]
    autres = []
    for e in exutoires:
        voisin, _ = remonter([e], affluents, lambda i: est_ouvrage(i))
        commun = voisin & bassin
        if commun:
            arreter(f"le bassin de la Moselle recouvre celui de « {nom(e)} » : "
                    f"{sorted(nom(i) for i in commun)[:10]}")
        autres.append((len(voisin), nom(e)))
    autres.sort(reverse=True)

    # Sortie CSV : un tracé par ligne, avec celui sur lequel il se termine.
    SORTIE_CSV.parent.mkdir(exist_ok=True)
    with SORTIE_CSV.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.writer(f, lineterminator="\n")
        ecrivain.writerow(["CdOH", "TopoOH", "recepteur_CdOH", "recepteur_TopoOH"])
        for i in sorted(bassin, key=lambda i: codes[i]):
            r = recepteur.get(i)
            ecrivain.writerow([codes[i], noms[i] or "", codes[r] if r is not None else "",
                               (noms[r] or "") if r is not None else ""])

    # Journal.
    def position(o: int) -> str:
        """Longitude, latitude du point où l'ouvrage touche le bassin."""
        voisins = [b for b in bassin | set(traverses) if o in affluents[b]]
        p = nearest_points(traces[o], shapely.union_all([traces[b] for b in voisins]))[0]
        lon, lat = VERS_LONLAT.transform(p.x, p.y)
        return f"{lon:.3f}, {lat:.3f}"

    perdus = set().union(*(amont for amont, _ in refuses.values())) if refuses else set()
    resume = [
        f"Tracés lus : {len(objets)}",
        f"Contacts extrémité → tracé : {nb_contacts}",
        f"Tracés retenus sans traverser d'ouvrage : {nb_sans_ouvrage}",
        f"Ouvrages traversés : {len(traverses)} (apportant {len(bassin) - nb_sans_ouvrage} tracés)",
        f"Ouvrages refusés : {len(refuses)} ({len(perdus)} tracés non retenus)",
        f"Tracés du bassin de la Moselle (Moselle et Moselle canalisée comprises) : {len(bassin)}",
        f"  noms distincts : {len({noms[i] for i in bassin if noms[i]})}",
        "",
    ]
    journal = ["Ouvrages traversés (position du contact avec le bassin en longitude, latitude)"]
    for o in sorted(traverses, key=lambda i: nom(i)):
        apportes = sorted(nom(i) for i in apports[o])
        journal.append(f"  {nom(o)} [{position(o)}] : {len(apportes)} tracés"
                       + (f" : {'; '.join(apportes)}" if apportes else ""))
    journal.append("")
    journal.append("Ouvrages refusés (un cours d'eau apporté se termine aussi hors du bassin)")
    for o, (amont, fuites) in sorted(refuses.items(), key=lambda kv: nom(kv[0])):
        journal.append(f"  {nom(o)} [{position(o)}] : {len(amont)} tracés non retenus : "
                       f"{'; '.join(sorted(nom(i) for i in amont))}")
        for u, r in fuites:
            journal.append(f"    raison : « {u} » se termine aussi sur « {r} »")
    journal.append("")
    journal.append(f"Contrôle : {len(exutoires)} exutoires hors bassin, bassins remontés "
                   "sans traverser d'ouvrage ; aucun tracé en commun avec la Moselle.")
    journal.append("Les dix plus grands :")
    for taille, n in autres[:10]:
        journal.append(f"  {n:<30} {taille:>5} tracés")
    SORTIE_JOURNAL.parent.mkdir(exist_ok=True)
    SORTIE_JOURNAL.write_text("\n".join(resume + journal) + "\n", encoding="utf-8")
    print("\n".join(resume))

    # Carte de contrôle.
    def dessiner(ax, geometrie, **style):
        lignes = geometrie.geoms if hasattr(geometrie, "geoms") else [geometrie]
        for ligne in lignes:
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
    tirets = (0, (2, 1))
    for i, trace in enumerate(traces):
        if i in depart:
            continue
        if i in bassin:
            style = dict(color="#2b7bb9", lw=0.7)
        elif i in traverses:
            style = dict(color="#2b7bb9", lw=1.2, ls=tirets)
        elif i in perdus:
            style = dict(color="#e08a00", lw=1.2)
        elif i in refuses:
            style = dict(color="#d6452b", lw=1.2)
        elif i in exclus:
            style = dict(color="#7a4fa0", lw=1.5)
        else:
            style = dict(color="#d5dde3", lw=0.4)
        dessiner(ax, trace, **style)
    for i in depart:
        dessiner(ax, traces[i], color="#0b3d66", lw=2.2)
    legende = [
        ("#0b3d66", "-", "Moselle et Moselle canalisée"),
        ("#2b7bb9", "-", "bassin de la Moselle retenu"),
        ("#2b7bb9", tirets, "canaux et rigoles traversés"),
        ("#d6452b", "-", "canaux et rigoles refusés"),
        ("#e08a00", "-", "non retenus (atteints seulement par un ouvrage refusé)"),
        ("#7a4fa0", "-", "la Sarre (exclue)"),
        ("#d5dde3", "-", "autres cours d'eau"),
    ]
    for couleur, style_trait, texte in legende:
        ax.plot([], [], color=couleur, lw=2, ls=style_trait, label=texte)
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
