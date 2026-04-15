#!/usr/bin/env python3
"""
Evaluation harness for AI Chatbot RAG system.

Runs test queries and measures:
- Routing correctness (internal vs. web fallback vs. explicit web)
- Source precision (% of retrieved sources in expected set)
- Judge score quality
- Latency
- Errors

Usage:
    python3 run_eval.py                    # Run all tests
    python3 run_eval.py --id internal_db   # Run specific test
    python3 run_eval.py --json             # Output JSON results
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path so we can import graph, etc.
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import build_graph
from logger import init_db, save_eval_run
from test_cases import TEST_CASES


def make_initial_state(query: str) -> dict:
    """Build initial SearchState dict for a query."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "normalized_query": query,  # Will be updated by query_normalize node
        "source": None,
        "top_k": 5,
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
        "web_sources": [],
        "final_output": None,
        "errors": [],
        "duration_ms": None,
        "total_llm_tokens_in": 0,
        "total_llm_tokens_out": 0,
    }


def classify_path(state: dict) -> str:
    """Classify which execution path was taken based on final state."""
    if state.get("intent_class") == "GENERAL" and state.get("llm_only_answer") is not None:
        return "llm_only"
    elif state.get("explicit_web_detected"):
        return "explicit_web"
    elif state.get("internal_succeeded"):
        return "internal"
    elif state.get("web_was_fallback"):
        return "web_fallback"
    elif state.get("web_succeeded"):
        return "web"
    else:
        return "unknown"


def compute_source_precision(state: dict, expected_sources: list) -> float:
    """
    Compute precision of retrieved sources.
    Returns % of metas whose author field matches any expected_source substring.
    """
    if not expected_sources or not state.get("metas"):
        return 1.0 if not expected_sources else 0.0

    metas = state.get("metas", [])
    if not metas:
        return 0.0

    matches = 0
    for meta in metas:
        author = meta.get("author", "").lower()
        for expected in expected_sources:
            if expected.lower() in author:
                matches += 1
                break  # Count each meta at most once

    return matches / len(metas) if metas else 0.0


def run_eval_test(test_case: dict, graph) -> dict:
    """
    Run a single test case and return results.
    """
    test_id = test_case["id"]
    query = test_case["query"]

    # Build state and invoke graph
    initial_state = make_initial_state(query)
    final_state = graph.invoke(initial_state)

    # Classify path
    actual_path = classify_path(final_state)
    expected_path = test_case.get("expected_path")
    path_correct = actual_path == expected_path

    # Source precision
    expected_sources = test_case.get("expected_sources", [])
    source_precision = compute_source_precision(final_state, expected_sources)

    # Judge score
    judge_score = final_state.get("judge_score")
    min_judge_score = test_case.get("min_judge_score", 0)
    judge_ok = (judge_score or 0) >= min_judge_score

    # Answer
    has_answer = bool(final_state.get("final_output"))
    duration_ms = final_state.get("duration_ms")
    errors = final_state.get("errors", [])

    # Check regression-specific assertions
    regression_failures = []
    if test_case.get("assert_has_answer") and not has_answer:
        regression_failures.append("assert_has_answer: final_output is empty")
    if test_case.get("assert_web_sources") and not final_state.get("web_sources"):
        regression_failures.append("assert_web_sources: web_sources is empty")
    if test_case.get("assert_hallucination_risk") and not final_state.get("hallucination_risk"):
        regression_failures.append("assert_hallucination_risk: hallucination_risk not flagged")

    # Compile result
    result = {
        "id": test_id,
        "query": query,
        "expected_path": expected_path,
        "actual_path": actual_path,
        "path_correct": path_correct,
        "source_precision": round(source_precision, 2),
        "judge_score": judge_score,
        "judge_ok": judge_ok,
        "has_answer": has_answer,
        "duration_ms": duration_ms,
        "errors": errors,
        "regression_failures": regression_failures,
    }

    return result


