"""
Chatbot UI server for search-news-twitter.
Serves a web interface at http://localhost:5000 for semantic search across digests.
"""

import time
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template

from graph import build_graph
from logger import init_db, save_log

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

    # Build initial state (mirrors search.py main())
    timestamp = datetime.now(timezone.utc).isoformat()
    initial_state = {
        "timestamp": timestamp,
        "query": query,
        "normalized_query": query,  # Will be updated by query_normalize node
        "source": source,
        "top_k": top_k,
        "date_from": None,
        "explicit_web_detected": False,
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
        "final_output": None,
        "errors": [],
        "duration_ms": None,
        "total_llm_tokens_in": 0,
        "total_llm_tokens_out": 0,
    }

    start_ms = time.monotonic()
    final_state = None
    error_msg = None

    try:
        # Invoke the graph
        final_state = graph.invoke(initial_state)
    except Exception as e:
        error_msg = str(e)
        print(f"Error during graph invocation: {error_msg}")

    duration_ms = int((time.monotonic() - start_ms) * 1000)

    if error_msg:
        return jsonify({"error": f"Search failed: {error_msg}"}), 500

    # Deduplicate sources by (source_type, date, author, title)
    unique_sources = {}
    for meta in final_state.get("metas", []):
        key = (meta.get("source_type"), meta.get("date"), meta.get("author"), meta.get("title"))
        if key not in unique_sources:
            unique_sources[key] = meta

    sources = list(unique_sources.values())

    # Build response
    response = {
        "answer": final_state.get("final_output") or "",
        "sources": sources,
        "tokens_in": final_state.get("total_llm_tokens_in", 0),
        "tokens_out": final_state.get("total_llm_tokens_out", 0),
        "duration_ms": duration_ms,
        "path": _classify_path(final_state),
        "judge_score": final_state.get("judge_score"),
        "web_result_count": final_state.get("web_result_count", 0),
    }

    # Log the search (if logging is available)
    try:
        distances = final_state.get("distances", [])
        log = {
            "timestamp": timestamp,
            "query": query,
            "normalized_query": final_state.get("normalized_query"),
            "explicit_web_detected": final_state.get("explicit_web_detected", False),
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
            "final_output": final_state.get("final_output"),
            "duration_ms": duration_ms,
            "total_llm_tokens_in": final_state.get("total_llm_tokens_in", 0),
            "total_llm_tokens_out": final_state.get("total_llm_tokens_out", 0),
        }
        if final_state.get("errors"):
            log["error"] = "; ".join(final_state["errors"])
        save_log(log)
    except Exception as e:
        print(f"Warning: Failed to log search: {e}")

    return jsonify(response), 200


def _classify_path(state):
    """Classify which path the search took."""
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
    print("Starting search-news-twitter chatbot UI...")
    print("Open http://localhost:5001 in your browser")
    app.run(debug=False, port=5001)
