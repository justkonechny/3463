import sqlite3, os

os.makedirs("data", exist_ok=True)

PATH = f"data/calgary_justin-mac.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    start_date TEXT,
    trip_id TEXT,
    stop_sequence INTEGER,
    route_id TEXT,
    stop_id TEXT,
    predicted_ts INTEGER,
    trip_status TEXT,
    feed_ts INTEGER,
    fetched_ts INTEGER,
    PRIMARY KEY (start_date, trip_id, stop_sequence)
    );
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    routes TEXT,
    effect TEXT,
    active_start INTEGER,
    active_end INTEGER,
    description TEXT,
    first_seen INTEGER,
    last_seen INTEGER
    );
CREATE TABLE IF NOT EXISTS weather (
    entry_id TEXT PRIMARY KEY,
    title TEXT,
    warning_type TEXT,
    published INTEGER,
    updated INTEGER,
    first_seen INTEGER,
    last_seen INTEGER
    );
CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    fetched_ts INTEGER,
    machine TEXT,
    http_status INTEGER,
    feed_ts INTEGER,
    entity_count INTEGER,
    rows_written INTEGER,
    error TEXT
    );
"""

def get_connection():
    conn = sqlite3.connect(PATH)
    conn.executescript(SCHEMA)
    return conn