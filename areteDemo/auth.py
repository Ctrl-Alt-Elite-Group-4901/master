from typing import Optional, Dict
from areteDemo import db

def signup(first_name: str, last_name: str, email: str, password: str) -> int:
    """
    Create a new user. Returns user id.
    Raises sqlite3.IntegrityError if email already exists.
    """
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
        (first_name.strip(), last_name.strip(), email.strip().lower(), password),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid

def find_user_by_email(email: str) -> Optional[Dict]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def validate_login(email: str, password: str) -> Optional[int]:
    """
    Return user id if email/password match, else None.
    """
    user = find_user_by_email(email)
    if user and user.get("password") == password:
        return user.get("id")
    return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name, email FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_user(user_id: int, first_name: str, last_name: str, email: str) -> bool:
    """Update user information. Returns True on success."""
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET first_name = ?, last_name = ?, email = ? WHERE id = ?",
            (first_name.strip(), last_name.strip(), email.strip().lower(), user_id)
        )
        conn.commit()
        success = cur.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        conn.close()
        raise e

def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change user password. Returns True on success."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    
    if not row or row['password'] != old_password:
        conn.close()
        return False
    
    cur.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user_id))
    conn.commit()
    success = cur.rowcount > 0
    conn.close()
    return success

def delete_user(user_id: int) -> bool:
    """Delete user account. Returns True on success."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    success = cur.rowcount > 0
    conn.close()
    return success

def add_score(user_id: int, score: int):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO scores (user_id, score) VALUES (?, ?)", (user_id, int(score)))
    conn.commit()
    conn.close()

def get_user_scores(user_id: int, limit: int = 10):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, score FROM scores WHERE user_id = ? ORDER BY score DESC LIMIT ?",
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

