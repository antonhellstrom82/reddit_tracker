import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, jsonify, send_file
import io
import sqlite3
import os

app = Flask(__name__)

def get_data():
    conn = sqlite3.connect("reddit_activity.db")
    df = pd.read_sql_query("SELECT * FROM activity", conn)
    conn.close()
    return df

def smooth_data(data, window=5):
    return data.rolling(window=window, min_periods=1).mean()

@app.route("/api/activity_chart")
def activity_chart():
    df = get_data()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ['blue', 'orange', 'green', 'red']
    
    for i, subreddit in enumerate(df['subreddit'].unique()):
        sub_df = df[df['subreddit'] == subreddit]
        
        # Sort by timestamp
        sub_df = sub_df.sort_values(by='timestamp')
        
        # Scatter plot for raw data
        ax.scatter(sub_df['timestamp'], sub_df['active_users'], color=colors[i], alpha=0.5, label=subreddit, s=30)
        
        # Trend line
        smoothed = smooth_data(sub_df['active_users'], window=5)
        ax.plot(sub_df['timestamp'], smoothed, color=colors[i], linewidth=2)
    
    ax.set_title("Utveckling av aktiva användare i subreddits")
    ax.set_xlabel("Tid")
    ax.set_ylabel("Antal Aktiva Användare")
    ax.legend()
    
    # Anpassar x-axeln för att förhindra överlappning
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))  # Max 10 etiketter på x-axeln
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    
    return send_file(img, mimetype='image/png')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
