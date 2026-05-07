from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

default_args = {
	"owner": "data-eng",
	"depends_on_past": False,
	"retries": 1,
	"retry_delay": timedelta(minutes=2),
}

with DAG(
	dag_id="recommendation_pipeline",
	default_args=default_args,
	description="Producer Kafka -> Spark Batch Training -> Spark Streaming",
	start_date=datetime(2026, 1, 1),
	schedule=None,
	catchup=False,
	tags=["kafka", "spark", "redis", "recommender"],
) as dag:
	run_producer = DockerOperator(
		task_id="run_producer_kafka",
		image="recsys-producer:latest",
		command="python producer.py",
		network_mode="bigdata-net",
		auto_remove=True,
		mount_tmp_dir=False,
	)

	run_batch_training = DockerOperator(
		task_id="run_spark_batch_training",
		image="recsys-spark:latest",
		command=(
			"spark-submit "
			"--master spark://spark-master:7077 "
			"--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 "
			"/app/batch.py "
			"--input /app/reviews_90.csv "
			"--output-dir /app/output"
		),
		network_mode="bigdata-net",
		auto_remove=True,
		mount_tmp_dir=False,
		mounts=[
			Mount(source="spark-models", target="/app/output", type="volume"),
			Mount(
				source="/home/mehdilaghrissi/projects/recommendation-system-spark/spark",
				target="/app",
				type="bind",
			),
		],
	)

	run_streaming = DockerOperator(
		task_id="run_spark_streaming",
		image="recsys-spark:latest",
		command=(
			"spark-submit "
			"--master spark://spark-master:7077 "
			"--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 "
			"/app/streaming.py"
		),
		network_mode="bigdata-net",
		auto_remove=False,
		mount_tmp_dir=False,
		mounts=[
			Mount(source="spark-models", target="/app/output", type="volume"),
			Mount(
				source="/home/mehdilaghrissi/projects/recommendation-system-spark/spark",
				target="/app",
				type="bind",
			),
		],
	)

	run_producer >> run_batch_training >> run_streaming
