CREATE TABLE IF NOT EXISTS players (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  display_name TEXT NOT NULL,
  username TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL,
  completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
  FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_run_sessions_player_ended
ON run_sessions(player_id, ended_at DESC);

CREATE TABLE IF NOT EXISTS dev_export_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL,
  requester TEXT NOT NULL DEFAULT 'unknown',
  exported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dev_export_audit_player_time
ON dev_export_audit(player_id, exported_at DESC);
