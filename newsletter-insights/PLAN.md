# Newsletter Insights — Plan

## Shipped

- `scan_newsletters.py` — Gmail OAuth integration; fetches emails matching `from:@substack.com OR subject:newsletter`, outputs JSON with id, from, subject, date, body
- `data/scanned.json` — state tracking to avoid re-processing emails across runs
- `/newsletter-insights` skill (`.claude/commands/newsletter-insights.md`) — end-to-end digest: run scanner → parse JSON → classify → write digest
- Topic classification: `AI/ML`, `Engineering`, `Product`, `Business`, `Other`
- Output format: `summaries/YYYY-MM-DD.md` — grouped by sender (sorted by issue count), `###` per issue with 4–6 extracted bullet-point learnings
- Skips podcast-only emails (no body content) and Substack notification digests

## Backlog / Ideas

*(add ideas here as they come up)*
