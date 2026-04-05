---
description: >
  Scan Reddit subreddits for tech/software problems people are facing and rank them as market opportunities.
  Use when the user asks: "reddit problems", "scan reddit", "what problems are people having on reddit",
  "reddit insights", "find market opportunities", "reddit pain points", "scan subreddits",
  "give me today's reddit problems", "what are people complaining about on reddit".
  Trigger phrases: "reddit problems", "scan reddit", "reddit insights", "market research reddit",
  "reddit pain points", "reddit opportunities".
allowed-tools: mcp__reddit-mcp-buddy__browse_subreddit, mcp__reddit-mcp-buddy__get_post_details, Read, Write
---

# Reddit Problems — Fetch + Extract + Rank

Scan configured subreddits for tech/software problems, score them, and produce a ranked list.

## Steps

### 1. Load config

Read `reddit-insights/data/subreddits.json` to get the subreddit list, limits, sort orders, and `min_score`.
Read `reddit-insights/data/scanned.json` to get `scanned_ids` (already-processed post IDs).

### 2. Fetch posts

For each subreddit in the config, call `browse_subreddit` with the configured `limit` and `sort`.

Filter out any posts where:
- The post `id` is already in `scanned_ids`
- The post score is below `min_score`
- The post is stickied/pinned (mod announcements)

Collect all new posts across all subreddits.

If zero new posts after filtering, tell the user:
> No new posts since the last scan. Check back later or add more subreddits to `data/subreddits.json`.

### 3. Fetch comments for high-signal posts

For posts with `score > 100` or `num_comments > 50`, call `get_post_details` to retrieve top comments. This gives richer evidence for problem extraction. Limit to `top_comments_per_post` comments from config (default 5).

For lower-signal posts, use only the post title and body.

### 4. Extract tech/software problems

For each post, evaluate whether it describes a tech or software problem worth investigating as a market opportunity.

**Include** posts that:
- Describe a frustration, pain point, or workflow inefficiency with tools, software, or systems
- Ask "why doesn't X exist" or "is there a better way to do X"
- Describe a manual process that should be automated
- Have comments amplifying the problem ("same here", workarounds being shared, people frustrated)
- Describe a gap between what tools promise and what they deliver

**Exclude** posts that:
- Are memes, jokes, polls, or general opinion without a specific problem
- Have a fully accepted answer (question is solved, not a recurring pain)
- Are career/hiring/salary discussions
- Describe a narrow one-off bug (not a general market problem)
- Are news articles or link shares with no problem discussion

### 5. For each extracted problem, record:

- `problem_statement`: 1–2 sentences, clean and general (not tied to OP's specific setup)
- `evidence`: 2–3 direct quotes from the post or top comments
- `category`: one of `Developer Tools`, `Productivity`, `Data/AI`, `DevOps/Infrastructure`, `Security`, `Communication`, `Business/Finance`, `Other`
- `intensity`: `low` / `medium` / `high` based on frustration level, comment count, and tone
- `source_posts`: list of `{id, subreddit, score, num_comments}`

### 6. Deduplicate

If two posts (from the same or different subreddits) describe the same underlying problem, merge them into one entry:
- Combine evidence from both
- Use the higher composite score
- List all source subreddits

### 7. Score and rank

Compute a composite score for each problem:
```
composite_score = score + (num_comments × 3) + intensity_bonus
intensity_bonus: low=0, medium=50, high=150
```
For merged problems, sum scores from all source posts.

Rank problems by `composite_score` descending. Number them 1–N.

### 8. Write outputs

**Write** the ranked problem list to `reddit-insights/problems/YYYY-MM-DD-problems.md` (use today's date):

```markdown
# Reddit Problem Scan — YYYY-MM-DD

> N posts scanned across M subreddits. K tech problems extracted. Run `/reddit-research` to deep-dive any of these.

---

### #1 — [Problem Title] `Category` `intensity`
**Score**: X | Upvotes: Y | Comments: Z | r/subreddit1, r/subreddit2

**Problem**: Clean 1–2 sentence problem statement.

**Evidence**:
> "Direct quote from post..."
> "Quote from a comment validating the problem..."

---

### #2 — ...
```

**Write** a lightweight research index to `reddit-insights/data/problems.json` — only the fields needed by `/reddit-research` (full problem detail lives in the markdown):

```json
{
  "generated_date": "YYYY-MM-DD",
  "schema_version": 2,
  "problems": [
    {
      "rank": 1,
      "id": "prob_001",
      "title": "Short problem title",
      "category": "Developer Tools",
      "intensity": "high",
      "composite_score": 1247,
      "researched": false
    }
  ]
}
```

**Update** `reddit-insights/data/scanned.json` — add all newly processed post IDs to `scanned_ids` and set `last_run` to now (ISO 8601).

### 9. Present results

Show the top 10 problems to the user in a concise table, then prompt:

> Found N problems ranked by engagement. Run `/reddit-research` to automatically research the top 5, or tell me which problem numbers to focus on (e.g. "research problems 1, 3, 7").
