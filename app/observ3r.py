from flask import Flask, render_template, jsonify, request
import yaml
import requests
import json
import os
import threading
import time
import shutil

app = Flask("OBSERV3R")

# Read the DEBUG environment variable
debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'

# Environment variable for config file location
CONFIG_PATH = '/config/config.yaml'
DEFAULT_CONFIG_PATH = '/app/config.default.yaml'
config_file_path = os.getenv('CONFIG_FILE', CONFIG_PATH)

# Check if the config file exists, if not copy the default config
if not os.path.exists(CONFIG_PATH):
    print(f"Config file not found. Copying default config to {CONFIG_PATH}...")
    shutil.copy(DEFAULT_CONFIG_PATH, CONFIG_PATH)
    is_first_run = True

# Load the configuration
with open(CONFIG_PATH, 'r') as file:
    config = yaml.safe_load(file)

trackers = config["trackers"] if config else []
refresh_interval_minutes = (
    int(os.getenv("REFRESH_INTERVAL", config.get("refresh_interval", 60))) if config else 60
)
refresh_interval_seconds = refresh_interval_minutes * 60

# Fetch statistics from a single tracker
def fetch_stats(tracker):
    try:
        response = requests.get(
            f"{tracker['address']}/api/user",
            headers={"Authorization": f"Bearer {tracker['api_key']}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        return {
            "tracker": tracker["name"],
            "username": data.get("username", "N/A"),
            "group": data.get("group", {}).get("name", "N/A"),
            "uploaded": data.get("uploaded", 0),
            "downloaded": data.get("downloaded", 0),
            "ratio": round(data.get("uploaded", 0) / data.get("downloaded", 1), 2) if data.get("downloaded", 0) > 0 else "∞",
            "buffer": data.get("uploaded", 0) - data.get("downloaded", 0),
            "seeding": data.get("seeding", 0),
            "leeching": data.get("leeching", 0),
            "seedbonus": data.get("seedbonus", 0),
            "hit_and_runs": data.get("hit_and_runs", 0),
        }
    except requests.exceptions.RequestException as e:
        return {"tracker": tracker["name"], "error": str(e)}

# Update statistics for all trackers
def update_all_stats():
    global stats_cache
    for tracker in trackers:
        stats_cache[tracker["name"]] = fetch_stats(tracker)

# Background thread to auto-refresh stats
def auto_refresh():
    while not is_first_run:
        update_all_stats()
        time.sleep(refresh_interval_seconds)

# Routes
@app.route("/")
def index():
    if is_first_run:
        return (
            "<h1>OBSERV3R: Tracker Stats Dashboard</h1>"
            "<h1>OBSERV3R is running.</h1>"
            "<p>A default configuration file has been created at <b>{config_file_path}</b>.</p>"
            "<p>Please update this file with your trackers and restart the app.</p>"
        )
    return render_template("index.html", refresh_interval=refresh_interval_minutes)

@app.route("/stats", methods=["GET"])
def get_stats():
    return jsonify(list(stats_cache.values()))

@app.route("/refresh", methods=["POST"])
def manual_refresh():
    tracker_name = request.json.get("tracker_name", None)
    if tracker_name:
        # Refresh single tracker
        for tracker in trackers:
            if tracker["name"] == tracker_name:
                stats_cache[tracker_name] = fetch_stats(tracker)
                return jsonify({"status": "refreshed", "tracker": tracker_name})
        return jsonify({"error": "Tracker not found"}), 404
    else:
        # Refresh all trackers
        update_all_stats()
        return jsonify({"status": "all refreshed"})

# Start background thread
if not is_first_run:
    threading.Thread(target=auto_refresh, daemon=True).start()

if __name__ == "__main__":
    # Run the Flask app with the appropriate debug mode based on the DEBUG environment variable
    if not is_first_run:
        update_all_stats()
    print(f"Starting OBSERV3R with config file: {config_file_path}")
    app.run(host="0.0.0.0", port=8383, debug=debug_mode)
