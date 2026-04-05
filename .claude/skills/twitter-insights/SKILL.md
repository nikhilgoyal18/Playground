---
description: >
  Scan Twitter/X home timeline for new tweets and produce a topic-grouped digest.
  Use when the user asks for twitter insights, tweet digest, latest tweets,
  or anything about scanning/reading/summarizing their Twitter timeline.
  Trigger phrases: "twitter digest", "scan tweets", "latest tweets",
  "today's tweets", "what's on my twitter", "twitter timeline", "twitter insights",
  "tweet summary", "show me my twitter feed", "give me today's twitter scan".
allowed-tools: Bash(python3 fetch_tweets.py*), Write, Read
---

# Twitter Insights

Scan the Twitter/X home timeline for new tweets and produce a topic-grouped digest.

## Steps

1. Change into the `twitter-insights/` directory (relative to the Playground root).

2. Run the fetcher:
   ```bash
   python3 fetch_tweets.py
   ```
   This outputs a JSON array of new tweets to stdout and updates `data/scanned.json`. If it exits with an auth error, remind the user to refresh their cookies as described in `twitter-insights/CLAUDE.md`.

3. Parse the JSON output. Each item has:
   - `id` — tweet ID
   - `author_username` — Twitter handle
   - `author_name` — display name
   - `text` — tweet text
   - `created_at` — timestamp
   - `like_count`, `retweet_count`, `reply_count` — engagement metrics

4. If the array is empty, respond:
   > No new tweets since the last scan. Check back later.

5. Otherwise, produce a digest using the following rules:

   **Filtering:**
   - Skip tweets with no substantive content: pure link shares with no context, puzzle answers, deal announcements, one-word reactions, content that's impossible to understand without the linked media
   - Skip tweets with `like_count + retweet_count + reply_count < 3` unless the content is clearly high-signal

   **Grouping:**
   - Group all tweets from the same account under one `##` heading
   - Use the author's display name as the `##` heading, with handle in parentheses
   - Sort sections by number of substantive tweets (most prolific first)

   **Per tweet:**
   - Each substantive tweet gets a `###` subsection: a short descriptive title followed by a topic tag in backticks
   - Topic tags: `AI/ML`, `Engineering`, `Product`, `Business`, `Other`
   - Write 2–4 bullet points of **actual insight extracted from the tweet** — not a paraphrase of what was said
   - Include specifics: numbers, names, frameworks, product names, claims made
   - If multiple tweets from the same account cover the same topic, group them under one `###`

6. Write the digest to `summaries/YYYY-MM-DD.md` using today's date. Format:

```markdown
# Twitter Digest — YYYY-MM-DD

> N tweets from M accounts. Skipped low-signal posts.

---

## [Display Name] (@handle) `[Primary Tag]`
*N substantive tweets*

### [Descriptive Title] `[Topic Tag]`
- Specific insight or claim from the tweet
- Supporting detail, number, or named entity
- Concrete takeaway if applicable

### [Another Title] `[Topic Tag]`
- ...

---

## [Next Account]
...
```

7. Display the digest to the user and mention the file it was saved to.
