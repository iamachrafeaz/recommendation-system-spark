import json
from time import sleep

from kafka import KafkaProducer
import pandas as pd


def create_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=['broker:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=5000,
            retries=2
        )

        # Force metadata fetch to test connection
        producer.bootstrap_connected()
        print("✅ Connected to Kafka successfully")

        return producer

    except Exception as e:
        print("❌ Kafka connection failed:")
        print(str(e))
        raise


producer = create_producer()


def send_product_data(product_data):
    product = {
        "user_id": product_data.UserId,
        "product_id": product_data.ProductId,
        "score": product_data.Score,
        "time": product_data.Time
    }

    try:
        print("➡️ Sending:", product)

        future = producer.send('product_reviews', product)

        record_metadata = future.get(timeout=10)

        print(f"✅ Sent -> partition {record_metadata.partition}")

    except Exception as e:
        print("❌ FULL KAFKA ERROR:")
        print(type(e))
        print(str(e))
        raise

def get_product_data():
    return pd.read_csv("reviews_10.csv")


if __name__ == "__main__":
    print("🚀 Starting producer")

    data = get_product_data()

    for index, row in data.iterrows():
        send_product_data(row)
        sleep(10)