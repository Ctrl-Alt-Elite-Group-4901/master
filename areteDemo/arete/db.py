# arete/db.py
import sqlite3

DB_NAME = "arete.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER,
            high_score INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()
