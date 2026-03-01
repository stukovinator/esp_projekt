from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

DB_PATH = 'temps.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON readings(timestamp)
    ''')
    conn.commit()
    conn.close()

def cleanup_old():
    conn = get_db()
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('DELETE FROM readings WHERE timestamp < ?', (cutoff,))
    conn.commit()
    conn.close()

@app.route('/temperature', methods=['GET'])
def get_temp():
    conn = get_db()
    # ostatni odczyt
    last = conn.execute(
        'SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1'
    ).fetchone()
    conn.close()

    if last:
        return jsonify({
            'temperature': last['temperature'],
            'last_updated': last['timestamp']
        })
    return jsonify({'temperature': None, 'last_updated': None})

@app.route('/temperature', methods=['POST'])
def post_temp():
    data = request.get_json()
    temp = data.get('temperature')
    timestamp = data.get('timestamp')

    conn = get_db()
    conn.execute(
        'INSERT INTO readings (temperature, timestamp) VALUES (?, ?)',
        (temp, timestamp)
    )
    conn.commit()
    conn.close()

    cleanup_old()
    return jsonify({'ok': True})

@app.route('/history', methods=['GET'])
def get_history():
    hours = request.args.get('hours', 24, type=int)
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    rows = conn.execute(
        'SELECT temperature, timestamp FROM readings WHERE timestamp > ? ORDER BY timestamp ASC',
        (cutoff,)
    ).fetchall()
    conn.close()

    return jsonify([{'temperature': r['temperature'], 'timestamp': r['timestamp']} for r in rows])

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
