# Search News & Twitter — Plan

## Shipped

- Initial RAG project: ChromaDB + sentence-transformers + Ollama LLM
- Auto-indexing: new summary files picked up on every search
- CLI: `--query`, `--source`, `--top-k`, `--date-from` flags
- Skill: `/search-news-twitter`
- **Sequential fallback strategy**: internal search first, web on miss (not LLM router)
- **LLM-as-Judge**: intent validation before answer generation (score 0-10)
- **SQLite logging**: full audit trail with routing decisions, judge scores, judge reasoning
- **Query normalization**: typo correction via Ollama before embedding
- **LangGraph orchestration**: 8 nodes (query_normalize, index_sync, detect_explicit_web, internal_retrieve, judge_gate, generate_answer, web_search) with typed state
- **Per-node retry logic**: judge (3 retries), web_search (3 retries), generate_answer (2 retries)
- **Explicit web keyword detection**: skip internal search for "latest", "breaking", "news", "stock", etc.

## Backlog / Ideas

- `--tag` filter (AI/ML, Engineering, etc.)
- Multi-query expansion: generate N query variants, merge + deduplicate results
- Interactive REPL mode (`--interactive`)
- Periodic re-embedding if embedding model is upgraded
- Index reddit-insights outputs once that project produces summaries
- Streaming responses for long-form answers
- Search result caching by query hash
