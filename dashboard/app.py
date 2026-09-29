import os

import pandas as pd
import requests
import streamlit as st
from sqlalchemy import create_engine, text

URL_API = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records"
CARBURANTS = ["gazole", "sp95", "sp98", "e10", "e85", "gplc"]

moteur = create_engine(os.getenv("DATABASE_URL"))


def chercher_stations(recherche):
    recherche = recherche.replace('"', "").replace("\\", "").strip()
    if not recherche:
        return []
    params = {
        "limit": 20,
        "select": "id,ville,cp,adresse,geom",
        "where": f'search(ville, "{recherche}") or search(adresse, "{recherche}") or cp = "{recherche}"',
    }
    reponse = requests.get(URL_API, params=params, timeout=15)
    reponse.raise_for_status()
    stations = []
    for s in reponse.json()["results"]:
        geom = s.get("geom") or {}
        stations.append({
            "id": s["id"],
            "ville": s["ville"],
            "cp": s["cp"],
            "adresse": s["adresse"],
            "latitude": geom.get("lat"),
            "longitude": geom.get("lon"),
        })
    return stations


def suivre_station(station):
    with moteur.begin() as connexion:
        connexion.execute(
            text(
                """
                INSERT INTO stations (id, adresse, ville, code_postal, latitude, longitude, suivie, derniere_synchro)
                VALUES (:id, :adresse, :ville, :cp, :latitude, :longitude, true, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    suivie = true,
                    adresse = EXCLUDED.adresse,
                    ville = EXCLUDED.ville,
                    code_postal = EXCLUDED.code_postal,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    derniere_synchro = NOW()
                """
            ),
            station,
        )


def enregistrer_premiers_prix(station_id):
    reponse = requests.get(URL_API, params={"limit": 1, "where": f"id = {int(station_id)}"}, timeout=15)
    reponse.raise_for_status()
    resultats = reponse.json()["results"]
    if not resultats:
        return
    fiche = resultats[0]
    with moteur.begin() as connexion:
        for carburant in CARBURANTS:
            prix = fiche.get(f"{carburant}_prix")
            if prix is None:
                continue
            connexion.execute(
                text(
                    """
                    INSERT INTO prix (station_id, carburant, prix, maj_source_at)
                    SELECT :station_id, :carburant, :prix, :maj
                    WHERE NOT EXISTS (
                        SELECT 1 FROM prix WHERE station_id = :station_id AND carburant = :carburant
                    )
                    """
                ),
                {
                    "station_id": station_id,
                    "carburant": carburant,
                    "prix": prix,
                    "maj": fiche.get(f"{carburant}_maj"),
                },
            )


@st.cache_data(ttl=60)
def charger_stations_suivies():
    df = pd.read_sql(
        "SELECT id, ville, adresse, latitude, longitude FROM stations WHERE suivie = true ORDER BY ville, adresse",
        moteur,
    )
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    df["libelle"] = df["ville"].fillna("Station") + " - " + df["adresse"].fillna("adresse inconnue") + " (" + df["id"].astype(str) + ")"
    return df


@st.cache_data(ttl=60)
def charger_prix():
    df = pd.read_sql(
        "SELECT station_id, carburant, prix, maj_source_at FROM prix ORDER BY maj_source_at",
        moteur,
    )
    df["prix"] = df["prix"].astype(float)
    return df


st.title("Prix de l'essence en direct")

with st.expander("Ajouter une station à suivre"):
    recherche = st.text_input("Ville, code postal ou adresse")
    if recherche:
        try:
            resultats = chercher_stations(recherche)
        except requests.RequestException:
            resultats = []
            st.error("L'API du gouvernement ne répond pas, réessaie dans un instant.")
        if not resultats:
            st.warning("Aucune station trouvée.")
        else:
            libelles = {f"{r['ville']} - {r['adresse']} ({r['cp']})": r for r in resultats}
            choix = st.selectbox("Résultats", list(libelles))
            if st.button("Suivre cette station"):
                station_ajoutee = libelles[choix]
                suivre_station(station_ajoutee)
                try:
                    enregistrer_premiers_prix(station_ajoutee["id"])
                except requests.RequestException:
                    st.warning("Station ajoutée, mais ses prix n'ont pas pu être récupérés tout de suite.")
                st.cache_data.clear()
                st.success("Station ajoutée.")

stations = charger_stations_suivies()

if stations.empty:
    st.info("Aucune station suivie pour l'instant. Ajoute-en une ci-dessus.")
    st.stop()

libelle = st.sidebar.selectbox("Station", stations["libelle"].tolist())
station = stations[stations["libelle"] == libelle].iloc[0]

if pd.notna(station["latitude"]) and pd.notna(station["longitude"]):
    st.map(
        pd.DataFrame({"latitude": [station["latitude"]], "longitude": [station["longitude"]]}),
        color="#C1602A",
        size=60,
        zoom=14,
    )
else:
    st.caption("Position inconnue pour cette station : recherche-la et clique sur « Suivre cette station » pour l'enregistrer.")

prix_station = charger_prix()
prix_station = prix_station[prix_station["station_id"] == station["id"]]

if prix_station.empty:
    st.info("Pas encore de prix pour cette station : ils arrivent au prochain cycle du pipeline (10 minutes maximum).")
    st.stop()

carburant = st.sidebar.selectbox("Carburant", sorted(prix_station["carburant"].unique()))
selection = prix_station[prix_station["carburant"] == carburant]
dernier = selection.iloc[-1]

st.metric(f"{carburant.upper()} - {libelle}", f"{dernier['prix']:.3f} €")
st.line_chart(selection, x="maj_source_at", y="prix")
st.dataframe(selection[["maj_source_at", "prix"]], hide_index=True)
