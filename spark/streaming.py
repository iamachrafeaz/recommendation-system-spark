from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, explode
from pyspark.sql.types import StructType, StringType, FloatType, LongType

from pyspark.ml import PipelineModel
from pyspark.ml.recommendation import ALSModel


# ---------------- SPARK ----------------
spark = SparkSession.builder.appName("ALS-Streaming").getOrCreate()
spark.sparkContext.setLogLevel("WARN")


# ---------------- LOAD MODELS ----------------
pipeline_model = PipelineModel.load("output/indexer_pipeline")
als_model = ALSModel.load("output/als_model")

# Extract ONLY user indexer
user_indexer = pipeline_model.stages[0]

# Extract item mapping once (static)
item_labels = pipeline_model.stages[1].labels

item_mapping = spark.createDataFrame(
    [(i, label) for i, label in enumerate(item_labels)],
    ["itemIndex", "ProductId"]
)


# ---------------- KAFKA STREAM ----------------
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "broker:9092") \
    .option("subscribe", "product_reviews") \
    .option("startingOffsets", "latest") \
    .load()


# ---------------- SCHEMA ----------------
schema = StructType() \
    .add("user_id", StringType()) \
    .add("product_id", StringType()) \
    .add("score", FloatType()) \
    .add("time", LongType())


parsed = kafka_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")


# ---------------- PROCESS BATCH ----------------
def process_batch(batch_df, batch_id):

    if batch_df.isEmpty():
        return

    # Only need users
    users_df = batch_df.select(col("user_id").alias("UserId")).distinct()

    # Apply ONLY user indexer
    indexed_users = user_indexer.transform(users_df)

    indexed_users.show()

    # Handle unknown users
    if indexed_users.rdd.isEmpty():
        print(f"Batch {batch_id}: no known users")
        return

    # Recommend
    recs = als_model.recommendForUserSubset(indexed_users, 5)

    # Flatten
    recs = recs.select(
        col("userIndex"),
        explode(col("recommendations")).alias("rec")
    ).select(
        col("userIndex"),
        col("rec.itemIndex"),
        col("rec.rating")
    )

    # Map back to ProductId
    final_recs = recs.join(item_mapping, "itemIndex") \
                     .join(indexed_users, "userIndex")

    final_recs.show(truncate=False)


# ---------------- STREAM RUN ----------------
query = parsed.writeStream \
    .foreachBatch(process_batch) \
    .outputMode("append") \
    .start()

query.awaitTermination()