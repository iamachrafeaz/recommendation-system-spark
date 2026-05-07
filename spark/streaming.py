import json
import os
import time
from datetime import datetime
import redis
from pyspark.ml import PipelineModel
from pyspark.ml.recommendation import ALSModel
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, collect_list, desc, explode, from_json
from pyspark.sql.types import FloatType, LongType, StringType, StructType

# --- SÉCURITÉ : ATTENTE DU MODÈLE ---
MODEL_PATH = "/app/output/als_model"
PIPELINE_PATH = "/app/output/indexer_pipeline"

print("🔍 Vérification des modèles ALS et Indexer...")
while not (os.path.exists(MODEL_PATH) and os.path.exists(PIPELINE_PATH)):
    print("⏳ Modèles absents. Spark attend que la tâche BATCH se termine...")
    time.sleep(10)

# --- INITIALISATION SPARK ---
spark = SparkSession.builder.appName("ALS-Streaming-Redis").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# Chargement des modèles une fois qu'ils existent
pipeline_model = PipelineModel.load(PIPELINE_PATH)
als_model = ALSModel.load(MODEL_PATH)

user_indexer = pipeline_model.stages[0]
item_labels = pipeline_model.stages[1].labels
item_mapping = spark.createDataFrame(
    [(int(i), label) for i, label in enumerate(item_labels)],
    ["itemIndex", "ProductId"],
)

# --- CONFIGURATION REDIS ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
METRICS_KEY = "metrics:kafka_stream"

schema = (
    StructType()
    .add("user_id", StringType())
    .add("product_id", StringType())
    .add("score", FloatType())
    .add("time", LongType())
)

# --- LECTURE KAFKA ---
kafka_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "product_reviews")
    .option("startingOffsets", "latest")
    .load()
)

parsed = (
    kafka_df.selectExpr("CAST(value AS STRING) AS value")
    .select(from_json(col("value"), schema).alias("data"))
    .select("data.*")
)

# --- LOGIQUE DE BATCH (TA LOGIQUE ORIGINALE) ---
def process_batch(batch_df, batch_id):
    if batch_df.rdd.isEmpty():
        return

    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    input_rows = batch_df.count()
    users_df = batch_df.select(col("user_id").alias("UserId")).dropna().distinct()
    distinct_users = users_df.count()

    indexed_users = user_indexer.transform(users_df).select("UserId", "userIndex")
    if indexed_users.rdd.isEmpty():
        # Mise à jour des métriques même si vide
        redis_client.hset(METRICS_KEY, mapping={"last_batch_id": str(batch_id), "last_batch_ts": datetime.utcnow().isoformat()})
        return

    # Recommandations
    recs = als_model.recommendForUserSubset(indexed_users.select("userIndex"), 5)
    flat_recs = recs.select("userIndex", explode("recommendations").alias("rec")) \
        .select(col("userIndex"), col("rec.itemIndex").cast("int").alias("itemIndex"), col("rec.rating").alias("rating"))

    joined_recs = flat_recs.join(item_mapping, on="itemIndex", how="inner") \
        .join(indexed_users, on="userIndex", how="inner") \
        .select("UserId", "ProductId", "rating") \
        .orderBy(col("UserId"), desc("rating"))

    user_recs_df = joined_recs.groupBy("UserId").agg(collect_list("ProductId").alias("product_ids"))

    # Envoi vers Redis
    for row in user_recs_df.collect():
        payload = {
            "user_id": row["UserId"],
            "product_ids": row["product_ids"][:5],
            "updated_at": datetime.utcnow().isoformat(),
        }
        redis_client.set(f"recs:user:{row['UserId']}", json.dumps(payload))

    # Métriques
    user_count = user_recs_df.count()
    redis_client.hset(METRICS_KEY, mapping={
        "last_batch_id": str(batch_id),
        "last_batch_ts": datetime.utcnow().isoformat(),
        "last_input_rows": str(input_rows),
        "known_users_in_batch": str(user_count),
    })
    redis_client.hincrby(METRICS_KEY, "total_rows_seen", int(input_rows))

# --- DÉMARRAGE DU STREAM ---
query = (
    parsed.writeStream
    .foreachBatch(process_batch)
    .outputMode("update")
    .option("checkpointLocation", "/tmp/checkpoints/als_streaming_to_redis")
    .start()
)

query.awaitTermination()