# areteDemo/auth.py
import re
from hmac import compare_digest
from typing import Optional, Dict

from passlib.hash import argon2

from areteDemo import db

# ── Developer mode ─────────────────────────────────────────────────────────────
# Leave email blank and use this password on the login screen to enter dev mode.
# No DB account is created or queried; this check runs before any DB call.
DEV_PASSWORD = "BobRoss5"
MIN_PASSWORD_LENGTH = 4
MAX_EMAIL_LENGTH = 320
_EMAIL_RE = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Z0-9-]{1,63}(?:\.[A-Z0-9-]{1,63})+$",
    re.IGNORECASE,
)


def normalize_email(email: str) -> str:
    normalized = (email or "").strip().lower()
    if len(normalized) > MAX_EMAIL_LENGTH or not _EMAIL_RE.fullmatch(normalized):
        raise ValueError("Please enter a valid email address.")

    _local, domain = normalized.rsplit("@", 1)
    if len(domain) > 255:
        raise ValueError("Please enter a valid email address.")

    labels = domain.split(".")
    if any(not label or label.startswith("-") or label.endswith("-") for label in labels):
        raise ValueError("Please enter a valid email address.")
    return normalized


def _validate_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError("Password must be at least 4 characters.")


def _hash_password(password: str) -> str:
    return argon2.hash(password)


def _is_password_hash(value: str) -> bool:
    return value.startswith("$argon2")


def _verify_password(password: str, stored_password: str) -> bool:
    if _is_password_hash(stored_password):
        try:
            return bool(argon2.verify(password, stored_password))
        except Exception:
            return False
    return compare_digest(password, stored_password)


def _update_password_hash(user_id: int, password: str) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password = ? WHERE id = ?",
        (_hash_password(password), user_id),
    )
    conn.commit()
    conn.close()


def validate_login(email: str, password: str) -> Optional[int | str]:
    """Return user id (int) on success, 'dev' for developer login, else None."""
    if email == "" and password == DEV_PASSWORD:
        return "dev"
    user = find_user_by_email(email)
    if user:
        user_id = user.get("id")
        stored_password = str(user.get("password") or "")
        if _verify_password(password, stored_password):
            if isinstance(user_id, int) and not _is_password_hash(stored_password):
                _update_password_hash(user_id, password)
            return user_id
    return None


def signup(first_name: str, last_name: str, email: str, password: str) -> int:
    """
    Create a new user. Returns user id.
    Raises sqlite3.IntegrityError if email already exists.
    """
    normalized_email = normalize_email(email)
    _validate_password(password)

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
        (first_name.strip(), last_name.strip(), normalized_email, _hash_password(password)),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def find_user_by_email(email: str) -> Optional[Dict]:
    try:
        normalized_email = normalize_email(email)
    except ValueError:
        return None

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (normalized_email,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, first_name, last_name, email FROM users WHERE id = ?", (user_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def update_user(user_id: int, first_name: str, last_name: str, email: str) -> bool:
    """Update user information. Returns True on success."""
    normalized_email = normalize_email(email)
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET first_name = ?, last_name = ?, email = ? WHERE id = ?",
            (first_name.strip(), last_name.strip(), normalized_email, user_id),
        )
        conn.commit()
        success = cur.rowcount > 0
        return success
    finally:
        conn.close()


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change user password. Returns True on success."""
    _validate_password(new_password)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row or not _verify_password(old_password, str(row["password"] or "")):
        conn.close()
        return False
    cur.execute(
        "UPDATE users SET password = ? WHERE id = ?", (_hash_password(new_password), user_id)
    )
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
    cur.execute(
        "INSERT INTO scores (user_id, score) VALUES (?, ?)", (user_id, int(score))
    )
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
