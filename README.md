# AI Playground 🚀

A collection of intelligent automation tools for extracting insights from newsletters, social media, and community forums. Each project is self-contained, designed to help you stay informed and identify opportunities across your digital channels.

**Status:** Active development | **Model:** Claude API (3.5 Sonnet) + Local embeddings | **Last Updated:** 2026-04-04

---

## Projects Overview

| Project | Purpose | Key Features |
|---------|---------|--------------|
| [Newsletter Insights](#newsletter-insights) | Auto-digest newsletters from Gmail | Topic classification, state tracking, scheduled runs |
| [Twitter Insights](#twitter-insights) | Auto-digest your Twitter home timeline | Tweet filtering, topic organization, stateless tracking |
| [Reddit Insights](#reddit-insights) | Extract tech problems from subreddits | Problem ranking, market research, opportunity scoring |
| [Search News & Twitter](#search-news-twitter) | Semantic search across all digests | RAG-powered, local vector DB, cross-source queries |

---

## Newsletter Insights

**Status:** ✅ Fully operational | **Setup Time:** ~5 min

Connects to your Gmail and surfaces the most important learnings from newsletters — organized by topic, completely on demand.

### How It Works

1. **Scan** → Fetches new newsletters from Gmail using the Gmail API
2. **Classify** → Groups content by topic using Claude's analysis
3. **Summarize** → Writes a human-readable digest organized by subject

Only emails not previously scanned are processed. State is tracked automatically in `data/scanned.json`, so future runs only process new newsletters.

### One-Time Setup

**Step 1:** Install dependencies
```bash
cd newsletter-insights
pip install -r requirements.txt
```

**Step 2:** Create Google Cloud credentials
- Go to [console.cloud.google.com](https://console.cloud.google.com)
- Create a new project
- Enable the **Gmail API** (APIs & Services → Library)
- Create OAuth 2.0 credentials:
  - Type: Desktop application
  - Scopes: `https://www.googleapis.com/auth/gmail.readonly`
  - Download JSON as `credentials.json` in the `newsletter-insights/` folder

**Step 3:** Authenticate
```bash
python scan_newsletters.py --auth
```
This opens a browser to authorize Gmail access and creates `token.json` for future runs.

### Usage

Invoke via Claude Code skill:
```
/newsletter-insights
```

Or run directly:
```bash
python scan_newsletters.py
```

Output: A markdown digest in `summaries/YYYY-MM-DD.md` containing all new newsletters grouped by topic.

### Configuration

The script detects newsletters using Gmail's query:
```
from:@substack.com OR subject:newsletter
```

You can modify `scan_newsletters.py` to add additional newsletter sources.

### File Structure
```
newsletter-insights/
├── scan_newsletters.py        # Gmail API integration
├── credentials.json           # OAuth credentials (git-ignored)
├── token.json                 # Auth token cache (git-ignored)
├── data/scanned.json          # Processed email ID tracking
└── summaries/                 # Generated digests (YYYY-MM-DD.md)
```

---

## Twitter Insights

**Status:** ✅ Fully operational | **Setup Time:** ~3 min

Monitors your Twitter home timeline and surfaces the most valuable insights — organized by topic.

### How It Works

1. **Fetch** → Pulls new tweets from your home timeline using the twikit library
2. **Filter** → Excludes retweets, only processes original tweets
3. **Classify** → Organizes content by topic using Claude
4. **Summarize** → Writes a digest to `summaries/YYYY-MM-DD.md`

State is tracked in `data/scanned.json` — only new tweets are processed on subsequent runs.

### One-Time Setup

**Step 1:** Install dependencies
```bash
cd twitter-insights
pip install -r requirements.txt
```

**Step 2:** Get your Twitter cookies
- Open [twitter.com](https://twitter.com) in your browser (must be logged in)
- Open DevTools (F12 or Cmd+Option+I)
- Navigate to **Application** → **Cookies** → `https://twitter.com`
- Copy the **Value** of: `auth_token` and `ct0`

**Step 3:** Create `.env` file
Create `twitter-insights/.env`:
```
AUTH_TOKEN=your_auth_token_here
CT0=your_ct0_here
```

**Step 4:** Verify authentication
```bash
python3 fetch_tweets.py --auth-check
```

Expected output: `Auth check passed — cookie is valid.`

### Usage

Invoke via Claude Code skill:
```
/twitter-insights
```

Or run directly:
```bash
python3 fetch_tweets.py
```

Output: A markdown digest in `summaries/YYYY-MM-DD.md` containing all new tweets grouped by topic.

### Cookie Management

The `auth_token` cookie typically remains valid for weeks to months. If you encounter authentication errors, simply repeat steps 2-3 above with a fresh cookie value.

### File Structure
```
twitter-insights/
├── fetch_tweets.py            # Timeline fetching via twikit
├── .env                       # Auth credentials (git-ignored)
├── data/scanned.json          # Processed tweet ID tracking
└── summaries/                 # Generated digests (YYYY-MM-DD.md)
```

---

## Reddit Insights

**Status:** ✅ Fully operational | **Setup Time:** ~5 min

Market research tool for discovering what problems people face in tech communities. Automatically scans subreddits, ranks problems by engagement, researches existing solutions, and identifies business opportunities.

### How It Works

**Stage 1-3: Problem Extraction**
- Fetches posts from your configured subreddits
- Extracts tech/software problems from post titles and top comments
- Ranks problems by engagement (upvotes, comment count)
- Outputs: Human-readable ranked list + structured JSON cache

**Stage 4-5: Market Research**
- Reads cached problems from Stage 1-3
- Searches for existing solutions across Reddit
- Analyzes solution quality, maturity, and market gaps
- Scores each problem's business opportunity potential
- Outputs: Detailed market research report with opportunity rankings

### One-Time Setup

**Step 1:** Install the Reddit MCP server
```bash
claude mcp add --transport stdio reddit-mcp-buddy -s user -- npx -y reddit-mcp-buddy
```

Verify installation:
```bash
claude mcp list
```

The `reddit-mcp-buddy` MCP is read-only and uses Reddit's public API — no Reddit account or API key required.

**Step 2:** Configure subreddits

Edit `data/subreddits.json`:
```json
{
  "subreddits": [
    { "name": "programming", "limit": 30, "sort": "hot" },
    { "name": "SideProject", "limit": 25, "sort": "hot" },
    { "name": "learnprogramming", "limit": 25, "sort": "hot" }
  ],
  "top_comments_per_post": 5,
  "min_score": 10
}
```

**Configuration options:**
- `sort`: `hot`, `new`, `top`, or `rising`
- `limit`: Max posts per subreddit (keep ≤ 50 for context efficiency)
- `min_score`: Skip posts below this upvote threshold (reduces noise)
- `top_comments_per_post`: How many top comments to analyze per post

### Usage

**Extract problems from subreddits:**
```
/reddit-problems
```

**Research problems and identify opportunities:**
```
/reddit-research
```

Or target specific problems:
```
/reddit-research research problems 1, 3, 5
```

### Outputs

- `problems/YYYY-MM-DD-problems.md` — Ranked list of discovered problems
- `data/problems.json` — Structured cache for research phase
- `problems/YYYY-MM-DD-research.md` — Market research report with opportunity scores

### File Structure
```
reddit-insights/
├── CLAUDE.md                  # Project documentation
├── data/
│   ├── scanned.json           # Processed post IDs
│   ├── subreddits.json        # Subreddit configuration
│   └── problems.json          # Extracted problems cache
└── problems/
    ├── YYYY-MM-DD-problems.md # Ranked problems
    └── YYYY-MM-DD-research.md # Market research report
```

### MCP Tools Used
- `browse_subreddit` — Fetch posts by sort order
- `get_post_details` — Fetch post with top comments
- `search_reddit` — Search for existing solutions

---

## Search News & Twitter

**Status:** ✅ Fully operational | **Setup Time:** ~10 min (first run includes dependency downloads)

Semantic search across all your newsletter and Twitter digests using a local vector database. Ask questions about what you've read, find topics across sources, and get cited answers powered by Claude.

### How It Works

1. **Index** → Automatically processes new summary files from Newsletter Insights and Twitter Insights
2. **Embed** → Chunks content by topic and embeds using `all-MiniLM-L6-v2` (local, no API key)
3. **Search** → Retrieves semantically similar chunks from ChromaDB
4. **Answer** → Generates a cited response using Claude, exclusively from retrieved content

All processing is local except for the final Claude API call. No web search, purely retrieval-augmented generation (RAG).

### One-Time Setup

**Step 1:** Install Ollama (optional, but recommended)
```bash
# Download from ollama.com
ollama pull llama3.2
```
This enables local LLM inference for advanced features. Size: ~2 GB.

**Step 2:** Install Python dependencies
```bash
cd search-news-twitter
pip install -r requirements.txt
```

Note: `sentence-transformers` installs PyTorch (~800 MB one-time). The embedding model (`all-MiniLM-L6-v2`, ~22 MB) is cached locally after first run.

**Step 3:** Build the initial index
```bash
python3 index.py
```

This scans `newsletter-insights/summaries/` and `twitter-insights/summaries/`, chunks by topic, and builds the ChromaDB vector store.

### Usage

Invoke via Claude Code skill:
```
/search-news-twitter
```

Or use the CLI directly:

```bash
# Basic search (both sources)
python3 search.py --query "database indexing trade-offs"

# Filter by source
python3 search.py --query "AI agent tools" --source twitter
python3 search.py --query "system design patterns" --source newsletter

# Retrieve more chunks for comprehensive results
python3 search.py --query "RAG retrieval" --top-k 8

# Filter by date range
python3 search.py --query "startup product" --date-from 2026-04-01
python3 search.py --query "security best practices" --date-from 2026-03-01 --date-to 2026-04-04
```

### How Chunking Works

Each `###` topic heading in a summary file becomes one searchable chunk with metadata:
- **source_type** — `newsletter` or `twitter`
- **date** — From filename (YYYY-MM-DD)
- **author** — Newsletter sender or Twitter handle
- **title** — Topic heading
- **tag** — Category: AI/ML, Engineering, Product, Business, Other

As you run Newsletter Insights and Twitter Insights over time, new summary files are automatically discovered and indexed on the next search.

### File Structure
```
search-news-twitter/
├── index.py                   # Indexing pipeline
├── search.py                  # Search CLI entry point
├── data/indexed.json          # Tracks indexed summary files
├── db/chroma/                 # ChromaDB persistent store (auto-created)
└── requirements.txt           # Python dependencies
```

---

## Getting Started

### Quick Start (All Projects)

```bash
# Clone and enter the playground
git clone <this-repo>
cd AI/Playground

# Start with any project
cd newsletter-insights
pip install -r requirements.txt
# ... follow project-specific setup

# Or invoke via Claude Code skills
/newsletter-insights
/twitter-insights
/reddit-problems
/reddit-research
/search-news-twitter
```

### Global Conventions

- **Skills** — Invoke with `/skill-name` from Playground root (e.g., `/twitter-insights`)
- **Project state** — Tracking files live in `<project>/data/`
- **Outputs** — Summaries and reports in `<project>/summaries/` or `<project>/problems/`
- **Secrets** — Never commit `credentials.json`, `token.json`, `.env`, or API keys

---

## Architecture & Design

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Claude 3.5 Sonnet (API) | Analysis, classification, summarization |
| **Orchestration** | Claude Code / MCP | Tool invocation, state management |
| **Data Sources** | Gmail, Twitter, Reddit | Newsletter, tweet, and community insights |
| **Embeddings** | sentence-transformers (local) | Semantic search without external APIs |
| **Vector Store** | ChromaDB | Persistent indexing of digests |
| **Infrastructure** | Python, Ollama (optional) | Local-first processing |

### Key Design Principles

1. **Local-first** — Minimize external dependencies. Embeddings and inference happen locally when possible.
2. **Stateful** — Track processed content to avoid re-processing (scanned.json, indexed.json).
3. **Composable** — Each project is independent but digestible together via Search News & Twitter.
4. **Low-friction** — Setup is minimal. Most tools require only Python and one cloud API connection.

---

## Data Privacy & Security

- **No data leakage** — Gmail, Twitter, and Reddit content stays local. Only queries and summaries hit the Claude API.
- **Credential management** — Secrets stored in `.env`, `credentials.json`, `token.json` — all git-ignored.
- **Read-only operations** — Newsletter and Twitter tools only fetch; Reddit MCP is read-only.

---

## Future Roadmap

- [ ] Hacker News Insights — Scan HN and extract trending topics
- [ ] Automatic scheduling — Cron-based daily digest generation
- [ ] Slack integration — Push digests directly to Slack
- [ ] Saved searches — Bookmark frequent queries for fast recall
- [ ] Trend detection — Identify emerging topics across 30+ days of digests
- [ ] Multi-user support — Shared digest repository

---

## Troubleshooting

### Newsletter Insights

**Issue:** `credentials.json not found`
- **Solution:** Complete the Google Cloud setup steps in the [Newsletter Insights section](#newsletter-insights)

**Issue:** `Auth token expired`
- **Solution:** Run `python scan_newsletters.py --auth` again to refresh

### Twitter Insights

**Issue:** `Auth check failed`
- **Solution:** Copy fresh cookies from DevTools (they expire after a few months)

**Issue:** No tweets being fetched
- **Solution:** Verify you're logged in on twitter.com and have followed accounts

### Reddit Insights

**Issue:** `reddit-mcp-buddy not found`
- **Solution:** Run `claude mcp list` to verify it's installed. Re-run the MCP install command if needed.

### Search News & Twitter

**Issue:** ChromaDB errors on first run
- **Solution:** Delete `db/chroma/` and re-run `python3 index.py`

**Issue:** `sentence-transformers` installation hangs
- **Solution:** This is normal the first time (PyTorch is large). Be patient or run with verbose flags: `pip install -v -r requirements.txt`

---

## Contributing

This is a personal playground for AI-powered tools. If you'd like to adapt any of these projects for your own use:

1. Fork the repository
2. Create your own project subfolder following the same structure
3. Add a `CLAUDE.md` describing the project
4. Update the Projects table above
5. Open a PR if you'd like to share improvements

---

## License

MIT — Feel free to use and adapt these tools for your own projects.

---

## Questions?

- 📚 See individual project `CLAUDE.md` files for detailed setup
- 🐛 Check the [Troubleshooting](#troubleshooting) section
- 🔗 Review the Architecture section to understand how projects fit together

**Happy exploring!** 🎯
