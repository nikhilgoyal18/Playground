"""
SQLite-backed search session logger.
All DB logic is isolated here. Import only init_db() and save_log() from other modules.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "search_logs.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS searches (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp                   TEXT NOT NULL,
    query                       TEXT NOT NULL,
    normalized_query            TEXT,
    duration_ms                 INTEGER,

    explicit_web_detected       INTEGER NOT NULL DEFAULT 0,

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

    final_output                TEXT,
    error                       TEXT,

    total_llm_tokens_in         INTEGER,
    total_llm_tokens_out        INTEGER
)
"""

INSERT_SQL = """
INSERT INTO searches (
    timestamp, query, normalized_query, duration_ms,
    explicit_web_detected,
    internal_attempted, top_chunk_distance, chunks_passed_threshold,
    judge_attempted, judge_score, judge_quality, judge_intent_understood,
    judge_reasoning, judge_parse_error,
    internal_answer_generated, internal_no_content_response, internal_succeeded,
    web_attempted, web_was_fallback, web_result_count, web_succeeded,
    final_output, error, total_llm_tokens_in, total_llm_tokens_out
) VALUES (
    :timestamp, :query, :normalized_query, :duration_ms,
    :explicit_web_detected,
    :internal_attempted, :top_chunk_distance, :chunks_passed_threshold,
    :judge_attempted, :judge_score, :judge_quality, :judge_intent_understood,
    :judge_reasoning, :judge_parse_error,
    :internal_answer_generated, :internal_no_content_response, :internal_succeeded,
    :web_attempted, :web_was_fallback, :web_result_count, :web_succeeded,
    :final_output, :error, :total_llm_tokens_in, :total_llm_tokens_out
)
"""


def init_db():
    """Create the DB and table if they don't exist. Safe to call on every run."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Enable WAL mode to prevent locking issues with concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


def save_log(log: dict):
    """
    Write a completed log dict to the DB. All fields are written via named
    parameters; missing keys fall back to None naturally via dict.get().
    Caller wraps this in try/except — failures must not crash the search flow.
    """
    row = {
        "timestamp": log.get("timestamp"),
        "query": log.get("query"),
        "normalized_query": log.get("normalized_query"),
        "duration_ms": log.get("duration_ms"),
        "explicit_web_detected": int(log.get("explicit_web_detected", False)),
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
        "final_output": _truncate(log.get("final_output"), 2000),
        "error": log.get("error"),
        "total_llm_tokens_in": log.get("total_llm_tokens_in"),
        "total_llm_tokens_out": log.get("total_llm_tokens_out"),
    }
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute(INSERT_SQL, row)
        conn.commit()
        # Explicit WAL checkpoint to flush to disk immediately
        conn.execute("PRAGMA wal_checkpoint(RESTART)")
        conn.commit()


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
