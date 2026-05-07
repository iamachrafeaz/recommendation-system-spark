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

    # Calcule le vrai nombre d'utilisateurs traités depuis les clés Redis
    user_keys = redis_client.keys("recs:user:*")
    metrics["total_users_processed"] = str(len(user_keys))

    return jsonify(metrics)


@app.get("/processed_users")
def get_processed_users():
    """Retourne la liste de tous les user_id ayant des recommandations."""
    keys = redis_client.keys("recs:user:*")
    user_ids = sorted([k.replace("recs:user:", "") for k in keys])
    return jsonify({"user_ids": user_ids, "count": len(user_ids)})


@app.get("/recent_activity")
def get_recent_activity():
    """Retourne les N dernières entrées Redis pour simuler un live feed."""
    keys = redis_client.keys("recs:user:*")
    activity = []
    for key in keys:
        raw = redis_client.get(key)
        if raw:
            try:
                data = json.loads(raw)
                activity.append({
                    "user_id": data.get("user_id", ""),
                    "updated_at": data.get("updated_at", ""),
                    "nb_recs": len(data.get("product_ids", [])),
                })
            except Exception:
                continue

    # Tri par updated_at décroissant, limité aux 20 derniers
    activity.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return jsonify({"activity": activity[:20]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=API_PORT, debug=False)