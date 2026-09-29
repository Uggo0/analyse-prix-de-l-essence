import requests

url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records"


def recuperer_prix(liste_ids):

    ids_en_texte = []
    for id in liste_ids :
        ids_en_texte.append(str(id))

    ids_joints = ",".join(ids_en_texte)

    condition = f"id in ({ids_joints})"

    params={
    "limit": 100,
    "where": condition
    }
    reponse = requests.get(url, params=params)

    donnees = reponse.json()
    stations = donnees["results"]
    carburants = ["gazole", "sp95", "sp98", "e10", "e85", "gplc"]
    resultats = []

    for station in stations :
        for carburant in carburants:
            prix = station[f"{carburant}_prix"]
            maj = station[f"{carburant}_maj"]

            if prix is not None:
             resultats.append({
                "station_id": station["id"],
                "carburant": carburant,
                "prix": prix,
                "maj": maj
             })
    return resultats