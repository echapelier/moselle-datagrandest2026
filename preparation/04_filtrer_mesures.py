"""Étape 4 : ne garder que les sites de la Moselle, en trois fichiers.

Les lignes de donnees.csv (nettoyé à l'étape 1) dont le site est rattaché
(étape 3) au tracé de la Moselle ou de la Moselle canalisée sont réparties en
trois fichiers, pour ne pas répéter à chaque semaine ce qui ne change pas.
Les sites des affluents ne servent ni aux calculs ni à l'affichage : ils ne
sont pas gardés.

  sites.csv     une ligne par site : libellés, commune, département,
                coordonnées, indicateur d'étiage, et le tracé rattaché
                à l'étape 3 (CdOH, TopoOH, distance) ;
  cours_eau.csv une ligne par cours d'eau : code, URI, libellé ;
  mesures.csv   une ligne par site et par semaine : semaine, date, et les
                mesures (temp, pluie, neige, debit, humidite).

Jointures : mesures.site → sites.site, sites.code_cours_eau →
cours_eau.code_cours_eau. Les fichiers sont lus et écrits en texte : les
valeurs restent exactement celles de l'étape 1 (zéros initiaux compris).

Contrôles
---------
  - les colonnes de sites.csv sont constantes pour chaque site, celles de
    cours_eau.csv pour chaque code de cours d'eau ;
  - chaque site a une ligne par semaine, sans doublon ;
  - jointure complète : en recollant les trois fichiers, on retrouve
    exactement les lignes de l'étape 1 pour les sites retenus.

Entrées : donnees-intermediaires/01_donnees_nettoyees.csv (étape 1)
          donnees-intermediaires/03_sites_rattaches.csv (étape 3)
Sorties : src/data/sites.csv, src/data/cours_eau.csv, src/data/mesures.csv
          (versionnées : ce sont les données de l'application)

Lancement, depuis la racine du projet :
    uv run preparation/04_filtrer_mesures.py
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ENTREE_MESURES = RACINE / "donnees-intermediaires" / "01_donnees_nettoyees.csv"
ENTREE_SITES = RACINE / "donnees-intermediaires" / "03_sites_rattaches.csv"
SORTIES = RACINE / "src" / "data"

TRACES_MOSELLE = {"la Moselle", "la Moselle Canalisée"}

COLONNES_SITES = ["site", "libelle_site", "code_cours_eau", "libelle_commune", "commune",
                  "dept", "libelle_dept", "lat", "lon", "etiage"]
COLONNES_RATTACHEMENT = ["CdOH", "TopoOH", "distance_m"]
COLONNES_COURS_EAU = ["code_cours_eau", "uri_cours_eau", "libelle_cours_eau"]
COLONNES_MESURES = ["semaine", "site", "temp", "pluie", "neige", "debit", "humidite", "date"]


def arreter(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def ecrire(nom: str, colonnes: list[str], lignes: list[dict]) -> None:
    with (SORTIES / nom).open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=colonnes, lineterminator="\n")
        ecrivain.writeheader()
        ecrivain.writerows(lignes)


def main() -> None:
    with ENTREE_SITES.open(encoding="utf-8", newline="") as f:
        lignes_sites = list(csv.DictReader(f))
    rattachement = {r["site"]: r for r in lignes_sites
                    if r["dans_bassin"] == "1" and r["TopoOH"] in TRACES_MOSELLE}
    print(f"Sites du bassin (étape 3) : {sum(1 for r in lignes_sites if r['dans_bassin'] == '1')}, "
          f"dont sur la Moselle : {len(rattachement)}")

    with ENTREE_MESURES.open(encoding="utf-8", newline="") as f:
        lecteur = csv.DictReader(f)
        colonnes_origine = lecteur.fieldnames
        retenues = [ligne for ligne in lecteur if ligne["site"] in rattachement]
    print(f"Lignes retenues : {len(retenues)}")

    # Une ligne par site et par cours d'eau, avec contrôle de constance.
    sites, cours_eau = {}, {}
    for ligne in retenues:
        for table, cle, colonnes in ((sites, "site", COLONNES_SITES),
                                     (cours_eau, "code_cours_eau", COLONNES_COURS_EAU)):
            valeurs = {c: ligne[c] for c in colonnes}
            deja = table.setdefault(ligne[cle], valeurs)
            if deja != valeurs:
                arreter(f"valeurs non constantes pour {cle} = {ligne[cle]} : {deja} / {valeurs}")
    for site, valeurs in sites.items():
        valeurs.update({c: rattachement[site][c] for c in COLONNES_RATTACHEMENT})
    if set(sites) != set(rattachement):
        arreter(f"sites sans aucune ligne de mesure : {sorted(set(rattachement) - set(sites))}")

    # Une ligne par site et par semaine.
    semaines = sorted({ligne["semaine"] for ligne in retenues})
    par_site = defaultdict(list)
    for ligne in retenues:
        par_site[ligne["site"]].append(ligne["semaine"])
    for site, liste in par_site.items():
        if sorted(liste) != semaines:
            arreter(f"le site {site} n'a pas exactement une ligne par semaine")

    mesures = [{c: ligne[c] for c in COLONNES_MESURES} for ligne in retenues]

    SORTIES.mkdir(parents=True, exist_ok=True)
    ecrire("sites.csv", COLONNES_SITES + COLONNES_RATTACHEMENT,
           sorted(sites.values(), key=lambda s: s["site"]))
    ecrire("cours_eau.csv", COLONNES_COURS_EAU,
           sorted(cours_eau.values(), key=lambda c: c["code_cours_eau"]))
    ecrire("mesures.csv", COLONNES_MESURES, mesures)

    # Contrôle par jointure complète, à partir des fichiers écrits.
    def lire(nom: str) -> list[dict]:
        with (SORTIES / nom).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    sites_lus = {s["site"]: s for s in lire("sites.csv")}
    cours_lus = {c["code_cours_eau"]: c for c in lire("cours_eau.csv")}
    recollees = []
    for m in lire("mesures.csv"):
        s = sites_lus[m["site"]]
        c = cours_lus[s["code_cours_eau"]]
        complete = {**m, **{k: s[k] for k in COLONNES_SITES}, **c}
        recollees.append([complete[col] for col in colonnes_origine])
    attendues = [[ligne[col] for col in colonnes_origine] for ligne in retenues]
    if recollees != attendues:
        arreter("la jointure des trois fichiers ne redonne pas les lignes d'origine")

    print(f"Semaines : {len(semaines)} ({semaines[0]} à {semaines[-1]})")
    print(f"sites.csv : {len(sites)} lignes ; cours_eau.csv : {len(cours_eau)} lignes ; "
          f"mesures.csv : {len(mesures)} lignes")
    print(f"Contrôle : la jointure des trois fichiers redonne les {len(attendues)} lignes d'origine.")
    for nom in ("sites.csv", "cours_eau.csv", "mesures.csv"):
        taille = (SORTIES / nom).stat().st_size
        print(f"  {nom} : {taille / 1e6:.2f} Mo")


if __name__ == "__main__":
    main()
