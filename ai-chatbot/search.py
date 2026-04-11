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
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from graph import build_graph
from logger import init_db, save_log


# Query caching configuration
CACHE_TTL_HOURS = 24
CACHE_PATH = Path(__file__).parent / "data" / "query_cache.json"


def load_cache() -> dict:
    """Load the query cache from disk."""
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def save_cache(cache: dict):
    """Save the query cache to disk."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def get_cache_key(query: str, source: str, top_k: int, date_from: str) -> str:
    """Generate MD5 hash cache key from query parameters."""
    raw = f"{query.strip().lower()}|{source}|{top_k}|{date_from}"
    return hashlib.md5(raw.encode()).hexdigest()


def lookup_cache(key: str) -> dict:
    """
    Look up cached answer by key. Returns None if not found or expired.

    Returns:
        dict with "final_output" and "metas" keys, or None if not cached
    """
    cache = load_cache()
    entry = cache.get(key)
    if not entry:
        return None

    # Check TTL
    try:
        age_hours = (
            (datetime.now(timezone.utc) - datetime.fromisoformat(entry["timestamp"]))
            .total_seconds()
            / 3600
        )
        if age_hours > CACHE_TTL_HOURS:
            return None
    except Exception:
        return None

    return entry


def store_cache(key: str, final_output: str, metas: list):
    """
    Store answer in cache. Evicts expired entries.

    Args:
        key: Cache key from get_cache_key()
        final_output: The generated answer
        metas: List of source metadata dicts
    """
    cache = load_cache()
    cache[key] = {
        "final_output": final_output,
        "metas": metas,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Evict expired entries
    cutoff = datetime.now(timezone.utc).timestamp() - CACHE_TTL_HOURS * 3600
    cache = {
        k: v
        for k, v in cache.items()
        if datetime.fromisoformat(v["timestamp"]).timestamp() > cutoff
    }
    save_cache(cache)


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

    # Check cache first (only for internal hits)
    cache_key = get_cache_key(args.query, args.source, args.top_k, args.date_from)
    cached = lookup_cache(cache_key)
    if cached:
        print("\n[Cached result — run with fresh data]\n")
        print(cached["final_output"])
        # Print sources if cached (deduplicated)
        if cached.get("metas"):
            print("---")
            print("Sources:")

            # Deduplicate by (source_type, date, author, title)
            unique_sources = {}
            for meta in cached["metas"]:
                key = (meta["source_type"], meta["date"], meta["author"], meta["title"])
                if key not in unique_sources:
                    unique_sources[key] = meta

            # Print deduplicated sources with new numbering
            for i, (_, meta) in enumerate(unique_sources.items(), start=1):
                tag_part = f" [{meta['tag']}]" if meta.get("tag") else ""
                print(f"  [{i}] {meta['source_type'].upper()} | {meta['date']} | {meta['author']} | {meta['title']}{tag_part}")
        return

    # Build initial state
    initial_state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": args.query,
        "normalized_query": args.query,  # Will be updated by query_normalize node
        "source": args.source,
        "top_k": args.top_k,
        "date_from": args.date_from,
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
        "final_output": None,
        "errors": [],
        "duration_ms": None,
        "total_llm_tokens_in": 0,
        "total_llm_tokens_out": 0,
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
                # Print internal sources (deduplicated)
                print("---")
                print("Sources:")

                # Deduplicate by (source_type, date, author, title)
                unique_sources = {}
                for meta in final_state.get("metas", []):
                    key = (meta["source_type"], meta["date"], meta["author"], meta["title"])
                    if key not in unique_sources:
                        unique_sources[key] = meta

                # Print deduplicated sources with new numbering
                for i, (_, meta) in enumerate(unique_sources.items(), start=1):
                    tag_part = f" [{meta['tag']}]" if meta.get("tag") else ""
                    print(f"  [{i}] {meta['source_type'].upper()} | {meta['date']} | {meta['author']} | {meta['title']}{tag_part}")

        # Cache internal hits (before logging)
        if final_state.get("internal_succeeded") and final_state.get("final_output"):
            store_cache(
                cache_key,
                final_state["final_output"],
                final_state.get("metas", [])
            )

        # Extract results for logging
        distances = final_state.get("distances", [])
        log = {
            "timestamp": initial_state["timestamp"],
            "query": initial_state["query"],
            "normalized_query": final_state.get("normalized_query"),
            "explicit_web_detected": final_state.get("explicit_web_detected", False),
            "intent_class": final_state.get("intent_class"),
            "llm_only_used": final_state.get("intent_class") == "GENERAL" and final_state.get("llm_only_answer") is not None,
            "internal_attempted": bool(final_state.get("chunks_passed_threshold") is not None),
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
            "duration_ms": int((time.monotonic() - start_ms) * 1000),
            "total_llm_tokens_in": final_state.get("total_llm_tokens_in", 0),
            "total_llm_tokens_out": final_state.get("total_llm_tokens_out", 0),
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
