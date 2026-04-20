# AI Chatbot — Plan

## Shipped

- Initial RAG project: ChromaDB + sentence-transformers + Ollama LLM
- Auto-indexing: new summary files picked up on every search
- CLI: `--query`, `--source`, `--top-k`, `--date-from` flags
- Skill: `/ai-chatbot`
- **Sequential fallback strategy**: internal search first, web on miss (not LLM router)
- **LLM-as-Judge**: intent validation before answer generation (score 0-10)
- **SQLite logging**: full audit trail with routing decisions, judge scores, judge reasoning
- **Query normalization**: typo correction via Ollama before embedding
- **LangGraph orchestration**: 9 nodes (query_normalize, index_sync, detect_explicit_web, classify_intent, llm_only, internal_retrieve, judge_gate, generate_answer, web_search) with typed state and explicit conditional edge mappings
- **Intent pre-classifier**: Routes GENERAL (textbook ML/CS concepts) → fast llm_only path (~500ms) vs PERSONAL → full RAG pipeline; achieves 100% validation accuracy on 77 test cases
- **LLM-only path**: Parametric-only answers for pure conceptual queries, skipping expensive retrieval and web search
- **Per-node retry logic**: judge (3 retries), web_search (3 retries), generate_answer (2 retries)
- **Explicit web keyword detection**: skip internal search for "latest", "breaking", "news", "stock", etc.
- **User feedback signal (1.9)**: Thumbs up/down buttons on each answer; feedback logged to SQLite `feedback` column; per-answer state persists across page reloads via sessionStorage

- **Web UI**: Flask chatbot interface at `http://localhost:5001` (`app.py` + `templates/index.html`)
- **Hybrid conversation mode**: per-turn RAG retrieval with conversation history injected at answer generation; web query enriched with context via `_enrich_web_query()` before hitting DuckDuckGo
- **Clear chat**: resets DOM + sessionStorage history + conversation ID
- **Conversation persistence**: `sessionStorage`-backed history survives tab refresh; DOM fully restored including sources and log UI
- **Conversation ID in logs**: every search turn tagged with `conversation_id` in SQLite for multi-turn tracing
- **Input lockout during requests**: send button + input disabled while awaiting response

## Backlog / Ideas

- `--tag` filter (AI/ML, Engineering, etc.)
- Multi-query expansion: generate N query variants, merge + deduplicate results
- Interactive REPL mode (`--interactive`)
- Periodic re-embedding if embedding model is upgraded
- Index reddit-insights outputs once that project produces summaries
- Streaming responses for long-form answers
- Search result caching by query hash
- Cap displayed history vs. sent history (currently all N messages shown, last 6 sent to backend)
- Sliding window UI indicator showing how many prior turns are in active context
