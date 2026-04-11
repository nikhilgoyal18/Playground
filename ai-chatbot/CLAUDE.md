# AI Chatbot

Semantic search and intelligent Q&A across all your digests with fallback to live web search. Powered by local embeddings, ChromaDB vector storage, Claude, and DuckDuckGo.

## How It Works

**Web UI (recommended):** Run `python3 app.py` and open `http://localhost:5001`. Supports multi-turn conversation with context memory, clear chat, and full log UI.

**CLI:** Run `python3 search.py --query "your question"` for single-shot queries.

Both invoke the same LangGraph pipeline:

1. **Auto-indexes** any new summary files from `newsletter-insights/summaries/` and `twitter-insights/summaries/`
2. **Checks for explicit web signals** — queries with real-time keywords (see `EXPLICIT_WEB_KEYWORDS` in `graph.py`) skip straight to web search
3. **Tries internal search first** — embeds your query with `all-MiniLM-L6-v2`, retrieves semantically similar chunks from ChromaDB
4. **Intent judge gates output** — LLM validates retrieved chunks match your intent (score 0-10; must be ≥5 to proceed)
5. **Falls back to web if needed** — queries DuckDuckGo if internal search finds nothing relevant; web query is enriched with conversation context before searching
6. **Generates cited answers** — both paths produce answers with `[Source N]` citations; conversation history is injected at answer generation for coherent follow-ups
7. **Logs everything** — every turn persisted to SQLite with `conversation_id` for multi-turn tracing

## Files

| File | Purpose |
|------|---------|
| `search.py` | CLI entry point — single-shot query mode |
| `app.py` | Flask web server — serves the chatbot UI at `http://localhost:5001` |
| `templates/index.html` | Chat UI — conversation history, clear chat, source citations, log details |
| `graph.py` | LangGraph pipeline: 9 nodes (query_normalize, index_sync, detect_explicit_web, classify_intent, llm_only, internal_retrieve, judge_gate, generate_answer, web_search), typed state, per-node retry logic |
| `index.py` | Parses summaries into bullet-level chunks, embeds, upserts to ChromaDB |
| `web_search.py` | DuckDuckGo integration + Ollama-based summarization (conversation-aware) |
| `logger.py` | SQLite persistence layer — includes `conversation_id` for multi-turn tracing |
| `data/indexed.json` | Tracks indexed summary files (prevents re-processing) |
| `data/query_cache.json` | Query normalization cache (auto-managed) |
| `data/search_logs.db` | SQLite audit trail: routing decisions, judge scores, durations, conversation IDs |
| `db/chroma/` | ChromaDB persistent vector store (auto-created, do not commit) |
| `eval/METRICS_AND_GUARDRAILS.md` | Evaluation metrics, guardrails, baselines, and SQL queries for production analysis |
| `eval/` | Evaluation harness — run `python3 eval/run_eval.py` to check pass rates |
| `bugs-and-fixes/BUGS.md` | Bug tracking and fix history |
| `CHUNKING_STRATEGY.md` | Read when modifying `index.py` or changing chunking behavior |
| `REFERENCE.md` | Read for setup instructions, SQLite analysis queries, and troubleshooting |

## CLI Usage

```bash
# Basic search
python3 search.py --query "database indexing trade-offs"

# Filter by source
python3 search.py --query "AI agent tools" --source twitter
python3 search.py --query "system design patterns" --source newsletter

# Retrieve more chunks
python3 search.py --query "RAG retrieval" --top-k 8

# Filter by date
python3 search.py --query "startup product strategy" --date-from 2026-04-01
```
