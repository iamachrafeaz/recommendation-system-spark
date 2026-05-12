import os
import pandas as pd

FILE_PATH = "Reviews.csv"

if not os.path.exists(FILE_PATH):
    print(f"Error: '{FILE_PATH}' not found.")
    print("Make sure the dataset file exists in the project root.")
    exit(1)

try:
    df = pd.read_csv(FILE_PATH)

    batch = df.sample(frac=0.9, random_state=42)
    streaming = df.drop(batch.index)

    os.makedirs("./spark", exist_ok=True)
    os.makedirs("./producer", exist_ok=True)

    batch.to_csv("./spark/reviews_90.csv", index=False)
    streaming.to_csv("./producer/reviews_10.csv", index=False)

    print("Dataset split completed successfully.")

except Exception as e:
    print(f"An error occurred: {e}")