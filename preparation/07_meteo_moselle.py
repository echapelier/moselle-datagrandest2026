"""Étape 7 : température, pluie et neige le long de la Moselle.

Données des graphiques météo de la Dataviz, pour les 12 sites du profil des
débits (étape 6) :

  1. Pour chaque semaine, moyenne des 12 sites de :
       temp   température moyenne hebdomadaire (°C) ;
       pluie  hauteur de pluie, cumul hebdomadaire (mm) ;
       neige  équivalent en eau des précipitations solides (neige, grêle),
              cumul hebdomadaire (mm).
     Le script s'arrête si une de ces valeurs manque pour l'un des sites :
     la moyenne ne porterait alors pas sur les mêmes sites chaque semaine.
  2. Valeurs de référence, pour repérer les écarts à l'habituel : pour
     chaque semaine de l'année (numéro de semaine ISO, de 1 à 52), moyenne
     des valeurs hebdomadaires de cette semaine sur toutes les années du jeu
     de données (2000 à 2026). La semaine 53, qui n'existe que certaines
     années, est regroupée avec la semaine 52.

Contrôle : la référence d'une semaine de l'année, calculée comme moyenne
des moyennes hebdomadaires, est égale à la moyenne directe de toutes les
mesures (sites × années) de cette semaine de l'année (possible parce que
chaque semaine compte les 12 sites).

Entrées : src/data/profil_sites.csv (les 12 sites, étape 6)
          src/data/mesures.csv (étape 4)
Sorties : src/data/meteo_semaines.csv
          preparation/journaux/07_meteo_moselle.txt

Lancement, depuis la racine du projet :
    uv run preparation/07_meteo_moselle.py
"""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ENTREE_SITES = RACINE / "src" / "data" / "profil_sites.csv"
ENTREE_MESURES = RACINE / "src" / "data" / "mesures.csv"
SORTIE = RACINE / "src" / "data" / "meteo_semaines.csv"
SORTIE_JOURNAL = RACINE / "preparation" / "journaux" / "07_meteo_moselle.txt"

VARIABLES = ["temp", "pluie", "neige"]
TOLERANCE = 1e-9


def arreter(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def semaine_de_l_annee(semaine: str) -> int:
    """Numéro de semaine ISO (« 2004W53 » → 53), la 53 regroupée avec la 52."""
    return min(int(semaine.split("W")[1]), 52)


def main() -> None:
    with ENTREE_SITES.open(encoding="utf-8", newline="") as f:
        sites = [r["site"] for r in csv.DictReader(f)]
    if len(sites) != 12:
        arreter(f"{len(sites)} sites dans profil_sites.csv, 12 attendus")

    # Valeurs par semaine et par site ; arrêt sur la première valeur vide.
    valeurs = defaultdict(dict)  # semaine → site → {variable: valeur}
    dates = {}
    with ENTREE_MESURES.open(encoding="utf-8", newline="") as f:
        for m in csv.DictReader(f):
            if m["site"] not in sites:
                continue
            vides = [v for v in VARIABLES if m[v] == ""]
            if vides:
                arreter(f"valeur vide ({', '.join(vides)}) pour le site {m['site']}, semaine {m['semaine']}")
            valeurs[m["semaine"]][m["site"]] = {v: float(m[v]) for v in VARIABLES}
            dates[m["semaine"]] = m["date"]
    semaines = sorted(valeurs)
    incompletes = [w for w in semaines if len(valeurs[w]) != len(sites)]
    if incompletes:
        arreter(f"semaines sans les 12 sites : {incompletes[:5]}")

    # 1. Moyennes hebdomadaires des 12 sites.
    moyennes = {w: {v: statistics.fmean(valeurs[w][s][v] for s in sites) for v in VARIABLES} for w in semaines}

    # 2. Références par semaine de l'année.
    par_semaine_annee = defaultdict(list)
    for w in semaines:
        par_semaine_annee[semaine_de_l_annee(w)].append(w)
    references = {
        n: {v: statistics.fmean(moyennes[w][v] for w in liste) for v in VARIABLES}
        for n, liste in par_semaine_annee.items()
    }
    if sorted(references) != list(range(1, 53)):
        arreter(f"semaines de l'année manquantes : {sorted(set(range(1, 53)) - set(references))}")

    # Contrôle : moyenne directe de toutes les mesures de la semaine de l'année.
    for n, liste in par_semaine_annee.items():
        for v in VARIABLES:
            directe = statistics.fmean(valeurs[w][s][v] for w in liste for s in sites)
            if abs(directe - references[n][v]) > TOLERANCE:
                arreter(f"référence de la semaine {n} ({v}) : {references[n][v]} au lieu de {directe}")

    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        e = csv.writer(f, lineterminator="\n")
        e.writerow(["semaine", "date", "semaine_annee", *VARIABLES, *(f"{v}_ref" for v in VARIABLES)])
        for w in semaines:
            n = semaine_de_l_annee(w)
            e.writerow([w, dates[w], n, *(f"{moyennes[w][v]:.3f}" for v in VARIABLES),
                        *(f"{references[n][v]:.3f}" for v in VARIABLES)])

    nb_annees = {n: len(liste) for n, liste in par_semaine_annee.items()}
    def etendue(v, source):
        donnees = [x[v] for x in source.values()]
        return f"{min(donnees):.1f} à {max(donnees):.1f}"
    resume = [
        f"Sites : {len(sites)} (sites du profil des débits)",
        f"Semaines : {len(semaines)} ({semaines[0]} à {semaines[-1]}), aucune valeur vide",
        f"Années par semaine de l'année : {min(nb_annees.values())} à {max(nb_annees.values())} "
        f"(semaine 52 : {nb_annees[52]}, dont les semaines 53)",
        "Moyennes hebdomadaires des 12 sites :",
        *(f"  {v:<6} {etendue(v, moyennes)}" for v in VARIABLES),
        "Références par semaine de l'année :",
        *(f"  {v:<6} {etendue(v, references)}" for v in VARIABLES),
        "Contrôle : références égales aux moyennes directes de toutes les mesures (sites × années).",
    ]
    SORTIE_JOURNAL.write_text("\n".join(resume) + "\n", encoding="utf-8")
    print("\n".join(resume))
    print(f"Fichier écrit : {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
