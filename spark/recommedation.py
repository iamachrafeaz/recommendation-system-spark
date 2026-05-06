from pyspark.sql import SparkSession
from pyspark.ml.pipeline import PipelineModel
from pyspark.ml.recommendation import ALSModel
from pyspark.sql.functions import explode, col

# --------------------------------------------------
# 1. Start Spark
# --------------------------------------------------
spark = SparkSession.builder.appName("ALSInference").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# --------------------------------------------------
# 2. Load saved models
# --------------------------------------------------
pipeline_model = PipelineModel.load("output/indexer_pipeline")
als_model = ALSModel.load("output/als_model")

# --------------------------------------------------
# 3. Input data (users you want recommendations for)
# --------------------------------------------------
# IMPORTANT: must have same column name: "UserId"
users_df = spark.createDataFrame([
    ("A3OXHLG6DIBRW8",),
], ["UserId"])


user_indexer_model = pipeline_model.stages[0]

# --------------------------------------------------
# 4. Apply SAME indexing
# --------------------------------------------------
indexed_users = user_indexer_model.transform(users_df)

indexed_users.show()

# This gives: UserId + userIndex

# --------------------------------------------------
# 5. Generate recommendations
# --------------------------------------------------
recommendations = als_model.recommendForUserSubset(indexed_users, 5)

# --------------------------------------------------
# 6. Flatten results
# --------------------------------------------------
recs = recommendations.select(
    col("userIndex"),
    explode(col("recommendations")).alias("rec")
).select(
    col("userIndex"),
    col("rec.itemIndex"),
    col("rec.rating")
)

# --------------------------------------------------
# 7. Convert back to original ProductId
# --------------------------------------------------

# Extract labels from indexer
item_labels = pipeline_model.stages[1].labels  # ProductId indexer

# Create mapping DataFrame
item_mapping = spark.createDataFrame(
    [(i, label) for i, label in enumerate(item_labels)],
    ["itemIndex", "ProductId"]
)

# Join to get real ProductId
final_recs = recs.join(item_mapping, on="itemIndex", how="left")

# --------------------------------------------------
# 8. Show results
# --------------------------------------------------
final_recs.show(truncate=False)