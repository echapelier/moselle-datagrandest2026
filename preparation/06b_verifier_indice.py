"""Contrôle de l'étape 6 : recalculer l'indice des semaines autrement.

Le calcul est refait avec numpy, sous forme de tableau semaines × sites
retenus, indépendamment du script 06, puis comparé à
src/data/profil_semaines.csv :
nombre de sites par semaine, indice (à l'arrondi près du fichier, 6
décimales), nombre de débits nuls remplacés par le plancher, et semaines
du maximum et du minimum. Le plancher de chaque site (moitié de son plus
petit débit strictement positif) est recalculé ici à partir des mesures.

Lancement, depuis la racine du projet (après le script 06) :
    uv run preparation/06b_verifier_indice.py
"""

import csv
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "src" / "data"
TOLERANCE = 1e-6


def main() -> None:
    with (DONNEES / "profil_sites.csv").open(encoding="utf-8", newline="") as f:
        sites = [r["site"] for r in csv.DictReader(f) if r["retenu_calcul"] == "1"]
    with (DONNEES / "mesures.csv").open(encoding="utf-8", newline="") as f:
        mesures = list(csv.DictReader(f))
    semaines = sorted({m["semaine"] for m in mesures})
    col = {s: j for j, s in enumerate(sites)}
    lig = {w: i for i, w in enumerate(semaines)}

    # Tableau des débits valides (>= 0, zéros compris), NaN ailleurs.
    debits = np.full((len(semaines), len(sites)), np.nan)
    for m in mesures:
        if m["site"] in col and m["debit"] != "" and float(m["debit"]) >= 0:
            debits[lig[m["semaine"]], col[m["site"]]] = float(m["debit"])

    medianes = np.nanmedian(debits, axis=0)
    nb_sites = (~np.isnan(debits)).sum(axis=1)
    # Plancher par site pour le logarithme : moitié du plus petit débit > 0.
    planchers = np.nanmin(np.where(debits > 0, debits, np.nan), axis=0) / 2
    nb_planchers = (debits == 0).sum(axis=1)
    with np.errstate(invalid="ignore"):
        rapports = np.fmax(debits, planchers) / np.maximum(medianes, planchers)
        rapports[np.isnan(debits)] = np.nan
        indice = np.exp(np.nanmean(np.log(rapports), axis=1))
    completes = nb_sites == len(sites)

    with (DONNEES / "profil_semaines.csv").open(encoding="utf-8", newline="") as f:
        fichier = list(csv.DictReader(f))
    erreurs = []
    for i, w in enumerate(fichier):
        if w["semaine"] != semaines[i] or int(w["nb_sites"]) != nb_sites[i]:
            erreurs.append(f"{w['semaine']} : nombre de sites différent")
        elif int(w["nb_planchers"]) != nb_planchers[i]:
            erreurs.append(f"{w['semaine']} : nombre de planchers différent")
        elif w["indice"] and abs(float(w["indice"]) - indice[i]) > TOLERANCE:
            erreurs.append(f"{w['semaine']} : indice {w['indice']} au lieu de {indice[i]:.6f}")
    haut = semaines[int(np.nanargmax(np.where(completes, indice, np.nan)))]
    bas = semaines[int(np.nanargmin(np.where(completes, indice, np.nan)))]
    classees = [w for w in fichier if w["classee"] == "1"]
    haut_f = max(classees, key=lambda w: float(w["indice"]))["semaine"]
    bas_f = min(classees, key=lambda w: float(w["indice"]))["semaine"]
    if (haut, bas) != (haut_f, bas_f):
        erreurs.append(f"semaines extrêmes : {haut}/{bas} au lieu de {haut_f}/{bas_f}")

    if erreurs:
        print("\n".join(erreurs), file=sys.stderr)
        sys.exit(1)
    ecart = max(abs(float(w["indice"]) - indice[i]) for i, w in enumerate(fichier) if w["indice"])
    print(f"Contrôle réussi sur {len(fichier)} semaines : écart maximal {ecart:.1e}, "
          f"maximum {haut}, minimum {bas}, {int(nb_planchers.sum())} débits nuls remplacés par le plancher.")


if __name__ == "__main__":
    main()
