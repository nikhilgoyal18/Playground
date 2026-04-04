# Reddit Insights

Market research tool: scan subreddits for tech/software problems people face, rank them by engagement, research existing solutions, and identify opportunities.

## Setup

### 1. Install the Reddit MCP server (one-time)

```bash
claude mcp add --transport stdio reddit-mcp-buddy -s user -- npx -y reddit-mcp-buddy
```

Verify it's connected:
```bash
claude mcp list
```

The `reddit-mcp-buddy` MCP is read-only and uses Reddit's public API — no Reddit account or API key needed.

### 2. Configure subreddits

Edit `data/subreddits.json` to add the subreddits you want to monitor:

```json
{
  "subreddits": [
    { "name": "programming", "limit": 30, "sort": "hot" },
    { "name": "SideProject", "limit": 25, "sort": "hot" }
  ],
  "top_comments_per_post": 5,
  "min_score": 10
}
```

- `sort`: `hot`, `new`, `top`, or `rising`
- `limit`: max posts to fetch per subreddit (keep ≤ 50 to avoid context overload)
- `min_score`: skip posts below this upvote count (reduces noise)

## Usage

### Stage 1-3: Problem Extraction

```
/reddit-problems
```

Fetches posts from configured subreddits, extracts tech/software problems, scores and ranks them, and writes:
- `summaries/YYYY-MM-DD-problems.md` — human-readable ranked list
- `data/problems.json` — structured cache for Stage 4-5

### Stage 4-5: Market Research

```
/reddit-research
```

Reads `data/problems.json`, searches for existing solutions, and writes:
- `summaries/YYYY-MM-DD-research.md` — market research report with opportunity scores

You can target specific problems: "research problems 1, 3, 5"

## File Structure

```
reddit-insights/
├── CLAUDE.md                   # This file
├── data/
│   ├── scanned.json            # Processed post IDs (prevents re-scanning)
│   ├── subreddits.json         # Subreddit configuration
│   └── problems.json           # Extracted problems cache (written by /reddit-problems)
└── summaries/
    ├── YYYY-MM-DD-problems.md  # Ranked problem list
    └── YYYY-MM-DD-research.md  # Market research report
```

## MCP Tools Used

- `browse_subreddit` — fetch posts from a subreddit by sort order
- `get_post_details` — fetch a post with its top comments
- `search_reddit` — search Reddit for existing discussions (used in research phase)
