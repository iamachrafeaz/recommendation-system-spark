import json
import os
from datetime import datetime

import redis
from pyspark.ml import PipelineModel
from pyspark.ml.recommendation import ALSModel
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, collect_list, desc, explode, from_json
from pyspark.sql.types import FloatType, LongType, StringType, StructType

spark = SparkSession.builder.appName("ALS-Streaming-Redis").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

pipeline_model = PipelineModel.load("/app/output/indexer_pipeline")
als_model = ALSModel.load("/app/output/als_model")

user_indexer = pipeline_model.stages[0]
item_labels = pipeline_model.stages[1].labels
item_mapping = spark.createDataFrame(
    [(int(i), label) for i, label in enumerate(item_labels)],
    ["itemIndex", "ProductId"],
)

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


def process_batch(batch_df, batch_id):
    if batch_df.rdd.isEmpty():
        return

    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )

    input_rows = batch_df.count()
    users_df = batch_df.select(col("user_id").alias("UserId")).dropna().distinct()
    distinct_users = users_df.count()

    indexed_users = user_indexer.transform(users_df).select("UserId", "userIndex")
    if indexed_users.rdd.isEmpty():
        redis_client.hset(
            METRICS_KEY,
            mapping={
                "last_batch_id": str(batch_id),
                "last_batch_ts": datetime.utcnow().isoformat(),
                "last_input_rows": str(input_rows),
                "last_distinct_users": str(distinct_users),
                "known_users_in_batch": "0",
            },
        )
        return

    recs = als_model.recommendForUserSubset(indexed_users.select("userIndex"), 5)
    flat_recs = (
        recs.select("userIndex", explode("recommendations").alias("rec"))
        .select(
            col("userIndex"),
            col("rec.itemIndex").cast("int").alias("itemIndex"),
            col("rec.rating").alias("rating"),
        )
    )

    joined_recs = (
        flat_recs.join(item_mapping, on="itemIndex", how="inner")
        .join(indexed_users, on="userIndex", how="inner")
        .select("UserId", "ProductId", "rating")
        .orderBy(col("UserId"), desc("rating"))
    )

    user_recs_df = joined_recs.groupBy("UserId").agg(collect_list("ProductId").alias("product_ids"))

    for row in user_recs_df.collect():
        payload = {
            "user_id": row["UserId"],
            "product_ids": row["product_ids"][:5],
            "updated_at": datetime.utcnow().isoformat(),
        }
        redis_client.set(f"recs:user:{row['UserId']}", json.dumps(payload))

    user_count = user_recs_df.count()
    redis_client.hset(
        METRICS_KEY,
        mapping={
            "last_batch_id": str(batch_id),
            "last_batch_ts": datetime.utcnow().isoformat(),
            "last_input_rows": str(input_rows),
            "last_distinct_users": str(distinct_users),
            "known_users_in_batch": str(user_count),
        },
    )
    redis_client.hincrby(METRICS_KEY, "total_rows_seen", int(input_rows))
    redis_client.hincrby(METRICS_KEY, "total_users_processed", int(user_count))


query = (
    parsed.writeStream
    .foreachBatch(process_batch)
    .outputMode("update")
    .option("checkpointLocation", "/tmp/checkpoints/als_streaming_to_redis")
    .start()
)

query.awaitTermination()