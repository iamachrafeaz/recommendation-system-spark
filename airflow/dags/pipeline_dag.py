from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

default_args = {
    "owner": "data-eng",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="recommendation_pipeline",
    default_args=default_args,
    description="Batch Training → Producer + Streaming (parallel)",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    # ============ Étape 1 : Entraînement Batch ============
    # On crée le modèle ALS. C'est la base de tout.
    run_batch = DockerOperator(
        task_id="batch_training",
        image="recsys-spark:latest",
        command="spark-submit --master spark://spark-master:7077 /app/batch.py",
        network_mode="bigdata-net",
        auto_remove=True,
        mount_tmp_dir=False,
        mounts=[
            # Crucial : le dossier où Spark écrit le modèle doit être persistant
            Mount(source="spark-models", target="/app/output", type="volume"),
        ],
    )

    # ============ Étape 2a : Producer Kafka ============
    # Le producer va créer le topic lui-même s'il manque.
    run_prod = DockerOperator(
        task_id="producer",
        image="recsys-producer:latest",
        command="python producer.py",
        network_mode="bigdata-net",
        auto_remove=True,
        mount_tmp_dir=False,
    )

    # ============ Étape 2b : Spark Streaming ============
    run_stream = DockerOperator(
        task_id="streaming",
        image="recsys-spark:latest",
        command="spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 /app/streaming.py",
        network_mode="bigdata-net",
        auto_remove=False, # On le garde allumé pour voir les logs
        mount_tmp_dir=False,
        mounts=[
            # Crucial : il lit le modèle créé par le Batch
            Mount(source="spark-models", target="/app/output", type="volume"),
        ],
    )

    # Dépendances : Le Batch doit être SUCCESS avant de lancer la suite
    run_batch >> [run_prod, run_stream]