import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib import error as urlerror
from urllib import parse, request

from areteDemo import db

try:
    import keyring
    _KEYRING_AVAILABLE = True
except Exception:
    keyring = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False


_KEYRING_SERVICE = "arete-cloud"
_KEYRING_USERNAME = "admin_token"
MAX_EXPORTED_QUIZ_QUESTION_COLUMNS = 25
_EXPORT_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_CLOUD_FILE_CONFIG_ERROR = ""


class CloudAuthError(Exception):
    """Raised when the Worker rejects our credentials (HTTP 401)."""
    pass


class RunSavePendingError(Exception):
    """Raised when a cloud-required run is queued locally for retry."""

    def __init__(self, message: str, pending_upload_id: int, original_error: Exception):
        super().__init__(message)
        self.pending_upload_id = pending_upload_id
        self.original_error = original_error


@dataclass(frozen=True)
class RunSaveResult:
    storage: str
    record_id: int


def _display_name(first_name: str | None, last_name: str | None, email: str) -> str:
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    full = f"{first} {last}".strip()
    return full if full else email


def _username_from_email(email: str) -> str:
    if "@" in email:
        return email.split("@", 1)[0]
    return email


def _csv_safe(value: Any) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def _parse_quiz_answers(raw_value: Any) -> list[dict[str, Any]]:
    if isinstance(raw_value, list):
        answers = raw_value
    else:
        try:
            answers = json.loads(str(raw_value or "[]"))
        except Exception:
            answers = []

    if not isinstance(answers, list):
        return []

    parsed: list[dict[str, Any]] = []
    for item in answers:
        if isinstance(item, dict):
            parsed.append(item)
    return parsed


