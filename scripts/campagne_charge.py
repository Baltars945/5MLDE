import argparse
import csv
import json
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import psutil

DOSSIER = "rapports/charge"


def attendre_api(port, delai=120):
    limite = time.time() + delai
    while time.time() < limite:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/ready", timeout=3) as reponse:
                if reponse.status == 200:
                    return True
        except OSError:
            time.sleep(1)
    raise TimeoutError(f"api pas prete sur le port {port}")


def demarrer_api(workers, port):
    processus = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "scripts.lancer_api",
            "--workers",
            str(workers),
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    attendre_api(port)
    print(f"api demarree avec {workers} worker(s) sur le port {port}")
    return processus


def arreter(processus):
    parent = psutil.Process(processus.pid)
    for enfant in parent.children(recursive=True):
        enfant.terminate()
    parent.terminate()
    processus.wait(timeout=30)


class Sonde(threading.Thread):
    def __init__(self, pid):
        super().__init__(daemon=True)
        self.racine = psutil.Process(pid)
        self.suivis = {pid: self.racine}
        self.cpu = []
        self.memoire = []
        self.actif = True

    def recenser(self):
        try:
            for processus in self.racine.children(recursive=True):
                self.suivis.setdefault(processus.pid, processus)
        except psutil.Error:
            pass

    def run(self):
        while self.actif:
            self.recenser()
            cpu = 0.0
            memoire = 0
            for identifiant, processus in list(self.suivis.items()):
                try:
                    cpu += processus.cpu_percent(interval=None)
                    memoire += processus.memory_info().rss
                except psutil.Error:
                    self.suivis.pop(identifiant, None)
            self.cpu.append(cpu)
            self.memoire.append(memoire)
            time.sleep(1)

    def resume(self):
        self.actif = False
        utiles = self.cpu[1:] or [0.0]
        return {
            "cpu_moyen_pourcent": round(statistics.mean(utiles), 1),
            "cpu_max_pourcent": round(max(utiles), 1),
            "memoire_max_mo": round(max(self.memoire or [0]) / 1024 / 1024, 1),
        }


def lire_stats(prefixe):
    with open(f"{prefixe}_stats.csv", newline="", encoding="utf-8") as fichier:
        lignes = list(csv.DictReader(fichier))
    total = next(ligne for ligne in lignes if ligne["Name"] == "Aggregated")
    return {
        "requetes": int(total["Request Count"]),
        "echecs": int(total["Failure Count"]),
        "requetes_par_seconde": round(float(total["Requests/s"]), 1),
        "p50_ms": round(float(total["50%"]), 1),
        "p95_ms": round(float(total["95%"]), 1),
        "max_ms": round(float(total["Max Response Time"]), 1),
    }


def jouer_palier(utilisateurs, duree, port, prefixe):
    commande = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        "locustfile.py",
        "--headless",
        "--host",
        f"http://127.0.0.1:{port}",
        "-u",
        str(utilisateurs),
        "-r",
        str(max(1, utilisateurs // 5)),
        "-t",
        f"{duree}s",
        "--csv",
        prefixe,
        "--only-summary",
    ]
    subprocess.run(commande, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return lire_stats(prefixe)


def campagne(workers, paliers, duree, port):
    dossier = Path(DOSSIER)
    dossier.mkdir(parents=True, exist_ok=True)
    mesures = []

    for nombre in workers:
        api = demarrer_api(nombre, port)
        try:
            for utilisateurs in paliers:
                prefixe = str(dossier / f"{nombre}w_{utilisateurs}u")
                sonde = Sonde(api.pid)
                sonde.start()
                stats = jouer_palier(utilisateurs, duree, port, prefixe)
                mesure = {"workers": nombre, "utilisateurs": utilisateurs, **stats, **sonde.resume()}
                mesures.append(mesure)
                print(
                    f"{nombre}w {utilisateurs}u : {mesure['requetes_par_seconde']} req/s "
                    f"p95 {mesure['p95_ms']} ms echecs {mesure['echecs']} "
                    f"cpu {mesure['cpu_moyen_pourcent']}% ram {mesure['memoire_max_mo']} Mo"
                )
        finally:
            arreter(api)

    return mesures


def ecrire_resultats(mesures, duree, paliers):
    dossier = Path(DOSSIER)
    (dossier / "mesures.json").write_text(json.dumps(mesures, indent=2), encoding="utf-8")

    lignes = [
        "# Resultats des tests de charge",
        "",
        f"Paliers : {paliers} utilisateurs, {duree} s par palier, scenario `locustfile.py`.",
        "",
        "| workers | utilisateurs | req/s | p50 ms | p95 ms | echecs | cpu moyen | ram max |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mesure in mesures:
        lignes.append(
            f"| {mesure['workers']} | {mesure['utilisateurs']} | {mesure['requetes_par_seconde']} "
            f"| {mesure['p50_ms']} | {mesure['p95_ms']} | {mesure['echecs']} "
            f"| {mesure['cpu_moyen_pourcent']} % | {mesure['memoire_max_mo']} Mo |"
        )
    chemin = dossier / "resultats.md"
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"resultats ecrits dans {chemin}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare des configurations de l'api sous charge")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--paliers", type=int, nargs="+", default=[10, 25, 50, 100])
    parser.add_argument("--duree", type=int, default=60)
    parser.add_argument("--port", type=int, default=8001)
    arguments = parser.parse_args()

    mesures = campagne(arguments.workers, arguments.paliers, arguments.duree, arguments.port)
    ecrire_resultats(mesures, arguments.duree, arguments.paliers)
