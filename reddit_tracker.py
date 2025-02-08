import requests
import sqlite3
import pandas as pd
import os
import time
from datetime import datetime
from flask import Flask, jsonify

# === Konfiguration ===
SUBREDDITS = ["Normalnudes", "gonewild30plus", "Tributeme", "nude_selfie"]
DB_NAME = "reddit_activity.db"

# Reddit API Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_AGENT = "Mozilla/5.0 (compatible; RedditTrackerBot/1.0; +https://reddit-tracker-jzk5.onrender.com)"

# === Skapa och initiera databasen ===
def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            subreddit TEXT NOT NULL,
            active_users INTEGER NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

initialize_database()

# === Skapa Flask-server ===
server = Flask(__name__)

# === Funktion för att hämta aktiva användare från Reddit ===
def fetch_active_users(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/about.json"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        active_users = data["data"].get("active_user_count", 0)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO active_users (subreddit, active_users) VALUES (?, ?)", (subreddit, active_users))
        conn.commit()
        conn.close()
        return active_users
    else:
        return None

# === API-endpoint för att hämta aktiva användare ===
@server.route("/api/fetch_users", methods=["GET"])
def api_fetch_users():
    results = {}
    for subreddit in SUBREDDITS:
        active_users = fetch_active_users(subreddit)
        results[subreddit] = active_users if active_users is not None else "Error"
    return jsonify(results)

# === API-endpoint för att verifiera databasinnehåll ===
@server.route("/api/check_db", methods=["GET"])
def check_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM active_users")
    count = cursor.fetchone()[0]
    conn.close()
    return jsonify({"record_count": count})

if __name__ == "__main__":
    server.run(debug=True, host="0.0.0.0", port=5000)
