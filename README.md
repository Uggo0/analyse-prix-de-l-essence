# Prix de l'essence en direct

Pipeline de données temps réel qui suit le prix des carburants dans les stations-service de ton choix en France, avec ingestion automatique, historique en base et dashboard interactif.

## Aperçu

Le prix des carburants change en continu. Ce projet interroge le jeu de données ouvert du gouvernement français, ne conserve que les stations que l'utilisateur choisit de suivre, et n'enregistre un nouveau relevé que lorsque le prix change réellement (pas de doublons toutes les 10 minutes). Un dashboard permet de chercher une station par ville, adresse ou code postal, de la suivre, et de visualiser l'évolution de ses prix sur une carte et un graphique.

## Source des données

[data.economie.gouv.fr — Prix des carburants en France, flux instantané](https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2/), mis à jour environ toutes les 10 minutes par le ministère de l'Économie. Environ 11 000 stations-service référencées en France, avec pour chacune ses coordonnées GPS, son adresse et le prix de chaque carburant vendu (Gazole, SP95, SP98, E10, E85, GPLc).

## Architecture

```
                     ┌─────────────┐
   toutes les 10min  │  pipeline   │
   ┌────────────────▶│  (Python)   │
   │                  └──────┬──────┘
   │                         │  1. quelles stations suivre ?
   │                         ▼
   │                  ┌─────────────┐
   │                  │  PostgreSQL │◀──────────────┐
   │                  └──────┬──────┘                │
   │                         │  2. quels prix ?       │  4. lecture
   │                         ▼                        │
   │                  ┌─────────────┐                 │
   │                  │  API gouv.  │           ┌─────┴──────┐
   │                  └──────┬──────┘           │  dashboard │
   │                         │  3. insertion si changé        │ Streamlit │
   └─────────────────────────┘                  └────────────┘
```

Trois conteneurs Docker, chacun avec une seule responsabilité :

- **`pipeline`** : va chercher les prix des stations suivies et les enregistre, en continu, toutes les 10 minutes (`APScheduler`).
- **`postgres`** : stocke les stations suivies et l'historique des prix.
- **`dashboard`** : lit la base et l'affiche (recherche, carte, courbes), sans jamais interroger l'API directement pour les prix.

## Schéma de données

- **`stations`** : référentiel des stations connues (adresse, ville, coordonnées GPS), avec un indicateur `suivie` qui définit la watchlist personnelle de l'utilisateur.
- **`prix`** : historique des relevés, une ligne par changement de prix constaté (pas un relevé toutes les 10 minutes), indexé sur `(station_id, carburant, releve_at DESC)` pour retrouver rapidement le dernier prix connu.

Cette séparation référentiel / historique est le pattern standard pour tout système de suivi dans le temps (cours de bourse, capteurs IoT, prix e-commerce...).

## Stack technique

| Rôle | Outil |
|---|---|
| Langage | Python |
| Base de données | PostgreSQL |
| Accès base | `psycopg2` (pipeline), `SQLAlchemy` + `pandas` (dashboard) |
| Appels API | `requests` |
| Planification | `APScheduler` |
| Interface | `Streamlit` |
| Conteneurisation | Docker / Docker Compose |

## Fonctionnalités

- Recherche de station par ville, adresse ou code postal
- Ajout d'une station suivie avec récupération immédiate de son premier prix (sans attendre le prochain cycle)
- Historique de prix stocké uniquement lors d'un changement réel (change data capture)
- Carte centrée sur la station sélectionnée
- Courbe d'évolution et dernier prix en direct par carburant

## Lancer le projet

Prérequis : Docker Desktop.

```bash
git clone https://github.com/Uggo0/analyse-prix-de-l-essence.git
cd analyse-prix-de-l-essence
cp .env.example .env   # puis personnaliser le mot de passe Postgres
docker compose up --build -d
```

Dashboard disponible sur [http://localhost:8501](http://localhost:8501).

## Limites connues

- Aucune gestion d'erreur réseau : un échec de l'API interrompt le cycle en cours (à améliorer avec `try/except` et une nouvelle tentative différée)
- Pas de journalisation (logs) du pipeline
- L'API est limitée à 100 résultats par appel : pas de pagination au-delà de 100 stations suivies simultanément
- Pas de tests automatisés

## Ce que ce projet démontre

Conception d'un schéma relationnel adapté à des données temporelles, séparation des responsabilités entre ingestion/stockage/visualisation, requêtes SQL paramétrées (protection contre l'injection), orchestration d'un pipeline temps réel avec Docker Compose, et consommation d'une API publique réelle.
