# Search News & Twitter — Reference

Read this file for: **setup, troubleshooting, or analyzing search logs**.  
For normal usage and project overview, see `CLAUDE.md`.

---

## One-Time Setup

### 1. Install Ollama
Download from **ollama.com**, then pull the model:
```bash
ollama pull llama3.2
```
Model size: ~2 GB. Runs as a local server — no API key needed after this step.

### 2. Install Python dependencies
```bash
cd search-news-twitter
pip install -r requirements.txt
```

Dependencies: `chromadb`, `sentence-transformers` (~800 MB one-time for PyTorch), `ollama`, `ddgs`, `sqlite3` (built-in).

> The embedding model (`all-MiniLM-L6-v2`, ~22 MB) is cached at `~/.cache/huggingface/` after first run.

### 3. Build the initial index
```bash
python3 index.py
```
Scans `../newsletter-insights/summaries/` and `../twitter-insights/summaries/`, chunks all new files by bullet point, embeds them, and upserts to ChromaDB. On subsequent runs, only new files are indexed.

---

## Analyze Search Sessions

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

---

## Analyze Conversations

To trace a full conversation in the DB:
```bash
sqlite3 data/search_logs.db "
SELECT id, timestamp, query, conversation_id
FROM searches
WHERE conversation_id = 'your-uuid-here'
ORDER BY id
"
```

To see all multi-turn conversations:
```bash
sqlite3 data/search_logs.db "
SELECT conversation_id, COUNT(*) as turns, MIN(timestamp) as started
FROM searches
WHERE conversation_id IS NOT NULL
GROUP BY conversation_id
ORDER BY started DESC
LIMIT 10
"
```

---

## Troubleshooting

### "Ollama is not running"
```bash
ollama serve
```
Keep this running in a separate terminal.

### "No web search results found"
DuckDuckGo may have rate-limited the request. Wait a moment and retry. All queries log to `data/search_logs.db` regardless.

### "Judge parse error — falling back to web"
Rare. The LLM judge couldn't parse its JSON output. Automatically falls back to web search. Safe — parse error is logged.

### "Index is empty. Run `python3 index.py` first"
Run `python3 index.py` from the project directory to scan and index existing summary files.

### Empty `data/search_logs.db`
Created on first search. If empty after searches, check for errors:
```bash
sqlite3 data/search_logs.db "SELECT * FROM searches LIMIT 1"
```

### 500 error on web UI (search failed)
Check the server log:
```bash
tail -50 /tmp/snt_server.log
```
Common causes:
- **`'<' not supported between instances of 'str' and 'int'`** — judge LLM returned score as string. Fixed in graph.py (cast to `int`). If it recurs, check Ollama output.
- Ollama timeout during `_enrich_web_query` — transient; retrying the query usually works.
- Graph state error — restart the server: `lsof -ti :5001 | xargs kill -9; python3 app.py > /tmp/snt_server.log 2>&1 &`

### Conversation context not carrying over
- Check browser sessionStorage: open DevTools → Application → Session Storage → `snt_conv_history`
- If empty, the history was cleared (tab closed, or "Clear chat" was clicked)
- Conversation history is capped at 6 entries (3 exchanges) before sending to backend — older context is not included
