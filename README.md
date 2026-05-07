## Setup
1. Download dataset from `https://www.kaggle.com/snap/amazon-fine-food-reviews`
2. Put the CSV in `data/`
3. Split data for producer/batch inputs:

```bash
python main.py
```

## Start full stack

```bash
docker compose up -d --build
```

Services:
- Airflow UI: `http://localhost:8088` (admin/admin)
- Dashboard API: `http://localhost:8000`
- Streamlit UI: `http://localhost:8501`
- Spark Master UI: `http://localhost:8080`

## Airflow pipeline
Run DAG `recommendation_pipeline` to orchestrate:
1. Kafka producer
2. Spark batch training (ALS model)
3. Spark streaming to Redis (Top-5 recommendations by user)

## Manual run (optional)

```bash
docker compose run --rm producer python producer.py
docker compose run --rm spark-master spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 /app/batch.py --input /app/reviews_90.csv --output-dir /app/output
docker compose run --rm spark-master spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 /app/streaming.py
```
