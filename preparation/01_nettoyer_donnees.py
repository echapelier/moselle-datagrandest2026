"""Étape 1 : premier nettoyage de donnees.csv.

Deux corrections, rien d'autre :
  1. la colonne « crue » est abandonnée (elle vaut 1 sur toutes les lignes) ;
  2. pour les Ardennes, le zéro initial perdu est rétabli :
     dept « 8 » → « 08 », commune « 8xxx » → « 08xxx ».

Le fichier est lu et écrit en texte (module csv, sans typage automatique),
pour que les autres valeurs restent exactement celles d'origine.
Les débits nuls ou à -1 ne sont pas modifiés ici : ils sont traités
au moment des calculs.

Entrée  : donnees-originales/donnees.csv
Sortie  : donnees-intermediaires/01_donnees_nettoyees.csv (non versionnée)

Lancement, depuis la racine du projet :
    uv run preparation/01_nettoyer_donnees.py
"""

import csv
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ENTREE = RACINE / "donnees-originales" / "donnees.csv"
SORTIE = RACINE / "donnees-intermediaires" / "01_donnees_nettoyees.csv"

COLONNE_ABANDONNEE = "crue"
LIBELLE_ARDENNES = "ARDENNES"
NB_LIGNES_ATTENDU = 370_538


def arreter(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    SORTIE.parent.mkdir(exist_ok=True)
    compteurs = Counter()

    with (
        ENTREE.open(encoding="utf-8", newline="") as f_entree,
        SORTIE.open("w", encoding="utf-8", newline="") as f_sortie,
    ):
        lecteur = csv.DictReader(f_entree)
        colonnes = [c for c in lecteur.fieldnames if c != COLONNE_ABANDONNEE]
        ecrivain = csv.DictWriter(
            f_sortie, fieldnames=colonnes, extrasaction="ignore", lineterminator="\n"
        )
        ecrivain.writeheader()

        for ligne in lecteur:
            compteurs["lignes"] += 1

            # La colonne abandonnée doit bien être constante à 1.
            if ligne[COLONNE_ABANDONNEE] != "1":
                arreter(f"« crue » vaut {ligne[COLONNE_ABANDONNEE]!r} (ligne {compteurs['lignes']})")

            if ligne["libelle_dept"] == LIBELLE_ARDENNES:
                # On vérifie la forme attendue avant de corriger, pour ne
                # jamais ajouter un zéro à une valeur déjà correcte.
                if ligne["dept"] != "8" or len(ligne["commune"]) != 4 or not ligne["commune"].startswith("8"):
                    arreter(f"forme inattendue pour les Ardennes : dept={ligne['dept']!r}, commune={ligne['commune']!r}")
                ligne["dept"] = "0" + ligne["dept"]
                ligne["commune"] = "0" + ligne["commune"]
                compteurs["lignes corrigées (Ardennes)"] += 1

            # Après correction, tous les codes doivent avoir leur longueur normale.
            if len(ligne["dept"]) != 2 or len(ligne["commune"]) != 5:
                arreter(f"code mal formé : dept={ligne['dept']!r}, commune={ligne['commune']!r}")

            ecrivain.writerow(ligne)

    if compteurs["lignes"] != NB_LIGNES_ATTENDU:
        arreter(f"{compteurs['lignes']} lignes lues, {NB_LIGNES_ATTENDU} attendues")

    print(f"Colonnes conservées ({len(colonnes)}) : {', '.join(colonnes)}")
    for nom, valeur in compteurs.items():
        print(f"{nom} : {valeur:,}".replace(",", " "))
    print(f"Fichier écrit : {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
