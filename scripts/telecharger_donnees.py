import io
import sys
import zipfile
from pathlib import Path

import requests

URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
FICHIER = "day.csv"
DESTINATION = Path("data/brut")


def telecharger(url=URL, destination=DESTINATION):
    destination.mkdir(parents=True, exist_ok=True)
    cible = destination / FICHIER
    if cible.exists():
        print(f"deja present : {cible}")
        return cible
    print(f"telechargement depuis {url}")
    reponse = requests.get(url, timeout=120)
    reponse.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(reponse.content)) as archive:
        cible.write_bytes(archive.read(FICHIER))
    print(f"ecrit : {cible} ({cible.stat().st_size} octets)")
    return cible


if __name__ == "__main__":
    try:
        telecharger()
    except Exception as erreur:
        print(f"echec du telechargement : {erreur}")
        sys.exit(1)
