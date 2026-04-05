# Search News & Twitter

**Latest Updates (April 2026):**
- ✅ Bullet-level chunking for precise retrieval (294 chunks vs 85 topic-level)
- ✅ Sequential fallback strategy (internal first, web on miss)
- ✅ Explicit web keyword detection (skip internal for "latest", "news", etc.)
- ✅ Intent judge LLM gate (semantic validation of retrieval)
- ✅ Full SQLite audit trail (logs every search decision + duration)

# Search News & Twitter

Semantic search across indexed newsletter and Twitter digests with intelligent fallback to live web search. Uses local embeddings (sentence-transformers), ChromaDB vector storage, Ollama LLM, and DuckDuckGo for web results.

## How It Works

Run `python3 search.py --query "your question"` from the `search-news-twitter/` directory. The system:

1. **Auto-indexes** any new summary files from `newsletter-insights/summaries/` and `twitter-insights/summaries/`
2. **Checks for explicit web signals** — if your query contains keywords like "latest", "news", "stock", "breaking", etc., it skips straight to web search
3. **Tries internal search first** — embeds your query locally with `all-MiniLM-L6-v2` and retrieves semantically similar chunks from ChromaDB via bullet-level precision
4. **Intent judge gates output** — even if chunks are retrieved, an LLM judge validates they match your intent (score 0-10; must be ≥5 to proceed)
5. **Falls back to web if needed** — if internal search finds nothing relevant, queries DuckDuckGo for live results
6. **Generates cited answers** — both internal and web paths produce answers with `[Source N]` citations
7. **Logs everything** — every search session is persisted to SQLite for later analysis

State is tracked in `data/indexed.json` (processed files), `db/chroma/` (vector store), and `data/search_logs.db` (search audit trail).

## One-Time Setup

### 1. Install Ollama
Download from **ollama.com**, then pull the model:
```bash
ollama pull llama3.2
```
Model size: ~2 GB. Ollama runs as a local server — no API key or internet connection needed after this step.

### 2. Install Python dependencies
```bash
cd search-news-twitter
pip install -r requirements.txt
```

Dependencies:
- `chromadb` — vector database
- `sentence-transformers` — local embeddings (installs PyTorch, ~800 MB one-time)
- `ollama` — local LLM client
- `ddgs` — DuckDuckGo search API (no auth required)
- `sqlite3` — built-in Python module (DB logging)

> Note: The embedding model (`all-MiniLM-L6-v2`, ~22 MB) is cached at `~/.cache/huggingface/` after first run.

### 3. Build the initial index
```bash
python3 index.py
```

This scans `../newsletter-insights/summaries/` and `../twitter-insights/summaries/`, chunks all new files by bullet point, embeds them, and upserts to ChromaDB. On subsequent runs, only new files are indexed.

## Files

| File | Purpose |
|------|---------|
| `search.py` | CLI entry point with orchestration logic (keyword check → internal search OR explicit web) |
| `index.py` | Parses summary files into bullet-level chunks, embeds with `all-MiniLM-L6-v2`, upserts to ChromaDB |
| `web_search.py` | DuckDuckGo integration + Ollama-based result summarization |
| `logger.py` | SQLite persistence layer for search audit trail (no external DB needed) |
| `data/indexed.json` | Tracks indexed summary files (prevents re-processing) |
| `data/search_logs.db` | SQLite database of all search sessions with full trace (routing decisions, judge scores, durations, etc.) |
| `db/chroma/` | ChromaDB persistent vector store (auto-created, do not commit) |

## CLI Usage

```bash
# Basic search (tries internal, falls back to web if needed)
python3 search.py --query "database indexing trade-offs"

# Explicit web query (skips internal, goes straight to web)
python3 search.py --query "latest news about AI regulation"
python3 search.py --query "today's MSFT stock price"

# Filter internal search to one source (only applies if internal is attempted)
python3 search.py --query "AI agent tools" --source twitter
python3 search.py --query "system design patterns" --source newsletter

# Retrieve more chunks from internal search (internal-only flag)
python3 search.py --query "RAG retrieval" --top-k 8

# Filter internal search by date (internal-only flag)
python3 search.py --query "startup product strategy" --date-from 2026-04-01
```

