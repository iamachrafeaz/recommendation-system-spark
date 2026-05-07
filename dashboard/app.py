import json
import os

import redis
from flask import Flask, jsonify

app = Flask(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
API_PORT = int(os.getenv("API_PORT", "8000"))

redis_client = redis.Redis(
	host=REDIS_HOST,
	port=REDIS_PORT,
	db=REDIS_DB,
	decode_responses=True,
)


@app.get("/health")
def health():
	try:
		return jsonify({"status": "ok", "redis": bool(redis_client.ping())})
	except Exception as exc:
		return jsonify({"status": "error", "detail": str(exc)}), 500


@app.get("/recommendations/<user_id>")
def get_recommendations(user_id: str):
	payload = redis_client.get(f"recs:user:{user_id}")
	if not payload:
		return jsonify(
			{
				"user_id": user_id,
				"product_ids": [],
				"message": "No recommendations found for this user_id",
			}
		), 404

	return jsonify(json.loads(payload))


@app.get("/metrics/stream")
def get_stream_metrics():
	metrics = redis_client.hgetall("metrics:kafka_stream")
	if not metrics:
		return jsonify({"message": "No streaming metrics yet"})
	return jsonify(metrics)


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=API_PORT, debug=False)

