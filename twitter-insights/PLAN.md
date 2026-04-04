# Twitter Insights — Plan

## Shipped

- `fetch_tweets.py` — cookie-based auth (auth_token + ct0); direct httpx calls to Twitter's internal GraphQL API (`HomeLatestTimeline`); outputs JSON with id, author_username, author_name, text, created_at, like/retweet/reply counts
- Uses "Following" tab endpoint (`HomeLatestTimeline`) — strictly accounts you follow, no algorithmic recommendations or ads
- `data/scanned.json` — state tracking to avoid re-processing tweets across runs
- 12-hour lookback window — only tweets from the last 12 hours are included per run
- Skips retweets (`retweeted_status_result` presence) and promoted tweets
- `/twitter-insights` skill (`.claude/skills/twitter-insights.md`) — end-to-end digest: run fetcher → parse JSON → classify → write digest
- Topic classification: `AI/ML`, `Engineering`, `Product`, `Business`, `Other`
- Output format: `summaries/YYYY-MM-DD.md` — grouped by author (sorted by tweet count), `###` per tweet with 2–4 extracted insight bullets

## Backlog / Ideas

*(add ideas here as they come up)*
