"""
SQLite-backed search session logger.
All DB logic is isolated here. Import only init_db() and save_log() from other modules.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "search_logs.db"

CREATE_EVAL_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS eval_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    total           INTEGER NOT NULL,
    passed          INTEGER NOT NULL,
    pass_rate       REAL NOT NULL,
    avg_latency_ms  INTEGER,
    results_json    TEXT NOT NULL
)
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS searches (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp                   TEXT NOT NULL,
    query                       TEXT NOT NULL,
    normalized_query            TEXT,
    duration_ms                 INTEGER,

    explicit_web_detected       INTEGER NOT NULL DEFAULT 0,
    intent_class                TEXT,
    llm_only_used               INTEGER NOT NULL DEFAULT 0,

    internal_attempted          INTEGER NOT NULL DEFAULT 0,
    top_chunk_distance          REAL,
    chunks_passed_threshold     INTEGER,

    judge_attempted             INTEGER NOT NULL DEFAULT 0,
    judge_score                 INTEGER,
    judge_quality               TEXT,
    judge_intent_understood     TEXT,
    judge_reasoning             TEXT,
    judge_parse_error           INTEGER,

    internal_answer_generated   INTEGER,
    internal_no_content_response INTEGER,
    internal_succeeded          INTEGER NOT NULL DEFAULT 0,

    web_attempted               INTEGER NOT NULL DEFAULT 0,
    web_was_fallback            INTEGER,
    web_result_count            INTEGER,
    web_succeeded               INTEGER,
    web_no_content_response     INTEGER,
    hallucination_risk          INTEGER,
    path                        TEXT,

    final_output                TEXT,
    error                       TEXT,

    total_llm_tokens_in         INTEGER,
    total_llm_tokens_out        INTEGER,
    conversation_id             TEXT,
    feedback                    TEXT
)
"""

INSERT_SQL = """
INSERT INTO searches (
    timestamp, query, normalized_query, duration_ms,
    explicit_web_detected, intent_class, llm_only_used,
    internal_attempted, top_chunk_distance, chunks_passed_threshold,
    judge_attempted, judge_score, judge_quality, judge_intent_understood,
    judge_reasoning, judge_parse_error,
    internal_answer_generated, internal_no_content_response, internal_succeeded,
    web_attempted, web_was_fallback, web_result_count, web_succeeded, web_no_content_response, hallucination_risk, path,
    final_output, error, total_llm_tokens_in, total_llm_tokens_out,
    conversation_id
) VALUES (
    :timestamp, :query, :normalized_query, :duration_ms,
    :explicit_web_detected, :intent_class, :llm_only_used,
    :internal_attempted, :top_chunk_distance, :chunks_passed_threshold,
    :judge_attempted, :judge_score, :judge_quality, :judge_intent_understood,
    :judge_reasoning, :judge_parse_error,
    :internal_answer_generated, :internal_no_content_response, :internal_succeeded,
    :web_attempted, :web_was_fallback, :web_result_count, :web_succeeded, :web_no_content_response, :hallucination_risk, :path,
    :final_output, :error, :total_llm_tokens_in, :total_llm_tokens_out,
    :conversation_id
)
"""


