import hashlib
import json
from pathlib import Path

import pandas as pd


def empreinte(chemin):
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()[:16]


def lire_curseur(chemin):
    fichier = Path(chemin)
    if not fichier.exists():
        return {"dernier_lot": -1, "lots_ingeres": []}
    return json.loads(fichier.read_text(encoding="utf-8"))


def ecrire_curseur(chemin, curseur):
    fichier = Path(chemin)
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(json.dumps(curseur, indent=2), encoding="utf-8")


def lister_lots(dossier):
    return sorted(Path(dossier).glob("lot_*.csv"))


def ingerer(config):
    donnees = config["donnees"]
    lots = lister_lots(donnees["dossier_lots"])
    if not lots:
        raise FileNotFoundError(f"aucun lot dans {donnees['dossier_lots']}")

    curseur = lire_curseur(donnees["curseur"])
    rang = curseur["dernier_lot"] + 1
    if rang >= len(lots):
        raise IndexError("tous les lots ont deja ete rejoues")

    chemin = lots[rang]
    lot = pd.read_csv(chemin)
    print(f"lot {chemin.name} : {len(lot)} lignes")
    return {
        "rang": rang,
        "nom": chemin.name,
        "chemin": str(chemin),
        "lignes": len(lot),
        "empreinte": empreinte(chemin),
        "donnees": lot,
    }


def promouvoir(lot, config):
    donnees = config["donnees"]
    cible = Path(donnees["dataset_courant"])
    cible.parent.mkdir(parents=True, exist_ok=True)

    if cible.exists():
        dataset = pd.concat([pd.read_csv(cible), lot["donnees"]])
    else:
        dataset = lot["donnees"].copy()
    dataset = dataset.drop_duplicates(subset="dteday").sort_values("dteday").reset_index(drop=True)
    dataset.to_csv(cible, index=False)

    curseur = lire_curseur(donnees["curseur"])
    curseur["dernier_lot"] = lot["rang"]
    curseur["lots_ingeres"] = curseur.get("lots_ingeres", []) + [lot["nom"]]
    ecrire_curseur(donnees["curseur"], curseur)

    print(f"dataset courant : {len(dataset)} lignes")
    return {
        "donnees": dataset,
        "chemin": str(cible),
        "lignes": len(dataset),
        "empreinte": empreinte(cible),
    }
