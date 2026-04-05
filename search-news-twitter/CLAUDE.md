# Search News & Twitter

Semantic search across indexed newsletter and Twitter digests — powered by ChromaDB, sentence-transformers, and Claude.

## How It Works

Run `/search-news-twitter` from the Playground root. Claude will:
1. Auto-index any new summary files from `newsletter-insights/summaries/` and `twitter-insights/summaries/`
2. Embed the query using `all-MiniLM-L6-v2` (local, no extra API key needed)
3. Retrieve the most semantically relevant chunks from ChromaDB
4. Generate a cited answer using Claude — strictly from retrieved content, no web search

State is tracked in `data/indexed.json`. The vector store lives in `db/chroma/` (auto-created on first run).

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

> Note: `sentence-transformers` installs PyTorch (~800 MB one-time download). The embedding model (`all-MiniLM-L6-v2`, ~22 MB) is cached at `~/.cache/huggingface/` after the first run.

### 3. Build the initial index
```bash
python3 index.py
```

## Files

| File | Purpose |
|------|---------|
| `index.py` | Parses summary files, chunks by topic, embeds and upserts into ChromaDB |
| `search.py` | CLI entry point: auto-indexes new files, retrieves chunks, answers with Claude |
| `data/indexed.json` | Tracks which summary files have been indexed (never re-processes the same file) |
| `db/chroma/` | ChromaDB persistent vector store (auto-created, do not commit) |

## CLI Usage

```bash
# Basic search (both sources)
python3 search.py --query "database indexing trade-offs"

# Filter to one source
python3 search.py --query "AI agent tools" --source twitter
python3 search.py --query "system design patterns" --source newsletter

# Retrieve more chunks
python3 search.py --query "RAG retrieval" --top-k 8

# Filter by date
python3 search.py --query "startup product" --date-from 2026-04-01
```

## How Chunking Works

Each `###` topic heading in a summary file becomes one chunk with metadata:
- `source_type`: `newsletter` or `twitter`
- `date`: from the filename (YYYY-MM-DD)
- `author`: newsletter sender or Twitter display name
- `title`: topic heading text
- `tag`: topic category (AI/ML, Engineering, Product, Business, Other)

As you run the newsletter and Twitter digest tools over time, new summary files are automatically picked up and indexed the next time you run a search.
