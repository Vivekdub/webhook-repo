# webhook-repo/app.py
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import os

load_dotenv()
app = Flask(__name__)

# ==============================
# MongoDB Configuration
# ==============================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "github_webhooks"
COLLECTION_NAME = "events"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
events_collection = db[COLLECTION_NAME]

# ==============================
# Health Check
# ==============================
@app.route("/health", methods=["GET"])
def health():
    return {"status": "running"}, 200

# ==============================
# Webhook Endpoint
# ==============================
@app.route("/webhook", methods=["POST"])
def github_webhook():
    payload = request.json
    headers = request.headers

    event_type = headers.get("X-GitHub-Event")

    if not payload or not event_type:
        return {"error": "Invalid webhook payload"}, 400

    data = parse_github_event(event_type, payload)

    if data:
        events_collection.insert_one(data)
        return {"status": "stored"}, 200

    return {"status": "ignored"}, 200

# ==============================
# Event Parser
# ==============================
def parse_github_event(event_type, payload):
    try:
        # -------- PUSH --------
        if event_type == "push":
            return {
                "type": "push",
                "author": payload.get("pusher", {}).get("name"),
                "from_branch": None,
                "to_branch": payload.get("ref", "").replace("refs/heads/", ""),
                "timestamp": payload.get("head_commit", {}).get("timestamp"),
                "raw": payload
            }

        # -------- PULL REQUEST --------
        if event_type == "pull_request":
            action = payload.get("action")
            pr = payload.get("pull_request", {})

            # MERGE CASE
            if pr.get("merged") is True:
                return {
                    "type": "merge",
                    "author": payload.get("sender", {}).get("login"),
                    "from_branch": pr.get("head", {}).get("ref"),
                    "to_branch": pr.get("base", {}).get("ref"),
                    "timestamp": pr.get("merged_at"),
                    "raw": payload
                }

            # NORMAL PR
            if action in ["opened", "reopened"]:
                return {
                    "type": "pull_request",
                    "author": payload.get("sender", {}).get("login"),
                    "from_branch": pr.get("head", {}).get("ref"),
                    "to_branch": pr.get("base", {}).get("ref"),
                    "timestamp": pr.get("created_at"),
                    "raw": payload
                }

    except Exception as e:
        print("Parse error:", e)

    return None

# ==============================
# Fetch Events API for UI
# ==============================
@app.route("/events", methods=["GET"])
def get_events():
    data = list(events_collection.find({}, {"raw": 0}).sort("timestamp", -1).limit(20))

    for d in data:
        d["_id"] = str(d["_id"])

    return jsonify(data)

@app.route("/")
def home():
    print("CCOOLLLEEDDD")
    return app.send_static_file("index.html")

# ==============================
# App Runner
# ==============================
if __name__ == "__main__":
    app.run(debug=True, port=5000)


# ==============================
# requirements.txt
# ==============================
# flask
# pymongo
# python-dotenv
