import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
url_base = os.getenv("DATABASE_URL")

connexion = psycopg2.connect(url_base)
curseur = connexion.cursor()

def recuperer_stations_suivies():
    curseur.execute("SELECT id FROM stations WHERE suivie = true")
    lignes = curseur.fetchall()

    ids = []
    for ligne in lignes:
     ids.append(ligne[0])
    return ids

def enregistrer_prix(liste_prix):
   for fiche in liste_prix:
      curseur.execute(
         "SELECT prix FROM prix WHERE station_id = %s AND carburant = %s ORDER BY releve_at DESC LIMIT 1",
         (fiche["station_id"], fiche["carburant"])
      )
      
      dernier = curseur.fetchone()

      if dernier is None or float(dernier[0]) != fiche["prix"]:
         curseur.execute(
            "INSERT INTO prix (station_id, carburant, prix, maj_source_at) VALUES (%s, %s, %s, %s)",
            (fiche["station_id"], fiche["carburant"], fiche["prix"], fiche["maj"])
         )
   connexion.commit()
                                  
                                  
                                  
                                  
            