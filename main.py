import pandas as pd

df = pd.read_csv("./data/Reviews.csv")

train = df.sample(frac=0.9, random_state=42)

test = df.drop(train.index)

train.to_csv('./spark/reviews_90.csv', index=False)

test.to_csv('./producer/reviews_10.csv', index=False)

# spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 batch.py --input reviews_90.csv
