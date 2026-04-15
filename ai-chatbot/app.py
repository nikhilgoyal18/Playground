"""
Chatbot UI server for AI Chatbot.
Serves a web interface at http://localhost:5001 for semantic search and Q&A across digests.
"""

import time
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template

from graph import build_graph
from logger import init_db, save_log, update_feedback

app = Flask(__name__)

# Build the graph once on startup
try:
    graph = build_graph()
except Exception as e:
    print(f"Warning: Failed to build graph on startup: {e}")
    graph = None

# Initialize logging
try:
    init_db()
except Exception:
    pass  # Logging is optional


@app.route("/")
def index():
    """Serve the chatbot UI."""
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    """
    Execute a semantic search query.

    Request JSON:
        {
            "query": "your question",
            "source": "newsletter" | "twitter" | null,
            "top_k": 5
        }

    Response JSON:
        {
            "answer": "...",
            "sources": [...],
            "tokens_in": 123,
            "tokens_out": 456,
            "duration_ms": 789,
            "path": "internal" | "web_fallback" | "explicit_web" | "web",
            "judge_score": 7,
            "web_result_count": 0
        }
    """
    if not graph:
        return jsonify({"error": "Graph not initialized"}), 500

    data = request.get_json() or {}
    query = data.get("query", "").strip()
    source = data.get("source", None)
    top_k = int(data.get("top_k", 5))

    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    # Extract and validate conversation_history
    raw_history = data.get("conversation_history", [])
    conversation_id = data.get("conversation_id", None)
    if not isinstance(conversation_id, str):
        conversation_id = None

    conversation_history = []
    if isinstance(raw_history, list):
        for entry in raw_history:
            if (isinstance(entry, dict) and
                    isinstance(entry.get("role"), str) and
                    entry.get("role") in ("user", "assistant") and
                    isinstance(entry.get("content"), str)):
                conversation_history.append({"role": entry["role"], "content": entry["content"]})
            else:
                print(f"Warning: Dropped malformed conversation_history entry: {entry}")
    # Cap to last 6 entries (3 exchanges) — server-side safety backstop
    conversation_history = conversation_history[-6:]

    # Build initial state (mirrors search.py main())
    timestamp = datetime.now(timezone.utc).isoformat()
    search_id = None  # Will be assigned after logging to DB
    initial_state = {
        "timestamp": timestamp,
        "query": query,
        "normalized_query": query,  # Will be updated by query_normalize node
        "source": source,
        "top_k": top_k,
        "date_from": None,
        "explicit_web_detected": False,
        "intent_class": None,
        "intent_classify_skipped": False,
        "llm_only_answer": None,
        "docs": [],
        "metas": [],
        "distances": [],
        "chunks_passed_threshold": None,
        "judge_score": None,
        "judge_quality": None,
        "judge_intent_understood": None,
        "judge_reasoning": None,
        "judge_parse_error": False,
        "internal_answer": None,
        "internal_answer_generated": None,
        "internal_succeeded": False,
        "internal_no_content_response": False,
        "web_answer": None,
        "web_result_count": 0,
        "web_succeeded": False,
        "web_was_fallback": False,
        "web_no_content_response": False,
        "web_sources": [],
        "hallucination_risk": False,
        "final_output": None,
        "errors": [],
        "duration_ms": None,
        "total_llm_tokens_in": 0,
        "total_llm_tokens_out": 0,
        "conversation_history": conversation_history,
        "conversation_id": conversation_id,
    }

    start_ms = time.monotonic()
    final_state = None
    error_msg = None

    try:
        # Invoke the graph
        final_state = graph.invoke(initial_state)
    except Exception as e:
        error_msg = str(e)
        import traceback
        print(f"Error during graph invocation: {error_msg}")
        traceback.print_exc()

    duration_ms = int((time.monotonic() - start_ms) * 1000)

    if error_msg:
        return jsonify({"error": f"Search failed: {error_msg}"}), 500

    # Deduplicate internal sources by (source_type, date, author, title)
    unique_sources = {}
    for meta in final_state.get("metas", []):
        key = (meta.get("source_type"), meta.get("date"), meta.get("author"), meta.get("title"))
        if key not in unique_sources:
            unique_sources[key] = meta

    sources = list(unique_sources.values())

    # Attach web sources so the UI can display titles + URLs
    web_sources = final_state.get("web_sources", [])

    # Compute path for logging and response
    path = _classify_path(final_state)

    # Log the search (if logging is available) and get the ID
    search_id = None
    print(f"DEBUG: About to log search for query: {query}")
    try:
        distances = final_state.get("distances", [])
        log = {
            "timestamp": timestamp,
            "query": query,
            "normalized_query": final_state.get("normalized_query"),
            "explicit_web_detected": final_state.get("explicit_web_detected", False),
            "intent_class": final_state.get("intent_class"),
            "llm_only_used": final_state.get("intent_class") == "GENERAL" and final_state.get("llm_only_answer") is not None,
            "internal_attempted": final_state.get("chunks_passed_threshold") is not None,
            "top_chunk_distance": distances[0] if distances else None,
            "chunks_passed_threshold": final_state.get("chunks_passed_threshold"),
            "judge_attempted": final_state.get("judge_score") is not None,
            "judge_score": final_state.get("judge_score"),
            "judge_quality": final_state.get("judge_quality"),
            "judge_intent_understood": final_state.get("judge_intent_understood"),
            "judge_reasoning": final_state.get("judge_reasoning"),
            "judge_parse_error": final_state.get("judge_parse_error", False),
            "internal_answer_generated": final_state.get("internal_answer_generated"),
            "internal_no_content_response": final_state.get("internal_no_content_response", False),
            "internal_succeeded": final_state.get("internal_succeeded", False),
            "web_attempted": final_state.get("web_answer") is not None,
            "web_was_fallback": final_state.get("web_was_fallback", False),
            "web_result_count": final_state.get("web_result_count", 0),
            "web_succeeded": final_state.get("web_succeeded", False),
            "web_no_content_response": final_state.get("web_no_content_response", False),
            "hallucination_risk": final_state.get("hallucination_risk", False),
            "path": path,
            "final_output": final_state.get("final_output"),
            "duration_ms": duration_ms,
            "total_llm_tokens_in": final_state.get("total_llm_tokens_in", 0),
            "total_llm_tokens_out": final_state.get("total_llm_tokens_out", 0),
        }
        if final_state.get("errors"):
            log["error"] = "; ".join(final_state["errors"])
        log["conversation_id"] = conversation_id
        search_id = save_log(log)  # Get the database ID
        print(f"DEBUG: Logged search with ID: {search_id}")
    except Exception as e:
        print(f"Warning: Failed to log search: {e}")
        import traceback
        traceback.print_exc()
        search_id = None

    # Build response (after logging to include the ID)
    response = {
        "id": search_id,  # Database row ID for lookup
        "answer": final_state.get("final_output") or "Sorry, I couldn't generate an answer. Please try rephrasing your question.",
        "sources": sources,
        "web_sources": web_sources,
        "tokens_in": final_state.get("total_llm_tokens_in", 0),
        "tokens_out": final_state.get("total_llm_tokens_out", 0),
        "duration_ms": duration_ms,
        "path": path,
        "judge_score": final_state.get("judge_score"),
        "web_result_count": final_state.get("web_result_count", 0),
        "hallucination_risk": final_state.get("hallucination_risk", False),
    }

    return jsonify(response), 200


