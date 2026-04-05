# Search News & Twitter — Plan

## Shipped

- Initial RAG project: ChromaDB + sentence-transformers + Claude
- Auto-indexing: new summary files picked up on every search
- CLI: `--query`, `--source`, `--top-k`, `--date-from` flags
- Skill: `/search-news-twitter`

## Backlog / Ideas

- `--tag` filter (AI/ML, Engineering, etc.)
- Multi-query expansion: generate N query variants, merge + deduplicate results
- Interactive REPL mode (`--interactive`)
- Periodic re-embedding if embedding model is upgraded
- Index reddit-insights outputs once that project produces summaries