def _format_answer_text(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return text if text else "-"


def _quiz_answer_summary(answers: list[dict[str, Any]]) -> str:
    if not answers:
        return "No quiz answers recorded."

    parts: list[str] = []
    for index, answer in enumerate(answers, start=1):
        order = answer.get("question_order") or index
        question = _format_answer_text(answer.get("question_text"))
        selected = _format_answer_text(answer.get("selected_text"))
        correct = _format_answer_text(answer.get("correct_text"))
        result = "Correct" if bool(answer.get("is_correct")) else f"Incorrect; correct answer: {correct}"
        parts.append(f"Q{order}: {question} - Player answered: {selected} - {result}")
    return " | ".join(parts)


def _quiz_answer_cells(answers: list[dict[str, Any]], max_answers: int) -> list[str]:
    cells: list[str] = []
    for index in range(max_answers):
        answer = answers[index] if index < len(answers) else {}
        is_correct = answer.get("is_correct")
        cells.extend(
            [
                _format_answer_text(answer.get("question_text")),
                _format_answer_text(answer.get("selected_text")),
                _format_answer_text(answer.get("correct_text")),
                "Correct" if is_correct is True else "Incorrect" if is_correct is False else "-",
            ]
        )
    return cells


def _load_cloud_file_config() -> dict[str, Any]:
    global _CLOUD_FILE_CONFIG_ERROR
    _CLOUD_FILE_CONFIG_ERROR = ""
    candidates = [
        os.path.join(os.path.dirname(db.get_db_path()), "cloud_config.json"),
        os.path.join(os.path.dirname(__file__), "cloud_config.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        config_label = f"cloud_config.json near {os.path.basename(os.path.dirname(path)) or 'the app'}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError:
            _CLOUD_FILE_CONFIG_ERROR = f"{config_label} is not valid JSON."
            continue
        except OSError:
            _CLOUD_FILE_CONFIG_ERROR = f"{config_label} could not be read."
            continue
        if isinstance(raw, dict):
            _CLOUD_FILE_CONFIG_ERROR = ""
            return raw
        _CLOUD_FILE_CONFIG_ERROR = f"{config_label} must contain a JSON object."
    return {}


_CLOUD_FILE_CONFIG = _load_cloud_file_config()


def get_cloud_config_error() -> str:
    return _CLOUD_FILE_CONFIG_ERROR


def _cloud_not_configured_message() -> str:
    return get_cloud_config_error() or "Cloud API is not configured."


def _config_value(key: str, env_key: str, default: Any = None) -> Any:
    env = os.getenv(env_key)
    if env is not None:
        return env
    return _CLOUD_FILE_CONFIG.get(key, default)


def _api_base_url() -> str:
    return str(_config_value("api_base_url", "ARETE_API_BASE_URL", "")).strip().rstrip("/")


def _validated_api_base_url() -> str:
    base = _api_base_url()
    if not base:
        raise RuntimeError(_cloud_not_configured_message())
    parsed = parse.urlparse(base)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    is_local_dev = host in {"localhost", "127.0.0.1", "::1"}
    if not parsed.netloc or scheme not in {"http", "https"}:
        raise RuntimeError("Cloud API base URL is invalid. Check cloud_config.json or ARETE_API_BASE_URL.")
    if scheme != "https" and not is_local_dev:
        raise RuntimeError("Cloud API base URL must use https:// outside local development.")
    return base


def _keyring_get_token() -> str:
    if not _KEYRING_AVAILABLE:
        return ""
    try:
        value = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    except Exception:
        return ""
    return (value or "").strip()


def save_admin_token(token: str) -> None:
    """Persist the admin token to the OS credential store (Windows DPAPI / macOS Keychain / Secret Service)."""
    value = (token or "").strip()
    if not value:
        raise ValueError("Token cannot be empty.")
    if not _KEYRING_AVAILABLE:
        raise RuntimeError("Secure credential storage is unavailable on this system.")
    keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, value)


def clear_admin_token() -> None:
    """Delete any admin token stored in the OS credential store."""
    if not _KEYRING_AVAILABLE:
        return
    try:
        keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    except Exception:
        # Missing entry is fine; ignore other backend errors so disconnect is best-effort.
        pass


def has_admin_token() -> bool:
    return bool(_admin_token())


def _admin_token() -> str:
    saved = _keyring_get_token()
    if saved:
        return saved
    return (os.getenv("ARETE_API_ADMIN_TOKEN") or "").strip()


def verify_and_save_admin_token(token: str) -> None:
    """Test the token against the Worker, then persist it only on success."""
    value = (token or "").strip()
    if not value:
        raise ValueError("Token cannot be empty.")
    base_url = _validated_api_base_url()

    url = f"{base_url}/api/v1/dev/players"
    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": "Arete-Desktop-Client/1.0",
        "Authorization": f"Bearer {value}",
    }
    client_key = _client_key()
    if client_key:
        headers["X-Client-Key"] = client_key

    req = request.Request(url=url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=_request_timeout_seconds()) as response:
            response.read()
    except urlerror.HTTPError as exc:
        if exc.code == 401:
            raise CloudAuthError("The Worker rejected that token.") from exc
        raise RuntimeError(f"Cloud API error {exc.code}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Cloud API request failed: {exc.reason}") from exc

    save_admin_token(value)


def _client_key() -> str:
    return str(_config_value("client_key", "ARETE_API_CLIENT_KEY", "")).strip()


def _request_timeout_seconds() -> float:
    raw = _config_value("timeout_seconds", "ARETE_API_TIMEOUT_SECONDS", "12")
    try:
        val = float(raw)
        if val <= 0:
            return 12.0
        return val
    except Exception:
        return 12.0


def is_cloud_required() -> bool:
    raw = str(_config_value("require_cloud", "ARETE_API_REQUIRE_CLOUD", "0")).strip().lower()
    return raw in ("1", "true", "yes", "on")


def is_cloud_enabled() -> bool:
    return bool(_api_base_url())


def _json_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    admin: bool = False,
) -> dict[str, Any]:
    base = _validated_api_base_url()

    url = f"{base}{path}"
    body = None
    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": "Arete-Desktop-Client/1.0",
    }

    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json"

    client_key = _client_key()
    if client_key:
        headers["X-Client-Key"] = client_key

    if admin:
        token = _admin_token()
        if not token:
            raise RuntimeError("Missing admin token. Connect in Player Directory or set ARETE_API_ADMIN_TOKEN.")
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url=url, data=body, headers=headers, method=method)

    try:
        with request.urlopen(req, timeout=_request_timeout_seconds()) as response:
            data = response.read().decode("utf-8")
            try:
                parsed = json.loads(data) if data else {}
            except json.JSONDecodeError as exc:
                raise RuntimeError("Cloud API returned invalid JSON.") from exc
            if not isinstance(parsed, dict):
                raise RuntimeError("Cloud API returned JSON, but not the expected object response.")
            return parsed
    except urlerror.HTTPError as exc:
        if exc.code == 401:
            raise CloudAuthError("Cloud rejected credentials.") from exc
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"Cloud API error {exc.code}: {detail}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Cloud API request failed: {exc.reason}") from exc


