---
name: news-twitter-search-eval
description: Run evaluation harness for ai-chatbot to measure model quality
---

# Evaluate AI Chatbot Model

Run the automated evaluation harness to measure RAG answer quality, routing correctness, and retrieval precision.

## Quick Start

```bash
cd /Users/nikhil/Documents/AI/Playground/ai-chatbot
python3 eval/run_eval.py
```

## Prerequisites

- Ollama is running (`ollama serve` in another terminal)
- Index is built (`python3 index.py` if not already done)

## Options

Run a specific test:
```bash
python3 eval/run_eval.py --id internal_db_optimization
```

Get JSON output:
```bash
python3 eval/run_eval.py --json
```

## What It Measures

The harness runs 12 test queries covering 4 execution paths:

- **5 internal hits** — queries answered by indexed newsletters/tweets
- **3 web fallbacks** — queries about out-of-corpus topics (triggers fallback to web)
- **2 explicit web** — queries with time-sensitive keywords (skips internal)
- **2 judge gate cases** — ambiguous queries that judge should reject

Per test, it measures:
- **Routing correctness** — did it use the expected path?
- **Source precision** — % of retrieved chunks from expected sources
- **Judge score** — was relevance validated?
- **Answer presence** — was a final answer generated?
- **Latency** — how long did it take?

## Interpreting Results

- **PASS** — all checks passed
- **FAIL** — one or more checks failed (see detailed breakdown)
- **Success rate** — X/12 passed (target: 12/12 or 11/12 for edge cases)
- **Average latency** — useful for detecting performance regressions

## Typical Workflow

**After changing judge prompt, embedding model, or chunking:**
```bash
python3 eval/run_eval.py
# If pass rate drops, revert the change
# If it stays same or improves, commit the change
```

**Debug a specific failure:**
```bash
python3 eval/run_eval.py --id <test_id>
```