**Keywords that trigger direct web search** (skips internal entirely):
`latest`, `last week`, `last month`, `breaking`, `news`, `current`, `stock`, `price`, `today`, `yesterday`, `right now`, `live`, `recently`, `trending`, `just announced`, `new release`

## How Chunking Works

Each bullet point under a `###` topic heading becomes its own chunk (bullet-level precision). Each chunk retains the topic heading and author as context, but is embedded independently for focused semantic matching.

Example: "EP209: 12 Claude Code Features" section with 6 bullet points → 6 separate chunks, each capturing one feature.

Metadata per chunk:
- `source_type`: `newsletter` or `twitter`
- `date`: from filename (YYYY-MM-DD)
- `author`: newsletter sender or Twitter display name
- `title`: topic heading text
- `tag`: category (AI/ML, Engineering, Product, Business, Other)

New summary files are automatically discovered and indexed on the next search run.

## Search Flow & Logging

Every search session is logged to `data/search_logs.db` with:
- **Routing decision** — explicit web keywords detected?
- **Internal attempt** — chunk distance score, whether threshold passed
- **Intent judge** — LLM validation score (0-10), parse errors, reasoning
- **Fallback status** — did web search run as primary or fallback?
- **Web results** — result count, success/failure
- **Output** — final answer (truncated to 2000 chars)
- **Duration** — total time in milliseconds
- **Errors** — any exceptions that occurred

### Analyze Search Sessions

```bash
# Fallback rate
sqlite3 data/search_logs.db "
SELECT SUM(web_was_fallback) as fallbacks, COUNT(*) as total,
       ROUND(100.0 * SUM(web_was_fallback) / COUNT(*), 1) as fallback_pct
FROM searches WHERE internal_attempted = 1
"

# Judge score distribution
sqlite3 data/search_logs.db "
SELECT judge_score, COUNT(*) FROM searches 
WHERE judge_attempted = 1 
GROUP BY judge_score 
ORDER BY judge_score
"

# Sessions where judge blocked a result
sqlite3 data/search_logs.db "
SELECT query, judge_score, judge_reasoning
FROM searches
WHERE judge_attempted = 1 AND judge_score < 5 AND internal_attempted = 1
"

# Average duration by path
sqlite3 data/search_logs.db "
SELECT
  CASE WHEN explicit_web_detected = 1 THEN 'explicit_web'
       WHEN internal_succeeded = 1 THEN 'internal_hit'
       WHEN web_was_fallback = 1 THEN 'internal_miss_web_fallback'
       ELSE 'other' END as path,
  COUNT(*) as n,
  AVG(duration_ms) as avg_ms
FROM searches 
GROUP BY path
"
```

## Troubleshooting

### "Ollama is not running"
Start the Ollama server in a separate terminal:
```bash
ollama serve
```
Keep this running while doing searches.

### "No web search results found"
DuckDuckGo may have rate-limited the request. Wait a moment and try again. Queries are logged to `data/search_logs.db` regardless of success.

### "Judge parse error — falling back to web"
The LLM judge couldn't parse its own JSON output (rare). This triggers a fallback to web search. It's safe; logging captures the parse error.

### "I didn't understand the query or context" (old behavior)
This was from the first-generation router. Now we have a sequential strategy: if internal search fails, we automatically try the web. This message shouldn't appear unless there's an exception.

### "Index is empty. Run `python3 index.py` first"
You haven't indexed any summary files yet. Run `python3 index.py` from this directory to scan and index existing newsletter/Twitter digests.

### Empty `data/search_logs.db`
It gets created on first search. If it exists but is empty, the search may have logged a JSON parse error or failed before reaching the finally block. Check the logs with:
```bash
sqlite3 data/search_logs.db "SELECT * FROM searches LIMIT 1"
```
