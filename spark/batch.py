import argparse
import logging
import sys
from pathlib import Path

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import StringIndexer
from pyspark.ml.pipeline import Pipeline
from pyspark.ml.recommendation import ALS, ALSModel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import IntegerType

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------

def build_spark_session(app_name: str = "ALSRecommender") -> SparkSession:
    spark = (
        SparkSession.builder
        .appName(app_name)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    logger.info("SparkSession initialised (version %s)", spark.version)
    return spark


# ---------------------------------------------------------------------------
# Data loading & validation
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {"UserId", "ProductId", "Score"}

def load_reviews(spark: SparkSession, path: str) -> DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .option("quote", '"')
        .option("escape", '"')
        .option("multiLine", True)
        .option("mode", "PERMISSIVE")
        .csv(path)
    )

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    logger.info("Loaded %d raw rows from '%s'", df.count(), path)
    return df


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def preprocess(df: DataFrame) -> DataFrame:
    df = (
        df.select("UserId", "ProductId", "Score")
          .withColumn("Score", col("Score").cast(IntegerType()))
          .dropna(subset=["UserId", "ProductId", "Score"])
          # Guard against out-of-range ratings
          .filter(col("Score").between(1, 5))
    )

    n = df.count()
    if n == 0:
        raise ValueError("No valid rows remain after preprocessing.")

    logger.info("Preprocessed dataset: %d rows", n)
    return df


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def build_indexer_pipeline(df: DataFrame):
    user_indexer = StringIndexer(
        inputCol="UserId",
        outputCol="userIndex",
        handleInvalid="skip",
    )
    item_indexer = StringIndexer(
        inputCol="ProductId",
        outputCol="itemIndex",
        handleInvalid="skip",
    )

    pipeline = Pipeline(stages=[user_indexer, item_indexer])
    model = pipeline.fit(df)
    indexed_df = model.transform(df)

    n_users = indexed_df.select("userIndex").distinct().count()
    n_items = indexed_df.select("itemIndex").distinct().count()
    logger.info("Distinct users: %d | Distinct items: %d", n_users, n_items)

    return model, indexed_df


def prepare_ratings(indexed_df: DataFrame) -> DataFrame:
    """Cast index columns to int and return the three-column ratings table."""
    return indexed_df.select(
        col("userIndex").cast("int"),
        col("itemIndex").cast("int"),
        col("Score"),
    )


# ---------------------------------------------------------------------------
# Model training & evaluation
# ---------------------------------------------------------------------------

def train_als(
    train: DataFrame,
    rank: int = 10,
    max_iter: int = 10,
    reg_param: float = 0.1,
    seed: int = 42,
) -> ALSModel:
    """Fit an ALS model on *train* and return it."""
    als = ALS(
        userCol="userIndex",
        itemCol="itemIndex",
        ratingCol="Score",
        rank=rank,
        maxIter=max_iter,
        regParam=reg_param,
        nonnegative=True,
        coldStartStrategy="drop",
        seed=seed,
    )
    logger.info(
        "Training ALS (rank=%d, maxIter=%d, regParam=%.4f) …",
        rank, max_iter, reg_param,
    )
    model = als.fit(train)
    logger.info("Training complete.")
    return model


def evaluate(model, test: DataFrame) -> dict:
    predictions = model.transform(test).dropna(subset=["prediction"])

    if predictions.rdd.isEmpty():
        logger.warning("No valid predictions — evaluation skipped.")
        return {}

    rmse = RegressionEvaluator(
        metricName="rmse", labelCol="Score", predictionCol="prediction"
    ).evaluate(predictions)

    mae = RegressionEvaluator(
        metricName="mae", labelCol="Score", predictionCol="prediction"
    ).evaluate(predictions)

    logger.info("Evaluation → RMSE: %.4f | MAE: %.4f", rmse, mae)

    predictions.select("userIndex", "itemIndex", "Score", "prediction") \
               .show(20, truncate=False)

    return {"rmse": rmse, "mae": mae}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_artifacts(
    indexer_pipeline,
    als_model,
    output_dir: str,
) -> None:
    """Persist the indexer pipeline and ALS model to *output_dir*."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    pipeline_path = str(Path(output_dir) / "indexer_pipeline")
    model_path = str(Path(output_dir) / "als_model")

    indexer_pipeline.write().overwrite().save(pipeline_path)
    als_model.write().overwrite().save(model_path)

    logger.info("Saved indexer pipeline → %s", pipeline_path)
    logger.info("Saved ALS model        → %s", model_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train an ALS recommender on Amazon product reviews."
    )
    parser.add_argument("--input", required=True, help="Path to Reviews.csv")
    parser.add_argument(
        "--output-dir", default="./output",
        help="Directory to save trained model artefacts (default: ./output)",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.8,
        help="Fraction of data used for training (default: 0.8)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rank", type=int, default=10)
    parser.add_argument("--max-iter", type=int, default=10)
    parser.add_argument("--reg-param", type=float, default=0.1)
    return parser.parse_args(argv)


def main(argv=None) -> dict:
    args = parse_args(argv)
    spark = build_spark_session()

    try:
        # 1. Load
        raw_df = load_reviews(spark, args.input)

        # 2. Preprocess
        clean_df = preprocess(raw_df)

        # 3. Feature engineering
        indexer_pipeline, indexed_df = build_indexer_pipeline(clean_df)
        ratings = prepare_ratings(indexed_df)

        # 4. Split
        train, test = ratings.randomSplit(
            [args.train_ratio, 1.0 - args.train_ratio],
            seed=args.seed,
        )
        logger.info(
            "Train rows: %d | Test rows: %d", train.count(), test.count()
        )

        # 5. Train
        als_model = train_als(
            train,
            rank=args.rank,
            max_iter=args.max_iter,
            reg_param=args.reg_param,
            seed=args.seed,
        )

        # 6. Evaluate
        metrics = evaluate(als_model, test)

        # 7. Persist artefacts
        save_artifacts(indexer_pipeline, als_model, args.output_dir)

        return metrics

    except Exception:
        logger.exception("Pipeline failed with an unhandled exception.")
        sys.exit(1)

    finally:
        spark.stop()
        logger.info("SparkSession stopped.")


if __name__ == "__main__":
    main()