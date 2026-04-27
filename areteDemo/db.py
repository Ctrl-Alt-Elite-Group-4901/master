# areteDemo/db.py
import os
import sys
import sqlite3
from sqlite3 import Connection

DB_NAME = "arete.db"


def get_db_path():
    # When running as a PyInstaller-frozen .exe, sys.frozen is set and
    # sys.executable points to the .exe. We store the DB next to the .exe
    # so it lives in a writable location.
    # When running from source, __file__ gives the package directory as before.
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, DB_NAME)


def get_connection() -> Connection:
    path = get_db_path()
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scores_user_id
        ON scores(user_id, score DESC)
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS run_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            score INTEGER NOT NULL DEFAULT 0,
            objects_hit_total INTEGER NOT NULL DEFAULT 0,
            hit_object_ids TEXT NOT NULL DEFAULT '',
            quiz_total_questions INTEGER NOT NULL DEFAULT 0,
            quiz_correct_count INTEGER NOT NULL DEFAULT 0,
            quiz_incorrect_count INTEGER NOT NULL DEFAULT 0,
            quiz_answers_detail TEXT NOT NULL DEFAULT '[]',
            player_size_px2 REAL NOT NULL DEFAULT 0,
            obstacle_size_px2 REAL NOT NULL DEFAULT 0,
            speed_start_pxps REAL NOT NULL DEFAULT 0,
            speed_avg_pxps REAL NOT NULL DEFAULT 0,
            speed_max_pxps REAL NOT NULL DEFAULT 0,
            speed_end_pxps REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_run_sessions_user_ended
        ON run_sessions(user_id, ended_at DESC)
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_run_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            run_payload TEXT NOT NULL,
            quiz_payload TEXT NOT NULL,
            last_error TEXT NOT NULL DEFAULT '',
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pending_run_uploads_user_created
        ON pending_run_uploads(user_id, created_at ASC)
        """
    )

    conn.commit()
    conn.close()


init_db()