def _download_csv(path: str) -> tuple[bytes, str]:
    base = _validated_api_base_url()

    url = f"{base}{path}"
    headers: dict[str, str] = {
        "Accept": "text/csv",
        "User-Agent": "Arete-Desktop-Client/1.0",
    }
    client_key = _client_key()
    if client_key:
        headers["X-Client-Key"] = client_key

    token = _admin_token()
    if not token:
        raise RuntimeError("Missing admin token. Connect in Player Directory or set ARETE_API_ADMIN_TOKEN.")
    headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url=url, headers=headers, method="GET")

    try:
        with request.urlopen(req, timeout=_request_timeout_seconds()) as response:
            data = response.read()
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = ""
            marker = "filename="
            lower = content_disposition.lower()
            idx = lower.find(marker)
            if idx >= 0:
                filename = content_disposition[idx + len(marker):].strip().strip('"').strip("'")
            return data, filename
    except urlerror.HTTPError as exc:
        if exc.code == 401:
            raise CloudAuthError("Cloud rejected credentials.") from exc
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"Cloud CSV export failed {exc.code}: {detail}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Cloud CSV export request failed: {exc.reason}") from exc


def _safe_export_filename(filename: str, player_id: int) -> str:
    raw_name = parse.unquote((filename or "").strip())
    name = os.path.basename(raw_name)
    name = _EXPORT_FILENAME_RE.sub("_", name).strip("._")
    if not name:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name = f"player_{int(player_id)}_runs_{timestamp}"
    if not name.lower().endswith(".csv"):
        name = f"{name}.csv"
    if len(name) > 128:
        stem = name[:-4]
        name = f"{stem[:124]}.csv"
    return name


def _get_local_user(user_id: int) -> dict[str, Any] | None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, first_name, last_name, email FROM users WHERE id = ?",
        (int(user_id),),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def _payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True)


