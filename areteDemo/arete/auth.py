import sqlite3
from arete import db

def signup(email, password, first_name="", last_name=""):
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password, first_name, last_name) VALUES (?, ?, ?, ?)",
            (email, password, first_name, last_name)
        )
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO stats (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login(email, password):
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email=? AND password=?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user(user_id):
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT email, first_name, last_name FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(user_id, first_name, last_name):
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET first_name=?, last_name=? WHERE id=?", (first_name, last_name, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stats WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()