def print_table(results: list):
    """Print results as a nicely formatted table."""
    print("\n" + "=" * 140)
    print("EVALUATION RESULTS")
    print("=" * 140)
    print(f"{'Test ID':<30} {'Expected':<15} {'Actual':<15} {'Precision':<10} {'Judge':<8} {'Answer':<8} {'Latency':<8} {'Status':<8}")
    print("-" * 140)

    passed = 0
    for r in results:
        test_id = r["id"][:28]
        expected = r["expected_path"]
        actual = r["actual_path"]
        precision = r["source_precision"]
        judge = r["judge_score"] if r["judge_score"] is not None else "—"
        answer = "✓" if r["has_answer"] else "✗"
        latency = f"{r['duration_ms']:.0f}ms" if r["duration_ms"] else "—"

        # Determine overall status
        regression_ok = not r.get("regression_failures")
        all_ok = r["path_correct"] and r["judge_ok"] and r["has_answer"] and regression_ok
        if r["errors"]:
            status = "ERR"
        elif all_ok:
            status = "PASS"
            passed += 1
        elif not r["path_correct"]:
            status = "PATH"
        elif not r["judge_ok"]:
            status = "JUDGE"
        elif not regression_ok:
            status = "REGR"
        else:
            status = "FAIL"

        print(f"{test_id:<30} {expected:<15} {actual:<15} {precision:<10} {judge:<8} {answer:<8} {latency:<8} {status:<8}")

    print("-" * 140)
    print(f"Results: {passed}/{len(results)} passed ({100*passed/len(results):.1f}%)")
    if results:
        avg_latency = sum(r["duration_ms"] or 0 for r in results) / len(results)
        print(f"Average latency: {avg_latency:.0f}ms")
    print("=" * 140 + "\n")

    # Print detailed failures
    failures = [r for r in results if not (r.get("path_correct") and r.get("judge_ok") and r.get("has_answer") and not r.get("regression_failures"))]
    if failures:
        print("FAILURES & ERRORS:")
        print("-" * 140)
        for r in failures:
            # Find the corresponding test case
            test_case = next((tc for tc in TEST_CASES if tc["id"] == r["id"]), {})
            min_judge = test_case.get("min_judge_score", 0)
            expected_sources = test_case.get("expected_sources", [])

            print(f"\n[{r['id']}] {r['query']}")
            print(f"  Expected path: {r['expected_path']}")
            print(f"  Actual path:   {r['actual_path']}")
            print(f"  Source precision: {r['source_precision']} (expected {len(expected_sources)} sources)")
            print(f"  Judge score: {r['judge_score']} (need >= {min_judge})")
            print(f"  Has answer: {r['has_answer']}")
            if r.get("regression_failures"):
                for rf in r["regression_failures"]:
                    print(f"  REGRESSION: {rf}")
            if r.get("errors"):
                print(f"  Errors: {r['errors']}")


def main():
    parser = argparse.ArgumentParser(description="Run evaluation harness for AI Chatbot")
    parser.add_argument("--id", help="Run only this test ID")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    parser.add_argument("--save", action="store_true", help="Save results to DB (eval_runs table)")
    args = parser.parse_args()

    # Filter test cases if --id specified
    test_cases = TEST_CASES
    if args.id:
        test_cases = [tc for tc in TEST_CASES if tc["id"] == args.id]
        if not test_cases:
            print(f"Error: test case '{args.id}' not found")
            return 1

    # Ensure DB and eval_runs table exist
    init_db()

    # Build graph
    print("Building LangGraph...")
    graph = build_graph()

    # Run tests
    print(f"Running {len(test_cases)} test case(s)...\n")
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test_case['id']}...", end=" ", flush=True)
        try:
            result = run_eval_test(test_case, graph)
            results.append(result)
            print(f"✓ ({result['actual_path']})")
        except Exception as e:
            print(f"✗ Exception: {e}")
            results.append({
                "id": test_case["id"],
                "query": test_case["query"],
                "expected_path": test_case.get("expected_path"),
                "actual_path": "exception",
                "path_correct": False,
                "error": str(e),
                "judge_ok": False,
                "has_answer": False,
                "duration_ms": None,
                "errors": [str(e)],
            })

    # Output results
    passed = sum(1 for r in results if r.get("path_correct") and r.get("judge_ok") and r.get("has_answer") and not r.get("regression_failures"))
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_table(results)

    # Log to DB if --save flag (skip for single-test runs)
    if args.save and not args.id:
        init_db()
        run_id = save_eval_run(results, passed)
        print(f"Eval run saved to DB: eval_runs.id = {run_id}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
