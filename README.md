# AI Playground 🚀

A collection of intelligent automation tools for extracting insights from newsletters, social media, and community forums. Each project follows a unified strategy: **gather ambient intelligence from dispersed sources, organize by signal, and make it searchable**.

**Vision:** Turn information overload into actionable insights by combining topic classification, semantic search, and opportunity ranking — all locally when possible.

**Status:** Active development | **Last Updated:** 2026-04-06

---

## Strategic Overview

### The Problem
You're exposed to newsletters, Twitter, Reddit, and other information channels daily. Information is scattered. Important signals are buried. It's hard to:
- Recall what you've read about a specific topic
- Find patterns across sources
- Identify market opportunities from community discussions
- Know what's timely (latest news) vs. archived knowledge

### The Solution
**Four complementary projects that work together:**

1. **Newsletter Insights** — Turn inbox chaos into organized summaries
2. **Twitter Insights** — Capture timeline insights before they disappear
3. **Reddit Insights** — Mine community feedback for problems and opportunities
4. **Search News & Twitter** — Unified semantic search across all sources

Each project is independent but composable. You can run one or all four. Their outputs feed into each other.

---

## Projects Overview

| Project | Purpose | Strategy |
|---------|---------|----------|
| **Newsletter Insights** | Auto-digest newsletters from Gmail | Classify by topic, track state, organize for later recall |
| **Twitter Insights** | Capture your Twitter home timeline | Filter signal, organize by topic, preserve before posts disappear |
| **Reddit Insights** | Extract tech problems from communities | Rank by engagement, research solutions, score market opportunities |
| **Search News & Twitter** | Unified search across digests | RAG-powered semantic search with intelligent fallback to live web |

---

## Newsletter Insights

**Status:** ✅ Fully operational

Turn your Gmail inbox of newsletters into organized, topic-based summaries. Rather than subscribing to dozens of newsletters and drowning in inbox volume, auto-digest them daily and browse by topic.

### Strategy

- **Scan** incoming newsletters (Substack, newsletters, etc.)
- **Classify** by topic using Claude analysis
- **Organize** by subject in a readable markdown digest
- **Track state** to process only new newsletters on future runs

Output: Daily digests in `summaries/YYYY-MM-DD.md` organized by topic. Persistent state in `data/scanned.json` prevents reprocessing.

### Key Insight

State-driven processing. Once a newsletter is scanned, it's marked complete. Future runs only process new emails. This prevents duplicate work and scales efficiently.

---

## Twitter Insights

**Status:** ✅ Fully operational

Capture insights from your Twitter timeline before they disappear. Tweets are ephemeral — they age fast and become unsearchable. This project preserves the signal.

### Strategy

- **Fetch** original tweets from your home timeline (filter out retweets)
- **Classify** by topic using Claude analysis
- **Organize** in daily digests by subject
- **Track state** to process only new tweets on future runs

Output: Daily digests in `summaries/YYYY-MM-DD.md` organized by topic. Persistent state in `data/scanned.json` prevents reprocessing.

### Key Insight

Stateless in the sense that tweets don't have inherent ordering — you process what's available today. But you track which tweets you've already seen to avoid duplicates and focus on new signal.

---

## Reddit Insights

**Status:** ✅ Fully operational

Mine tech communities for real problems people face, then research existing solutions to identify business opportunities.

### Strategy

**Stage 1: Problem Extraction**
- Scan configured subreddits for posts and comments
- Extract tech problems mentioned in titles and top comments
- Rank problems by community engagement (upvotes, comment count, signal strength)
- Output: Ranked problem list with engagement metrics

**Stage 2: Market Research**
- Take extracted problems and search Reddit for existing solutions
- Analyze solution quality, maturity, and market saturation
- Score each problem for business opportunity potential
- Output: Market research report with opportunity rankings

### Key Insight

