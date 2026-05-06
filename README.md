## Setup
First, download dataset from 
`https://www.kaggle.com/snap/amazon-fine-food-reviews`

Copy the dataset (.csv) to `data/`

Run `python main.py` to split dataset

Run docker compose up, but 

## Kafka
Go to the `broker` container and run this command to create topic :
`/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --partitions 1 --replication-factor 1 --topic product_reviews`

## Batch
To train model, go to `spark-master` container and execute this command :
`spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 batch.py --input reviews_90.csv`

## Streaming
Make sure producer is up and running : `python producer.py`

Go to `spark-master` container and execute this :
`spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 streaming.py`