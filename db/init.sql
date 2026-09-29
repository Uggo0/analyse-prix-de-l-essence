CREATE TABLE stations(

    id INTEGER PRIMARY KEY,
    adresse TEXT,
    ville TEXT,
    code_postal TEXT,
    latitude NUMERIC(9,6), 
    longitude NUMERIC(9,6),
    suivie BOOLEAN DEFAULT FALSE,
    derniere_synchro TIMESTAMP
);

CREATE TABLE prix(

    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES stations(id),
    carburant TEXT,
    prix NUMERIC(5,3),
    maj_source_at TIMESTAMP,
    releve_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_prix_station_carburant ON prix (station_id, carburant, releve_at DESC);