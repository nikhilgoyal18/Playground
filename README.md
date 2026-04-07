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

### Strategy & Implementation

- **Fetch** — Scan Gmail for newsletters using Gmail API (Substack, newsletter mailing lists, etc.)
- **Classify** — Use Claude to group content by topic (AI/ML, Engineering, Product, Business, Other)
- **Summarize** — Generate readable markdown digests organized by topic with key learnings
- **State Tracking** — Track processed email IDs in `data/scanned.json` to avoid reprocessing

Output: Daily digests in `summaries/YYYY-MM-DD.md` organized by topic. Persistent state prevents reprocessing and enables efficient incremental updates.

### Architecture

**State-driven incremental processing:** Email IDs are tracked. Only new, unprocessed emails are fetched and analyzed. This scales efficiently — you're never re-analyzing old newsletters.

---

## Twitter Insights

**Status:** ✅ Fully operational

Capture insights from your Twitter timeline before they disappear. Tweets are ephemeral — they age fast and become unsearchable. This project preserves the signal by converting timeline noise into organized topic-based summaries.

### Strategy & Implementation

- **Fetch** — Pull original tweets from home timeline (filter retweets to focus on primary signal)
- **Classify** — Use Claude to organize by topic
- **Summarize** — Generate daily digests organized by subject with key insights
- **State Tracking** — Track processed tweet IDs in `data/scanned.json`

Output: Daily digests in `summaries/YYYY-MM-DD.md` organized by topic. Preserved copies of tweets before they age out of search.

### Architecture

**Tweet-level state tracking:** Each tweet ID tracked to prevent duplicates. Tweets themselves are ephemeral, but summaries persist. Enables timeline analysis over time without losing signal to Twitter's ordering algorithms.

---

## Reddit Insights

**Status:** ✅ Fully operational

Mine tech communities for real problems people face, then research existing solutions to identify business opportunities. Two-stage pipeline: problem extraction with engagement ranking, then market research with opportunity scoring.

### Strategy & Implementation

**Stage 1: Problem Extraction & Ranking**
- Scan configured subreddits (hot, new, top posts) for tech problems
- Extract problems from post titles and top comments
- Rank by engagement signals (upvotes, comment count, discussion volume)
- Output: Ranked problem list with metrics

**Stage 2: Market Research & Opportunity Scoring**
- Search Reddit for existing solutions to extracted problems
- Analyze solution maturity, adoption, market saturation
- Score business opportunity potential for each problem (high engagement + weak solutions = high opportunity)
- Output: Market research report with ranked opportunities

### Architecture

**Engagement-Based Ranking:**
Problems ranked by community engagement (upvotes, comments) as proxy for real pain points. 100+ upvotes signals genuine demand.

**Two-Stage Caching:**
Problem extraction cached in `data/problems.json`. Market research runs independently against cached problems. Enables re-research without re-extraction.

**Opportunity Scoring:**
Problems scored on two axes: (1) community demand (engagement), (2) solution availability (research). High demand + low availability = high opportunity.

---

## Search News & Twitter

**Status:** ✅ Fully operational

Unified semantic search across all your newsletter and Twitter digests with intelligent fallback to live web search. Built on **RAG (Retrieval-Augmented Generation)** architecture with local embeddings, semantic chunking, and intent validation.

### Architecture

**RAG Pipeline with Three-Part Flow:**

1. **Smart Routing**
   - Detect if query needs current/live data (keywords: "latest", "today", "breaking", "stock price")
   - If live data needed → skip internal, go straight to web
   - If historical/knowledge question → try internal first

2. **Internal Search (Semantic Retrieval)**
   - **Chunking:** Newsletter and Twitter digests chunked at bullet-level precision (not topic-level). Each bullet point becomes its own searchable chunk with topic/author context retained.
   - **Vectorization:** Query and chunks embedded locally using `sentence-transformers` (all-MiniLM-L6-v2 model, ~22 MB). No external embeddings API.
   - **Storage:** Embeddings persisted in **ChromaDB** vector database for fast semantic similarity search.
   - **Intent Validation:** Retrieved chunks passed through LLM judge that scores semantic match (0-10). Only chunks with score ≥5 proceed (eliminates low-confidence matches).
   - **Generation:** Relevant chunks passed to LLM to synthesize cited answer with `[Source N]` references.

3. **Fallback to Web**
   - If internal search fails or judge rejects → query DuckDuckGo for live results
   - Summarize web results and cite sources
   - Ensures current data when knowledge base is incomplete

### Key Technical Insights

**Bullet-Level Chunking:**
Each bullet under a topic heading becomes its own chunk, not entire topics. This enables granular retrieval — you get exactly the relevant bullet, not a topic block containing 10 tangential bullets.

**Local Embeddings:**
Vector computations happen locally (no embedding API cost or latency). Query embedding + similarity search are instant. ~22 MB model cached after first run.

**Judge Gate:**
LLM validates that retrieved content actually matches intent (prevents false positive retrievals). Score threshold (≥5) acts as quality filter. Retries up to 3 times on parse errors to ensure reliability.

**All Decisions Logged:**
Every search decision (route choice, chunks retrieved, judge score, fallback trigger) logged to SQLite. Enables analysis of system performance and user behavior over time.

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

## Technical Architecture

### Core Concepts

**1. Semantic Chunking & Vectorization**
- Content chunked at meaningful boundaries (bullet-level precision, not document-level)
- Chunks embedded using local sentence-transformers (all-MiniLM-L6-v2, ~22 MB)
- Embeddings stored in ChromaDB for sub-millisecond semantic similarity search
- No external embedding APIs — all computation local and cached

**2. State-Driven Incremental Processing**
- Each project tracks processed IDs (newsletters, tweets, Reddit posts)
- Only new, unprocessed items analyzed on subsequent runs
- Prevents duplicate LLM calls and scales to months of history
- State stored in JSON files (`scanned.json`, `indexed.json`) for simplicity

**3. RAG (Retrieval-Augmented Generation)**
- Search News & Twitter uses RAG architecture: retrieve relevant chunks, then generate answers with context
- Judge gate validates semantic relevance before generation (0-10 score, threshold ≥5)
- Fallback to web search if internal retrieval fails
- All decisions logged to SQLite for analysis and debugging

**4. Topic-Based Organization**
- All summaries classified by topic (AI/ML, Engineering, Product, Business, Other)
- Enables natural browsing and better semantic search performance
- Topic context included in embeddings for improved relevance

**5. Local-First, Privacy-Focused**
- Gmail, Twitter, Reddit content stays local
- Embeddings computed locally (no external API)
- Only Claude API used for content analysis (not data storage)
- Ollama optional for local LLM inference
- Cost-efficient: embeddings are cached, reused across queries

---

## Data Privacy & Security

- **No data leakage** — Gmail, Twitter, and Reddit content stays local. Only queries and summaries hit the Claude API.
- **Credential management** — Secrets stored in `.env`, `credentials.json`, `token.json` — all git-ignored.
- **Read-only operations** — Newsletter and Twitter tools only fetch; Reddit MCP is read-only.

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
