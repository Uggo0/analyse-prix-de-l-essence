from db import recuperer_stations_suivies, enregistrer_prix
from fetch import recuperer_prix
from apscheduler.schedulers.blocking import BlockingScheduler

def cycle():
    ids = recuperer_stations_suivies()

    if not ids:
        return

    prix = recuperer_prix(ids)
    enregistrer_prix(prix)

def demarrer():
    planificateur=BlockingScheduler()
    planificateur.add_job(cycle, "interval", minutes=10)
    planificateur.start()