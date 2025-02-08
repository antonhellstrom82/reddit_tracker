import requests
import sqlite3
import pandas as pd
import os
import time
import threading
import matplotlib.pyplot as plt
from datetime import datetime
from flask import Flask, jsonify, send_file

# === Konfiguration ===
SUBREDDITS = ["Normalnudes", "gonewild30plus", "Tributeme", "nude_selfie"]
DB_NAME = "reddit_activity.db"

# Reddit API Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USERNAME = os.getenv("REDDIT_USERNAME")
PASSWORD = os.getenv("REDDIT_PASSWORD")
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
            active_users INTEGER NOT NULL,
            subscribers INTEGER NOT NULL,
            active_percentage REAL NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

initialize_database()

# === Skapa Flask-server ===
server = Flask(__name__)

# === Funktion för att autentisera mot Reddit API ===
def get_reddit_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {
        'grant_type': 'password',
        'username': USERNAME,
        'password': PASSWORD
    }
    headers = {'User-Agent': USER_AGENT}
    response = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Failed to get token: {response.status_code}, {response.text}")
        return None

# === Funktion för att hämta och logga aktiva användare ===
def fetch_active_users(subreddit):
    token = get_reddit_token()
    if not token:
        return {"error": "Failed to authenticate with Reddit API"}
    
    url = f"https://oauth.reddit.com/r/{subreddit}/about.json"
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        active_users = data["data"].get("active_user_count", 0)
        subscribers = data["data"].get("subscribers", 0)
        active_percentage = (active_users / subscribers) * 100 if subscribers > 0 else 0
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO active_users (subreddit, active_users, subscribers, active_percentage) 
            VALUES (?, ?, ?, ?)
        """, (subreddit, active_users, subscribers, active_percentage))
        conn.commit()
        conn.close()
        
        return {"active_users": active_users, "subscribers": subscribers, "active_percentage": active_percentage}
    else:
        return {"error": f"Failed to fetch data. Status code: {response.status_code}"}

# === Automatisk loggning var 15:e minut ===
def log_active_users():
    while True:
        for subreddit in SUBREDDITS:
            fetch_active_users(subreddit)
        print(f"[LOG] Data loggad vid {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(900)  # Vänta i 15 minuter

# Starta loggning i en separat tråd
t = threading.Thread(target=log_active_users, daemon=True)
t.start()

# === API-endpoint för att hämta aktiva användare ===
@server.route("/api/fetch_users", methods=["GET"])
def api_fetch_users():
    results = {}
    for subreddit in SUBREDDITS:
        data = fetch_active_users(subreddit)
        results[subreddit] = data
    return jsonify(results)

# === API-endpoint för att hämta och visualisera datan ===
@server.route("/api/activity_chart", methods=["GET"])
def activity_chart():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT timestamp, subreddit, active_percentage FROM active_users", conn)
    conn.close()
    
    plt.figure(figsize=(10, 5))
    for subreddit in df["subreddit"].unique():
        sub_df = df[df["subreddit"] == subreddit]
        plt.plot(sub_df["timestamp"], sub_df["active_percentage"], label=subreddit)
    
    plt.xlabel("Tid")
    plt.ylabel("% Aktiva Användare")
    plt.title("Utveckling av aktiva användare i subreddits")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("activity_chart.png")
    plt.close()
    
    return send_file("activity_chart.png", mimetype="image/png")

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