def init_db():
    """Create the DB and table if they don't exist. Safe to call on every run."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Enable WAL mode to prevent locking issues with concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(CREATE_EVAL_TABLE_SQL)
        # Migrate existing DBs: add conversation_id column if missing
        try:
            conn.execute("ALTER TABLE searches ADD COLUMN conversation_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Migrate existing DBs: add intent_class column if missing
        try:
            conn.execute("ALTER TABLE searches ADD COLUMN intent_class TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Migrate existing DBs: add llm_only_used column if missing
        try:
            conn.execute("ALTER TABLE searches ADD COLUMN llm_only_used INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Migrate existing DBs: add feedback column if missing
        try:
            conn.execute("ALTER TABLE searches ADD COLUMN feedback TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Migrate existing DBs: add web_no_content_response column if missing
        try:
            conn.execute("ALTER TABLE searches ADD COLUMN web_no_content_response INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Migrate existing DBs: add hallucination_risk column if missing
        try:
            conn.execute("ALTER TABLE searches ADD COLUMN hallucination_risk INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Migrate existing DBs: add path column if missing
        try:
            conn.execute("ALTER TABLE searches ADD COLUMN path TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        conn.commit()


def save_log(log: dict):
    """
    Write a completed log dict to the DB and return the inserted row ID.
    All fields are written via named parameters; missing keys fall back to None naturally via dict.get().
    Caller wraps this in try/except — failures must not crash the search flow.

    Returns:
        int: The auto-increment ID of the inserted row, or None on error
    """
    row = {
        "timestamp": log.get("timestamp"),
        "query": log.get("query"),
        "normalized_query": log.get("normalized_query"),
        "duration_ms": log.get("duration_ms"),
        "explicit_web_detected": int(log.get("explicit_web_detected", False)),
        "intent_class": log.get("intent_class"),
        "llm_only_used": int(log.get("llm_only_used", False)),
        "internal_attempted": int(log.get("internal_attempted", False)),
        "top_chunk_distance": log.get("top_chunk_distance"),
        "chunks_passed_threshold": _opt_int(log.get("chunks_passed_threshold")),
        "judge_attempted": int(log.get("judge_attempted", False)),
        "judge_score": log.get("judge_score"),
        "judge_quality": log.get("judge_quality"),
        "judge_intent_understood": log.get("judge_intent_understood"),
        "judge_reasoning": log.get("judge_reasoning"),
        "judge_parse_error": _opt_int(log.get("judge_parse_error")),
        "internal_answer_generated": _opt_int(log.get("internal_answer_generated")),
        "internal_no_content_response": _opt_int(log.get("internal_no_content_response")),
        "internal_succeeded": int(log.get("internal_succeeded", False)),
        "web_attempted": int(log.get("web_attempted", False)),
        "web_was_fallback": _opt_int(log.get("web_was_fallback")),
        "web_result_count": log.get("web_result_count"),
        "web_succeeded": _opt_int(log.get("web_succeeded")),
        "web_no_content_response": _opt_int(log.get("web_no_content_response")),
        "hallucination_risk": _opt_int(log.get("hallucination_risk")),
        "path": log.get("path"),
        "final_output": _truncate(log.get("final_output"), 2000),
        "error": log.get("error"),
        "total_llm_tokens_in": log.get("total_llm_tokens_in"),
        "total_llm_tokens_out": log.get("total_llm_tokens_out"),
        "conversation_id": log.get("conversation_id"),
    }
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.execute(INSERT_SQL, row)
            inserted_id = cursor.lastrowid
            conn.commit()
            return inserted_id
    except Exception as e:
        print(f"ERROR in save_log: {e}")
        import traceback
        traceback.print_exc()
        raise  # Let caller handle it


def _opt_int(value):
    """Convert True/False/None to 1/0/None for SQLite INTEGER columns."""
    if value is None:
        return None
    return int(value)


def _truncate(text, max_len):
    """Truncate text to max_len characters, or return None if text is None."""
    if text is None:
        return None
    return text[:max_len] if len(text) > max_len else text


def save_eval_run(results: list, passed: int) -> int:
    """
    Persist a completed eval run to the eval_runs table.

    Args:
        results: List of per-test result dicts from run_eval.py
        passed:  Number of tests that passed

    Returns:
        int: The inserted row ID
    """
    import json as _json
    from datetime import datetime, timezone
    total = len(results)
    avg_latency = int(sum(r.get("duration_ms") or 0 for r in results) / total) if total else 0
    pass_rate = round(100 * passed / total, 1) if total else 0.0

    # Strip large debug keys before storing
    slim = [
        {k: v for k, v in r.items() if k != "final_state_keys"}
        for r in results
    ]

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        cursor = conn.execute(
            """INSERT INTO eval_runs (timestamp, total, passed, pass_rate, avg_latency_ms, results_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                total,
                passed,
                pass_rate,
                avg_latency,
                _json.dumps(slim),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def update_feedback(search_id: int, feedback: str) -> bool:
    """
    Update the feedback column for an existing search row.

    Args:
        search_id: The integer primary key of the row to update.
        feedback:  "up" or "down" — stored as TEXT for SQL readability.

    Returns:
        True  — row was found and updated.
        False — no row matched search_id (id not found).
    """
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.execute(
                "UPDATE searches SET feedback = ? WHERE id = ?",
                (feedback, search_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"ERROR in update_feedback: {e}")
        import traceback
        traceback.print_exc()
        return False