Problems ranked by engagement are proxy signals for real pain. If 100+ people upvoted a problem, it matters. Then research whether solutions exist, are mature, or if there's a gap. This two-stage approach converts community signals into business validation.

---

## Search News & Twitter

**Status:** ✅ Fully operational

Unified semantic search across all your newsletter and Twitter digests with intelligent fallback to live web search. Ask questions once, get answers from both archived knowledge and current web data.

### Strategy

**Three-part search pipeline:**

1. **Smart Routing**
   - Detect if query needs current/live data (keywords: "latest", "today", "breaking", "stock price")
   - If live data needed → skip internal, go straight to web
   - If historical/knowledge question → try internal first

2. **Internal Search (Knowledge Base)**
   - Embed query locally using semantic embeddings
   - Search ChromaDB vector database of newsletter/Twitter summaries
   - Judge retrieved chunks with LLM to validate semantic match (0-10 score)
   - Only proceed if confidence ≥5 (high relevance)

3. **Fallback to Web**
   - If internal search fails or judge rejects → query DuckDuckGo for live results
   - Summarize web results and cite sources
   - Ensures you get current data when knowledge base is incomplete

### Key Insight

**Sequential fallback with intent validation.** Try cheap, fast internal search first (local vector DB + judgement gate). If that fails, fallback to web search. But be intelligent about routing — if you ask for "today's stock price", skip internal entirely because you need current data, not archived knowledge.

All decisions logged to SQLite for later analysis: routing choices, judge scores, fallback rates, query durations.

---

## How They Work Together

```
Gmail (newsletters) ──┐
                      ├──> Newsletter Insights ──────┐
                      │    (organize by topic)       │
                      │                               │
Twitter (timeline) ───┼──> Twitter Insights ────────┼──> Indexed Summaries (ChromaDB)
                      │    (capture & organize)      │
                      │                               │
                      ├──────────────────────────────┤
                                                     └──> Search News & Twitter
Reddit (communities) ─┴──> Reddit Insights              (semantic search + web fallback)
                           (rank problems, research)
```

Each project creates summaries that feed into the central search index. You can use projects independently or together. The key: **everything is searchable and organized by topic**.

---

## Global Conventions

- **Skills** — Invoke with `/skill-name` from Playground root
- **Project state** — Tracking files in `<project>/data/`
- **Outputs** — Summaries in `<project>/summaries/`, reports in `<project>/problems/`
- **Secrets** — Never commit `.env`, `credentials.json`, `token.json`, or API keys
- **Documentation** — Each project has its own `CLAUDE.md` with detailed setup

---

## Design Philosophy

### Principles

**1. Local-First**
- Embeddings computed locally (sentence-transformers)
- Inference on local LLM when possible (Ollama)
- Minimal external API dependencies (only Claude for analysis)
- Fast, private, cost-effective

**2. Stateful Processing**
- Track what you've seen (newsletters, tweets, posts)
- Process only new items on subsequent runs
- Prevents duplicate work and enables incremental updates
- Scalable without re-processing history

**3. Composable & Independent**
- Each project works standalone
- Or combine outputs via Search News & Twitter
- No hard dependencies between projects
- Mix and match based on your needs

**4. Topic-Based Organization**
- All content organized by topic (AI/ML, Engineering, Product, Business, etc.)
- Makes browsing and discovery natural
- Semantic search works better with topic context

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


## Future Roadmap

- [ ] Hacker News Insights — Extract trending tech topics
- [ ] Automatic scheduling — Daily digest generation
- [ ] Slack integration — Push digests to Slack
- [ ] Saved searches — Bookmark and re-run frequent queries
- [ ] Trend detection — Identify emerging topics over time
- [ ] Multi-source cross-reference — Show which sources discuss the same topic

---

## For Implementation Details

Each project has its own `CLAUDE.md` with:
- Detailed setup instructions
- Configuration options
- Troubleshooting guides
- Advanced usage patterns

Start there for specific project help.

---

## License

MIT — Use and adapt these tools freely for your own projects.
