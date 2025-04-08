from flask import Flask, jsonify
import redis
import os

app = Flask(__name__)

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)

@app.route("/debug/queue", methods=["GET"])
def view_order_queue():
    queue = r.lrange("order_queue", 0, -1)
    return jsonify(queue), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000, debug=True)