@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Record a thumbs-up or thumbs-down for a previously logged search.

    Request JSON:
        { "id": <int>, "feedback": "up" | "down" }

    Responses:
        200  { "ok": true }
        400  { "error": "..." }   — bad input
        404  { "error": "Search ID not found" }
    """
    data = request.get_json() or {}

    search_id = data.get("id")
    fb = data.get("feedback")

    if not isinstance(search_id, int):
        return jsonify({"error": "id must be an integer"}), 400
    if fb not in ("up", "down"):
        return jsonify({"error": "feedback must be 'up' or 'down'"}), 400

    found = update_feedback(search_id, fb)
    if not found:
        return jsonify({"error": "Search ID not found"}), 404

    return jsonify({"ok": True}), 200


@app.route("/api/feedback-stats", methods=["GET"])
def feedback_stats():
    """
    Return aggregate feedback statistics for the dashboard.
    """
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).parent / "data" / "search_logs.db"
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback = 'up' THEN 1 ELSE 0 END) as up_count,
                    SUM(CASE WHEN feedback = 'down' THEN 1 ELSE 0 END) as down_count,
                    SUM(CASE WHEN feedback IS NULL THEN 1 ELSE 0 END) as null_count
                FROM searches
            """)
            overall_row = cursor.fetchone()
            total = overall_row['total'] or 0
            up_count = overall_row['up_count'] or 0
            down_count = overall_row['down_count'] or 0
            pct_positive = 0.0 if down_count + up_count == 0 else (100.0 * up_count) / (down_count + up_count)

            # Failures by path
            cursor.execute("""
                SELECT path,
                       SUM(CASE WHEN feedback = 'up' THEN 1 ELSE 0 END) as up_count,
                       SUM(CASE WHEN feedback = 'down' THEN 1 ELSE 0 END) as down_count,
                       COUNT(*) as total
                FROM searches
                WHERE feedback IS NOT NULL
                GROUP BY path
                ORDER BY down_count DESC
            """)
            by_path = [dict(row) for row in cursor.fetchall()]

            # Judge score distribution for negatives
            cursor.execute("""
                SELECT judge_score, COUNT(*) as count
                FROM searches
                WHERE feedback = 'down' AND judge_score IS NOT NULL
                GROUP BY judge_score
                ORDER BY judge_score DESC
            """)
            judge_scores = [dict(row) for row in cursor.fetchall()]

            # Recent 20 feedback (both up and down, combined)
            cursor.execute("""
                SELECT id, timestamp, query, path, judge_score, final_output, feedback
                FROM searches
                WHERE feedback IS NOT NULL
                ORDER BY id DESC
                LIMIT 20
            """)
            recent = []
            for row in cursor.fetchall():
                output_preview = row['final_output'][:100] if row['final_output'] else ""
                recent.append({
                    "id": row['id'],
                    "timestamp": row['timestamp'],
                    "query": row['query'],
                    "path": row['path'],
                    "judge_score": row['judge_score'],
                    "output_preview": output_preview,
                    "feedback": row['feedback']
                })

            return jsonify({
                "overall": {
                    "total": total,
                    "up": up_count,
                    "down": down_count,
                    "null": overall_row['null_count'] or 0,
                    "pct_positive": round(pct_positive, 1)
                },
                "by_path": by_path,
                "judge_scores_on_negatives": judge_scores,
                "recent_negatives": recent
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Serve the feedback dashboard page.
    """
    return render_template("dashboard.html")


def _classify_path(state):
    """Classify which path the search took."""
    if state.get("intent_class") == "GENERAL" and state.get("llm_only_answer") is not None:
        return "llm_only"
    if state.get("explicit_web_detected"):
        return "explicit_web"
    if state.get("web_was_fallback"):
        return "web_fallback"
    if state.get("internal_succeeded"):
        return "internal"
    if state.get("web_succeeded"):
        return "web"
    return "unknown"


if __name__ == "__main__":
    print("Starting AI Chatbot UI...")
    print("Open http://localhost:5001 in your browser")
    app.run(debug=False, port=5001)
