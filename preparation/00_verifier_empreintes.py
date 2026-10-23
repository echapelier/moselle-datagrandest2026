"""Étape 0 : vérifier que les fichiers d'origine sont bien ceux attendus.

Compare l'empreinte SHA-256 de chaque fichier de donnees-originales/ à celle
notée dans preparation/empreintes.sha256. S'arrête avec un message clair
(code de sortie 1) si un fichier manque ou diffère.

Lancement, depuis la racine du projet :
    uv run preparation/00_verifier_empreintes.py
"""

import hashlib
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_ORIGINES = RACINE / "donnees-originales"
FICHIER_EMPREINTES = RACINE / "preparation" / "empreintes.sha256"


def sha256(chemin: Path) -> str:
    """Calcule l'empreinte SHA-256 d'un fichier, lu par blocs de 1 Mo."""
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def main() -> None:
    erreurs = []
    for ligne in FICHIER_EMPREINTES.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        attendue, nom = ligne.split(maxsplit=1)
        chemin = DOSSIER_ORIGINES / nom
        if not chemin.exists():
            erreurs.append(f"MANQUANT : {chemin}")
            continue
        obtenue = sha256(chemin)
        if obtenue == attendue:
            print(f"OK         {nom}")
        else:
            erreurs.append(f"DIFFÉRENT : {nom}\n  attendue {attendue}\n  obtenue  {obtenue}")

    if erreurs:
        print("\n".join(erreurs), file=sys.stderr)
        print(
            "\nLes fichiers d'origine ne correspondent pas à ceux de référence "
            "(voir README, section « Données d'origine »). Arrêt.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("Tous les fichiers d'origine sont conformes.")


if __name__ == "__main__":
    main()
