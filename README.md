# Système de Recommandation Temps Réel · Spark / Kafka / Redis

Pipeline de recommandation de produits alimentaires Amazon basé sur ALS (Alternating Least Squares),
entièrement conteneurisé avec Docker.

---

## Prérequis

- Docker >= 24 et Docker Compose >= 2.20
- 4 Go de RAM disponibles minimum
- Ports libres : `8000`, `8501`, `9092`, `6379`

---

## Configuration

Tout d’abord, téléchargez le dataset depuis :
[Kaggle Amazon Fine Food Reviews](https://www.kaggle.com/snap/amazon-fine-food-reviews?utm_source=chatgpt.com)

Copiez ensuite le fichier du dataset (`.csv`) dans le projet.

Exécutez enfin :

```bash
python main.py
```

pour diviser le dataset.



## Installation

```bash
git clone https://github.com/iamachrafeaz/recommendation-system-spark
cd recommendation-system-spark
```

Générer un CLUSTER_ID pour Kafka (à faire une seule fois) :

```bash
docker run --rm confluentinc/cp-kafka:7.5.0 kafka-storage random-uuid
```

Coller la valeur dans `docker-compose.yaml` :

```yaml
broker:
  environment:
    CLUSTER_ID: "<uuid-généré>"
```

---

## Démarrage

```bash
docker compose up --build
```

L'ordre de démarrage est automatique :
1. **Kafka + Redis** démarrent en premier
2. **spark-batch** s'exécute et entraîne le modèle ALS → puis s'arrête
3. **spark-streaming** + **producer** démarrent en parallèle
4. **flask-api** + **streamlit-ui** sont disponibles dès que Redis est prêt

---

## Accès

| Service | URL |
|---|---|
| Dashboard Streamlit | http://localhost:8501 |
| API Flask | http://localhost:8000 |
| Health check | http://localhost:8000/health |

---

## Vérifications rapides

```bash
# Voir les recommandations stockées dans Redis
docker exec -it redis redis-cli KEYS "recs:user:*" | wc -l

# Tester l'API
curl http://localhost:8000/processed_users
curl http://localhost:8000/recommendations/<user_id>
curl http://localhost:8000/metrics/stream

# Logs du job batch
docker logs spark-batch

# Logs du streaming
docker logs -f spark-streaming
```

---

## Arrêt

```bash
# Arrêt simple (conserve les volumes)
docker compose down

# Arrêt complet + suppression des volumes (repart de zéro)
docker compose down --volumes --remove-orphans
```

---

## Structure

```
.
├── spark/
│   ├── batch.py          # Entraînement ALS (run & exit)
│   ├── streaming.py      # Consommation Kafka → Redis
│   ├── Dockerfile
│   └── requirements.txt  # pyspark, numpy, redis
├── producer/
│   ├── producer.py       # Simulation flux Kafka
│   └── reviews_10.csv    # Sous-ensemble de test (10%)
├── dashboard/
│   ├── app.py            # API Flask (port 8000)
│   └── dashboard_ui.py   # Interface Streamlit (port 8501)
├── data/
│   └── Reviews.csv       # Dataset complet Amazon Fine Food
└── docker-compose.yaml
```

---

## Points importants

**Dataset** — Le batch s'entraîne sur `spark/reviews_90.csv` (90% des données).
Le producer rejoue `producer/reviews_10.csv` (10% de test) dans Kafka.

**Modèle** — Sauvegardé dans le volume Docker `spark-models` partagé entre
`spark-batch` et `spark-streaming`. Ne pas supprimer ce volume entre deux runs
si vous voulez éviter de ré-entraîner.

**Rebuild** — Si vous modifiez `batch.py` ou `streaming.py`, relancez avec `--build`.
Si vous modifiez uniquement `app.py` ou `dashboard_ui.py` :

```bash
docker compose restart flask-api streamlit-ui
```

**Premier démarrage** — Le batch peut prendre **5 à 15 minutes** selon la machine
(téléchargement des packages Maven Kafka inclus au premier run du streaming).