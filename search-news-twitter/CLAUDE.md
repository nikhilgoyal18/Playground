# Search News & Twitter

Semantic search across indexed newsletter and Twitter digests with intelligent fallback to live web search. Uses local embeddings (sentence-transformers), ChromaDB vector storage, Ollama LLM, and DuckDuckGo.

## How It Works

Run `python3 search.py --query "your question"` from this directory. The system:

1. **Auto-indexes** any new summary files from `newsletter-insights/summaries/` and `twitter-insights/summaries/`
2. **Checks for explicit web signals** — queries with real-time keywords (see `EXPLICIT_WEB_KEYWORDS` in `graph.py`) skip straight to web search
3. **Tries internal search first** — embeds your query with `all-MiniLM-L6-v2`, retrieves semantically similar chunks from ChromaDB
4. **Intent judge gates output** — LLM validates retrieved chunks match your intent (score 0-10; must be ≥5 to proceed)
5. **Falls back to web if needed** — queries DuckDuckGo if internal search finds nothing relevant
6. **Generates cited answers** — both paths produce answers with `[Source N]` citations
7. **Logs everything** — every session persisted to SQLite for analysis

## Files

| File | Purpose |
|------|---------|
| `search.py` | CLI entry point — orchestrates the full search flow |
| `graph.py` | LangGraph pipeline: 8 nodes, typed state, per-node retry logic |
| `index.py` | Parses summaries into bullet-level chunks, embeds, upserts to ChromaDB |
| `web_search.py` | DuckDuckGo integration + Ollama-based summarization |
| `logger.py` | SQLite persistence layer for search audit trail |
| `data/indexed.json` | Tracks indexed summary files (prevents re-processing) |
| `data/query_cache.json` | Query normalization cache (auto-managed) |
| `data/search_logs.db` | SQLite audit trail: routing decisions, judge scores, durations |
| `db/chroma/` | ChromaDB persistent vector store (auto-created, do not commit) |
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