def _queue_pending_run_upload(
    user_id: int,
    run_payload: dict[str, Any],
    quiz_payload: dict[str, Any],
    error_message: str,
) -> int:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pending_run_uploads (
            user_id,
            run_payload,
            quiz_payload,
            last_error
        ) VALUES (?, ?, ?, ?)
        """,
        (
            int(user_id),
            _payload_json(run_payload),
            _payload_json(quiz_payload),
            str(error_message)[:1000],
        ),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def _delete_pending_run_upload(upload_id: int) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_run_uploads WHERE id = ?", (int(upload_id),))
    conn.commit()
    conn.close()


def _mark_pending_run_upload_failed(upload_id: int, error_message: str) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE pending_run_uploads
        SET
            last_error = ?,
            retry_count = retry_count + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (str(error_message)[:1000], int(upload_id)),
    )
    conn.commit()
    conn.close()


def _pending_upload_rows(user_id: int | None = None, limit: int = 25) -> list[dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    if user_id is None:
        cur.execute(
            """
            SELECT id, user_id, run_payload, quiz_payload
            FROM pending_run_uploads
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (int(limit),),
        )
    else:
        cur.execute(
            """
            SELECT id, user_id, run_payload, quiz_payload
            FROM pending_run_uploads
            WHERE user_id = ?
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def count_pending_run_uploads(user_id: int | None = None) -> int:
    conn = db.get_connection()
    cur = conn.cursor()
    if user_id is None:
        cur.execute("SELECT COUNT(*) AS total FROM pending_run_uploads")
    else:
        cur.execute(
            "SELECT COUNT(*) AS total FROM pending_run_uploads WHERE user_id = ?",
            (int(user_id),),
        )
    row = cur.fetchone()
    conn.close()
    return int(row["total"] if row else 0)


def _decode_pending_payload(raw_value: Any, upload_id: int, payload_name: str) -> dict[str, Any]:
    try:
        decoded = json.loads(str(raw_value or "{}"))
    except Exception as exc:
        raise RuntimeError(f"Pending upload {upload_id} has invalid {payload_name}.") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError(f"Pending upload {upload_id} has invalid {payload_name}.")
    return decoded


def _local_save_completed_run(user_id: int, run_payload: dict[str, Any], quiz_payload: dict[str, Any]) -> int:
    hit_ids = run_payload.get("hit_object_ids", [])
    if not isinstance(hit_ids, list):
        hit_ids = []
    hit_ids_text = "|".join(str(item) for item in hit_ids)

    answers_detail = quiz_payload.get("answers", [])
    if not isinstance(answers_detail, list):
        answers_detail = []

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO run_sessions (
            user_id,
            started_at,
            ended_at,
            score,
            objects_hit_total,
            hit_object_ids,
            quiz_total_questions,
            quiz_correct_count,
            quiz_incorrect_count,
            quiz_answers_detail,
            player_size_px2,
            obstacle_size_px2,
            speed_start_pxps,
            speed_avg_pxps,
            speed_max_pxps,
            speed_end_pxps
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(user_id),
            str(run_payload.get("started_at", "")),
            str(run_payload.get("ended_at", "")),
            int(run_payload.get("score", 0)),
            int(run_payload.get("objects_hit_total", 0)),
            hit_ids_text,
            int(quiz_payload.get("quiz_total_questions", 0)),
            int(quiz_payload.get("quiz_correct_count", 0)),
            int(quiz_payload.get("quiz_incorrect_count", 0)),
            json.dumps(answers_detail, ensure_ascii=True),
            float(run_payload.get("player_size_px2", 0.0)),
            float(run_payload.get("obstacle_size_px2", 0.0)),
            float(run_payload.get("speed_start_pxps", 0.0)),
            float(run_payload.get("speed_avg_pxps", 0.0)),
            float(run_payload.get("speed_max_pxps", 0.0)),
            float(run_payload.get("speed_end_pxps", 0.0)),
        ),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def _local_list_players_for_directory() -> list[dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            u.id,
            u.first_name,
            u.last_name,
            u.email,
            COUNT(rs.id) AS run_count,
            MAX(rs.ended_at) AS last_run_at
        FROM users u
        LEFT JOIN run_sessions rs
            ON rs.user_id = u.id
        GROUP BY u.id, u.first_name, u.last_name, u.email
        ORDER BY LOWER(u.email) ASC
        """
    )
    rows = cur.fetchall()
    conn.close()

    players: list[dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        email = data.get("email", "")
        players.append(
            {
                "id": data["id"],
                "display_name": _display_name(data.get("first_name"), data.get("last_name"), email),
                "username": _username_from_email(email),
                "email": email,
                "run_count": int(data.get("run_count") or 0),
                "last_run_at": data.get("last_run_at"),
            }
        )
    return players


def _local_get_player_runs(user_id: int) -> list[dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id,
            user_id,
            started_at,
            ended_at,
            score,
            objects_hit_total,
            hit_object_ids,
            quiz_total_questions,
            quiz_correct_count,
            quiz_incorrect_count,
            quiz_answers_detail,
            player_size_px2,
            obstacle_size_px2,
            speed_start_pxps,
            speed_avg_pxps,
            speed_max_pxps,
            speed_end_pxps
        FROM run_sessions
        WHERE user_id = ?
        ORDER BY ended_at DESC, id DESC
        """,
        (int(user_id),),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def _local_export_player_runs_csv(user_id: int) -> str:
    user = _get_local_user(user_id)
    if not user:
        raise ValueError("Player not found.")

    runs = _local_get_player_runs(user_id)
    base_dir = os.path.dirname(db.get_db_path())
    export_dir = os.path.join(base_dir, "exports")
    os.makedirs(export_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"player_{int(user_id)}_runs_{timestamp}.csv"
    full_path = os.path.join(export_dir, filename)

    display_name = _display_name(user.get("first_name"), user.get("last_name"), user["email"])
    username = _username_from_email(user["email"])
    quiz_answers_by_run = [
        _parse_quiz_answers(run.get("quiz_answers_detail", "[]"))
        for run in runs
    ]
    max_quiz_answers = max((len(answers) for answers in quiz_answers_by_run), default=0)
    exported_quiz_answer_columns = min(max_quiz_answers, MAX_EXPORTED_QUIZ_QUESTION_COLUMNS)
    has_extra_quiz_answers = max_quiz_answers > exported_quiz_answer_columns
    quiz_answer_headers: list[str] = []
    for index in range(1, exported_quiz_answer_columns + 1):
        quiz_answer_headers.extend(
            [
                f"Q{index} Question",
                f"Q{index} Player Answer",
                f"Q{index} Correct Answer",
                f"Q{index} Result",
            ]
        )
    if has_extra_quiz_answers:
        quiz_answer_headers.append("Additional Quiz Answers Count")

    with open(full_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Player Name",
                "Username",
                "Email",
                "Run ID",
                "Run Started",
                "Run Ended",
                "Score",
                "Obstacles Hit",
                "Hit Obstacle IDs",
                "Quiz Total Questions",
                "Quiz Correct Answers",
                "Quiz Incorrect Answers",
                "Quiz Answers Summary",
                *quiz_answer_headers,
                "Player Size (px sq)",
                "Obstacle Size (px sq)",
                "Speed at Start (px/s)",
                "Average Speed (px/s)",
                "Peak Speed (px/s)",
                "Speed at End (px/s)",
            ]
        )
        for run, answers in zip(runs, quiz_answers_by_run):
            writer.writerow(
                [
                    _csv_safe(display_name),
                    _csv_safe(username),
                    _csv_safe(user["email"]),
                    run["id"],
                    _csv_safe(run.get("started_at", "")),
                    _csv_safe(run.get("ended_at", "")),
                    run.get("score", 0),
                    run.get("objects_hit_total", 0),
                    _csv_safe(run.get("hit_object_ids", "")),
                    run.get("quiz_total_questions", 0),
                    run.get("quiz_correct_count", 0),
                    run.get("quiz_incorrect_count", 0),
                    _csv_safe(_quiz_answer_summary(answers)),
                    *[_csv_safe(cell) for cell in _quiz_answer_cells(answers, exported_quiz_answer_columns)],
                    *([max(0, len(answers) - exported_quiz_answer_columns)] if has_extra_quiz_answers else []),
                    run.get("player_size_px2", 0.0),
                    run.get("obstacle_size_px2", 0.0),
                    run.get("speed_start_pxps", 0.0),
                    run.get("speed_avg_pxps", 0.0),
                    run.get("speed_max_pxps", 0.0),
                    run.get("speed_end_pxps", 0.0),
                ]
            )

    return full_path


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _send_completed_run_to_cloud(
    user_id: int,
    run_payload: dict[str, Any],
    quiz_payload: dict[str, Any],
) -> int:
    user = _get_local_user(user_id)
    if not user:
        raise RuntimeError("Cannot sync run: local player profile not found.")

    payload = {
        "player_name": _display_name(user.get("first_name"), user.get("last_name"), user["email"]),
        "player_username": _username_from_email(user["email"]),
        "player_email": user["email"],
        "run": {
            "started_at": str(run_payload.get("started_at", "")),
            "ended_at": str(run_payload.get("ended_at", "")),
            "score": int(run_payload.get("score", 0)),
            "objects_hit_total": int(run_payload.get("objects_hit_total", 0)),
            "hit_object_ids": _as_list(run_payload.get("hit_object_ids", [])),
            "player_size_px2": float(run_payload.get("player_size_px2", 0.0)),
            "obstacle_size_px2": float(run_payload.get("obstacle_size_px2", 0.0)),
            "speed_start_pxps": float(run_payload.get("speed_start_pxps", 0.0)),
            "speed_avg_pxps": float(run_payload.get("speed_avg_pxps", 0.0)),
            "speed_max_pxps": float(run_payload.get("speed_max_pxps", 0.0)),
            "speed_end_pxps": float(run_payload.get("speed_end_pxps", 0.0)),
        },
        "quiz": {
            "quiz_total_questions": int(quiz_payload.get("quiz_total_questions", 0)),
            "quiz_correct_count": int(quiz_payload.get("quiz_correct_count", 0)),
            "quiz_incorrect_count": int(quiz_payload.get("quiz_incorrect_count", 0)),
            "answers": _as_list(quiz_payload.get("answers", [])),
        },
    }

    response = _json_request("POST", "/api/v1/runs", payload=payload, admin=False)
    session_id = response.get("session_id")
    if isinstance(session_id, int):
        return session_id
    if isinstance(session_id, str) and session_id.isdigit():
        return int(session_id)
    return 0


def retry_pending_run_uploads(user_id: int | None = None, limit: int = 25) -> int:
    """Retry queued cloud-required run uploads. Returns the number uploaded."""
    if not is_cloud_enabled():
        raise RuntimeError("Cloud API is not configured.")

    uploaded = 0
    for row in _pending_upload_rows(user_id=user_id, limit=limit):
        upload_id = int(row["id"])
        try:
            run_payload = _decode_pending_payload(row.get("run_payload"), upload_id, "run payload")
            quiz_payload = _decode_pending_payload(row.get("quiz_payload"), upload_id, "quiz payload")
            _send_completed_run_to_cloud(int(row["user_id"]), run_payload, quiz_payload)
        except Exception as exc:
            _mark_pending_run_upload_failed(upload_id, str(exc))
            if uploaded:
                raise RuntimeError(
                    f"{uploaded} pending run(s) uploaded, but another retry failed: {exc}"
                ) from exc
            raise RuntimeError(f"Pending run retry failed: {exc}") from exc

        _delete_pending_run_upload(upload_id)
        uploaded += 1

    return uploaded


def save_completed_run(user_id: int, run_payload: dict[str, Any], quiz_payload: dict[str, Any]) -> RunSaveResult:
    if is_cloud_enabled():
        try:
            session_id = _send_completed_run_to_cloud(user_id, run_payload, quiz_payload)
            try:
                retry_pending_run_uploads(user_id=user_id)
            except Exception:
                # Current run is safe; older queued runs remain available for manual retry.
                pass
            return RunSaveResult(storage="cloud", record_id=int(session_id))
        except Exception as exc:
            if is_cloud_required():
                try:
                    pending_id = _queue_pending_run_upload(
                        user_id,
                        run_payload,
                        quiz_payload,
                        str(exc),
                    )
                except Exception as queue_exc:
                    raise RuntimeError(
                        "Cloud save failed, and the app could not queue the run locally."
                    ) from queue_exc
                raise RunSavePendingError(
                    "Cloud save failed. The completed run was kept locally for retry.",
                    pending_id,
                    exc,
                ) from exc
            return RunSaveResult(
                storage="local",
                record_id=_local_save_completed_run(user_id, run_payload, quiz_payload),
            )

    return RunSaveResult(
        storage="local",
        record_id=_local_save_completed_run(user_id, run_payload, quiz_payload),
    )


def list_players_for_directory() -> list[dict[str, Any]]:
    if is_cloud_enabled():
        try:
            response = _json_request("GET", "/api/v1/dev/players", admin=True)
            players = response.get("players", [])
            if not isinstance(players, list):
                raise RuntimeError("Unexpected players response.")
            return players
        except CloudAuthError:
            # Surface auth failures so the UI can prompt for a new token.
            raise
        except Exception:
            if is_cloud_required():
                raise
            raise RuntimeError("Cloud player directory is unavailable. Check the connection and try again.")
    raise RuntimeError("Cloud API is not configured. Player Directory requires the cloud database.")


def get_player_runs(player_id: int) -> list[dict[str, Any]]:
    """Look up runs for a player id.

    When cloud is enabled, player_id MUST be the cloud `players.id` returned
    by list_players_for_directory(), not the local `users.id` — those are
    independent sequences and drilling in with the wrong one returns 404 or
    the wrong user.
    """
    if is_cloud_enabled():
        try:
            path = f"/api/v1/dev/players/{int(player_id)}/runs"
            response = _json_request("GET", path, admin=True)
            runs = response.get("runs", [])
            if not isinstance(runs, list):
                raise RuntimeError("Unexpected runs response.")
            return runs
        except CloudAuthError:
            raise
        except Exception:
            if is_cloud_required():
                raise
            raise RuntimeError("Cloud run history is unavailable. Check the connection and try again.")
    raise RuntimeError("Cloud API is not configured. Player run history requires the cloud database.")


def export_player_runs_csv(player_id: int) -> str:
    """Download and save the per-player CSV export.

    player_id must be the cloud `players.id` when cloud is enabled — see
    get_player_runs() for the same caveat.
    """
    if is_cloud_enabled():
        try:
            csv_bytes, filename = _download_csv(f"/api/v1/dev/players/{int(player_id)}/export.csv")
            base_dir = os.path.dirname(db.get_db_path())
            export_dir = os.path.join(base_dir, "exports")
            os.makedirs(export_dir, exist_ok=True)

            filename = _safe_export_filename(filename, int(player_id))

            export_root = os.path.abspath(export_dir)
            full_path = os.path.abspath(os.path.join(export_root, filename))
            if os.path.commonpath([export_root, full_path]) != export_root:
                raise RuntimeError("Invalid export filename.")
            with open(full_path, "wb") as f:
                f.write(csv_bytes)
            return full_path
        except CloudAuthError:
            raise
        except Exception:
            if is_cloud_required():
                raise
            raise RuntimeError("Cloud CSV export is unavailable. Check the connection and try again.")
    raise RuntimeError("Cloud API is not configured. Player CSV export requires the cloud database.")
