import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, jsonify, send_file, request, render_template
import io
import sqlite3
import os
import requests
import time
import threading

app = Flask(__name__, template_folder="templates")

# Reddit API-konfiguration
API_URL = "https://oauth.reddit.com/r/{}/about.json"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USERNAME = os.getenv("REDDIT_USERNAME")
PASSWORD = os.getenv("REDDIT_PASSWORD")
USER_AGENT = "RedditTracker/1.0"

SUBREDDITS = ["Normalnudes", "Gonewild", "RealGirls", "Tributeme"]

# Funktion för att hämta OAuth-token
def get_oauth_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    headers = {"User-Agent": USER_AGENT}
    response = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers)
    token = response.json().get("access_token")
    return token

# Skapa databastabell
def create_table():
    conn = sqlite3.connect("reddit_activity.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subreddit TEXT NOT NULL,
            active_users INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_table()

# Hämta Reddit-data och lagra i databasen
def fetch_and_store_reddit_data():
    token = get_oauth_token()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}
    conn = sqlite3.connect("reddit_activity.db", check_same_thread=False)
    cursor = conn.cursor()
    
    for subreddit in SUBREDDITS:
        response = requests.get(API_URL.format(subreddit), headers=headers)
        if response.status_code == 200:
            data = response.json()
            active_users = data["data"].get("active_user_count", 0)
            cursor.execute("INSERT INTO activity (subreddit, active_users) VALUES (?, ?)", (subreddit, active_users))
            conn.commit()
    conn.close()

# Starta tråd för att hämta data kontinuerligt
def scheduled_fetch():
    while True:
        fetch_and_store_reddit_data()
        time.sleep(300)  # Vänta 5 minuter

thread = threading.Thread(target=scheduled_fetch, daemon=True)
thread.start()

# Hämta data från databasen
def get_data(subreddit):
    conn = sqlite3.connect("reddit_activity.db")
    df = pd.read_sql_query("SELECT * FROM activity WHERE subreddit = ?", conn, params=(subreddit,))
    conn.close()
    return df

@app.route("/")
def index():
    return render_template("index.html", subreddits=SUBREDDITS)

@app.route("/api/activity_chart")
def activity_chart():
    subreddit = request.args.get("subreddit", "Normalnudes")
    df = get_data(subreddit)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['timestamp'], df['active_users'], marker='o', linestyle='-', color='blue', label=subreddit)
    ax.set_title(f"Utveckling av aktiva användare i {subreddit}")
    ax.set_xlabel("Tid")
    ax.set_ylabel("Antal Aktiva Användare")
    ax.legend()
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    
    return send_file(img, mimetype='image/png')

@app.route("/api/timestamps")
def get_timestamps():
    subreddit = request.args.get("subreddit", "Normalnudes")
    df = get_data(subreddit)
    timestamps = df['timestamp'].tolist()
    return jsonify(timestamps)

@app.route("/api/fetch_data", methods=["POST"])
def fetch_data():
    fetch_and_store_reddit_data()
    return jsonify({"status": "Data hämtad"})

@app.route("/activity")
def activity():
    return render_template("activity.html", subreddits=SUBREDDITS)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
