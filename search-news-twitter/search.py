"""
Semantic search across newsletter and Twitter summaries using RAG with LangGraph.
Falls back to live web search (DuckDuckGo) if nothing relevant is found internally.
Jumps straight to web search if the query explicitly asks for current/live data.

Uses LangGraph for orchestration with typed state, per-node retry policies, and
a query normalization step that fixes typos before embedding.

Usage:
    python3 search.py --query "database performance trade-offs"
    python3 search.py --query "RAG systems" --source newsletter --top-k 8
    python3 search.py --query "AI tools" --source twitter --date-from 2026-04-01
    python3 search.py --query "latest MSFT news"
"""

import argparse
import time
from datetime import datetime, timezone

from graph import build_graph
from logger import init_db, save_log


def main():
    parser = argparse.ArgumentParser(
        description="Search newsletter, Twitter summaries, or the web"
    )
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument(
        "--source", choices=["newsletter", "twitter"], help="Filter by source type (internal search only)"
    )
    parser.add_argument(
        "--top-k", "-k", type=int, default=5, help="Number of chunks to retrieve (default: 5)"
    )
    parser.add_argument(
        "--date-from", help="Only search summaries from this date onward (YYYY-MM-DD, internal search only)"
    )
    args = parser.parse_args()

    # Logging setup
    try:
        init_db()
    except Exception:
        pass  # If DB init fails, logging is silently disabled

    # Build initial state
    initial_state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": args.query,
        "normalized_query": args.query,  # Will be updated by query_normalize node
        "source": args.source,
        "top_k": args.top_k,
        "date_from": args.date_from,
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
        "internal_succeeded": False,
        "internal_no_content_response": False,
        "web_answer": None,
        "web_result_count": 0,
        "web_succeeded": False,
        "web_was_fallback": False,
        "final_output": None,
        "errors": [],
        "duration_ms": None,
    }

    start_ms = time.monotonic()

    try:
        # Build and invoke the graph
        graph = build_graph()
        final_state = graph.invoke(initial_state)

        # Print the answer to user
        if final_state.get("final_output"):
            print(f"\n{final_state['final_output']}\n")
            if final_state.get("internal_succeeded"):
                # Print internal sources
                print("---")
                print("Sources:")
                for i, meta in enumerate(final_state.get("metas", []), start=1):
                    tag_part = f" [{meta['tag']}]" if meta.get("tag") else ""
                    print(f"  [{i}] {meta['source_type'].upper()} | {meta['date']} | {meta['author']} | {meta['title']}{tag_part}")

        # Extract results for logging
        distances = final_state.get("distances", [])
        log = {
            "timestamp": initial_state["timestamp"],
            "query": initial_state["query"],
            "normalized_query": final_state.get("normalized_query"),
            "explicit_web_detected": final_state.get("explicit_web_detected", False),
            "internal_attempted": bool(final_state.get("chunks_passed_threshold") is not None),
            "top_chunk_distance": distances[0] if distances else None,
            "chunks_passed_threshold": final_state.get("chunks_passed_threshold"),
            "judge_attempted": final_state.get("judge_score") is not None,
            "judge_score": final_state.get("judge_score"),
            "judge_quality": final_state.get("judge_quality"),
            "judge_intent_understood": final_state.get("judge_intent_understood"),
            "judge_reasoning": final_state.get("judge_reasoning"),
            "judge_parse_error": final_state.get("judge_parse_error", False),
            "internal_answer_generated": final_state.get("internal_answer") is not None,
            "internal_no_content_response": final_state.get("internal_no_content_response", False),
            "internal_succeeded": final_state.get("internal_succeeded", False),
            "web_attempted": final_state.get("web_answer") is not None,
            "web_was_fallback": final_state.get("web_was_fallback", False),
            "web_result_count": final_state.get("web_result_count", 0),
            "web_succeeded": final_state.get("web_succeeded", False),
            "final_output": final_state.get("final_output"),
            "duration_ms": int((time.monotonic() - start_ms) * 1000),
        }

        # Add errors if any
        if final_state.get("errors"):
            log["error"] = "; ".join(final_state["errors"])

    except Exception as e:
        log = {
            "timestamp": initial_state["timestamp"],
            "query": initial_state["query"],
            "duration_ms": int((time.monotonic() - start_ms) * 1000),
            "error": str(e),
        }
        raise  # re-raise so the user still sees the traceback

    finally:
        try:
            save_log(log)
        except Exception:
            pass  # Logging must never crash the main flow


if __name__ == "__main__":
    main()
