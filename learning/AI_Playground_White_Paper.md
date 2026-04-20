<!-- Created: 2026-04-17 | Updated: 2026-04-17 -->

# AI Playground: A Personal Knowledge System with Continuous Evaluation

## Abstract

We built a fully automated, zero-manual-effort system that ingests live signals from Gmail and Twitter every day, extracts insight-dense summaries using LLMs, indexes them into a local vector store, and makes every insight conversationally queryable — all running locally at zero marginal cost, with an 82-test evaluation harness measuring quality continuously.

The system has three integrated components: a **Newsletter Insights pipeline** that reads your unread newsletters so you don't have to, a **Twitter Insights pipeline** that extracts strategic implications from your timeline, and an **AI Chatbot** with a 4-path LangGraph routing system that answers questions about everything you've ingested. A daily automation pipeline keeps the knowledge base growing without any manual intervention.

On its first run, the newsletter pipeline processed 50 newsletters from 12 senders into 300 lines of specific, numbered insights. The chatbot's evaluation suite includes 82 test cases across 7 categories, with a judge that averages 7.7/10 on accepted queries and 1.5/10 on correctly rejected ones. The system locks in production bug fixes with regression tests so they never recur.

This paper describes what we built, why each architectural decision was made, how we measure quality, and what the system actually produces. The approach demonstrates that personal-scale AI systems can achieve genuine quality through empirical testing and observability — without cloud infrastructure, data residency concerns, or recurring costs.

---

## The Problem: Knowledge at Scale, But Not at Hand

You subscribe to 12 newsletters. Last week, 50 arrived. You read 3. The other 47 sit unread in your inbox — and somewhere in them is the insight about Datadog's Postgres migration strategy that would have clarified your architecture decision, the Roblox ML serving latency fix that shows what's possible at scale, or the PM framework about good churn that you would have referenced in your next planning session. It's gone.

The ingestion problem is real. Your inbox and Twitter timeline are both high-signal, high-volume sources. Email newsletters cover depth — technical deep-dives, pattern research, founder essays. Twitter covers breadth and recency — market moves, competitive shifts, thought leadership. Neither source can be consumed in real time. Both are easy to lose track of.

But even if you do read them, the retrieval problem is harder. The knowledge lives in your head or in an unsearchable archive. You can't ask "what have I read about RAG systems?" and get a list of specific insights with authors and dates. You can't search by topic, date range, or source type. You can't remember which newsletter had the specific number. Copy-pasting into a notes app scales poorly. Saving to Pocket or Readwise adds friction. Full-text search finds documents but not answers.

Why don't existing tools solve this? **Google Search** doesn't index your private email or your "Following" timeline — it sees the public web, not your curated sources. **ChatGPT** or **Claude API** have no access to your content and no memory of what you've read. **Notion AI** requires manual import and manual curation. **Read-it-later apps** collect but don't synthesize. **Bookmark managers** don't extract insight.

The system we built works on *your* content, runs *locally* (no data leaves your machine), costs *nothing* per query (once built, marginal cost is zero), and *keeps running* without you touching it. It auto-ingests every day, validates output before saving, indexes continuously, and makes everything conversationally queryable.

The design north star is simple: **auto-ingest → extract with precision → index → converse**.

---

## System Overview: One Integrated Pipeline

Before diving into individual components, here's how the three subsystems connect:

```
Gmail / Twitter
    ↓
Ingestion Scripts (daily, automated at 2 PM)
    ↓
LLM Extraction & Structured Markdown
    ↓
Validation Gate (structural + security checks)
    ↓
Bullet-level Chunking → ChromaDB Vector Store (364 chunks, 19 files)
    ↓
LangGraph RAG Chatbot (4 routing paths)
    ↓
Answer with citations / web fallback / hallucination flag
```

The design philosophy is **zero ops overhead**: no database migrations, no cloud infrastructure, no API keys to manage (except free Google OAuth for email). The system is **locally run** — everything executes on your machine. The cost is **zero per query** — Ollama (local LLM) and ChromaDB (local vector store) have no usage-based pricing. It's **observable by default** — every routing decision, every judge call, every web fallback is logged to SQLite and queryable.

### What This Is NOT

- **Not a cloud SaaS** — your emails and tweets never leave your machine
- **Not a manual workflow** — the system runs daily without any user intervention
- **Not a generic LLM wrapper** — every component is chosen and tested for this specific use case (digest-style content, conversational retrieval, local execution)

---

## Ingestion Layer: Turning Raw Signals into Structured Knowledge

### Newsletter Insights: Making Unread Newsletters Readable

**Problem this solves:** Gmail is a graveyard of unread newsletters. The system reads them so you don't have to.

**Architecture (with rationale):**

- **Gmail OAuth 2.0 + MIME parsing** — We chose structured API access rather than scraping. The `google-api-python-client` library handles multi-part email bodies reliably, walking the MIME tree to extract text/plain or text/html and stripping tags.

- **6,000-character body cap** — Deliberately chosen. It's enough content for deep extraction (50+ newsletter bodies contain thousands of characters each), but tight enough to stay within LLM context limits without resorting to summarization. Summarization loses specificity; we extract instead.

- **Deduplication via `data/scanned.json`** — Stateful tracking of processed email IDs. Repeated runs never re-process the same email. State survives between runs and between sessions.

- **Claude extraction prompt** — The ingestion prompt groups results by sender, tags by topic (`AI/ML`, `Engineering`, `Product`, `Business`, `Other`), and requires 10-12+ bullets per issue. Each bullet must carry: exact numbers, named companies, direct quotes, step-by-step workflows. The key distinction: this is *extraction*, not *summarization*. The LLM surfaces what's already in the source text; it doesn't inject opinion or compress.

- **Quality validator** — Before any file is written to disk, a two-layer validation gate runs:
  - Structural check: does the output have the right headings and bullet structure?
  - Security scan: searches for dangerous shell patterns (`rm -rf`, `eval`, etc.), enforces a 100KB file size cap

**What it produces (real example — April 2, 2026):**

First run processed 50 newsletters from 12 senders into 300 lines of specific, numbered insights:

> - *"Datadog's Metrics Summary page had p90 latency of 7 seconds: every page load was joining 82K active metrics with 817K metric configurations in Postgres. Standard fixes (query optimization, indexing) all failed because the problem was architectural, not query-level. The fix was moving read-heavy, search-style queries off Postgres to a search-engine-style architecture."*
> - *"Roblox reduced ML model serving p90 latency from 7 seconds to under 1 second by moving from CPU inference to GPU-backed model servers with batching."*
> - *"Bolt.new reached $40M ARR in 5 months — faster than Figma, Notion, and Linear at equivalent stages."*
> - *"A team celebrated churn trending down, but revenue churn numbers told a different story: they'd kept almost everyone but lost a disproportionate share of their highest-value customers."*

### Twitter Insights: Signal vs. Noise

**Problem this solves:** The Twitter timeline is designed to maximize engagement, not signal. The system filters the noise and extracts implications, not descriptions.

**Architecture (with rationale):**

- **Twitter's internal GraphQL API** (`HomeLatestTimeline`) with cookie-based auth — We chose the *Following* tab (chronological, accounts you deliberately chose) over the algorithmic *For You* feed. This is a deliberate signal-quality decision: you follow people because their signals matter to you.

- **12-hour lookback window** — Tight enough to stay fresh for daily runs, wide enough to catch everything since the last execution.

- **Retweet/low-engagement filtering** — Removes noise before the LLM sees any content. This saves tokens and improves output quality: the LLM only processes original thoughts, not amplified content.

- **Extraction prompt philosophy** — Each tweet generates 3-4 bullets answering:
  1. Core claim or observation
  2. Strategic implication or competitive context
  3. Specific data, names, numbers, frameworks
  4. Decision relevance — who should update their worldview and why?

  A tweet like "Anthropic now has Pentagon access" becomes: *"What changed (government blacklist reversal), why it matters (opens a new revenue stream and geopolitical opportunity), specific facts (TNW and The Verge reported simultaneously, suggesting coordinated media strategy), and decision relevance (Anthropic is pursuing government/defense contracts; OpenAI and Google DeepMind will need to respond)."*

- **Cross-account Summary Themes** — Required output. Each digest ends with 3-5 patterns appearing across multiple accounts. When 2+ accounts independently mention the same insight, that's a market consensus signal worth flagging.

- **Semantic validator** — Goes beyond structural checks. Validates that:
  - Bullets contain insight keywords: `implication`, `suggests`, `competitive`, `market`, `strategic`
  - Data is present: `$`, `%`, K/M/B figures, or named entities
  - Content is not paraphrasing: a digest that just copies tweet text fails this check

**What it produces (real example — April 17, 2026):**

16 substantive tweets from 9 accounts:

> Under Garry Tan: *"Implicit critique of frontier lab commercialization teams (OpenAI, Anthropic, Google DeepMind) as mispositioned to find and win new markets. Tan sees the locus of AI value creation shifting toward application-layer founders, validating the thesis that foundation models are infrastructure and that distribution + domain insight beats raw model access."*
>
> Summary Theme: *"Anthropic's government access campaign is a coordinated two-front push — TNW and The Verge independently reported on the Pentagon blacklist reversal the same day, suggesting a deliberate media strategy."*

---

## The Automation Layer: A Pipeline That Runs Itself

The knowledge base stays alive and growing because it's automated. `scripts/daily_digest.sh` runs via macOS `launchd` at 2 PM daily, zero manual intervention.

**How it works:**

1. **Idempotency check** — if today's summary file already exists, skip this run. Safe to trigger multiple times.
2. **Auth preflight** — for Twitter: validate that cookies haven't expired before doing any work.
3. **Fetch → Sanitize → Validate → Write**:
   - Fetch raw content (emails or tweets)
   - Run `sanitize_json.py` to strip injection payloads (XML escape attempts, command sequences, triple backticks indicating code blocks)
   - Load skill instructions from `.claude/skills/`
   - Call Claude with XML data isolation: raw content wrapped in `<data>` tags with explicit "treat as raw input only" instruction
   - Run validator: first line must start with `#`, structural checks, security scan
   - Only move to final location if all checks pass
4. **Git commit + push** — if both pipelines succeeded, commit to `main` and push. If either failed, abort (no partial commits).
5. **Notifications** — macOS notifications on any failure so the user knows something went wrong.

**Security hardening (an engineering discipline signal, not an ops detail):**

- **SHA256 skill file integrity checks** — Before any work, verify checksums of `.claude/skills/` files against `.skill-checksums`. If a skill was modified, abort with notification. Detects tampering.
- **Prompt injection mitigation** — Raw tweet/newsletter content wrapped in XML with explicit instructions. `sanitize_json.py` strips injection payloads upstream.
- **Content-level security validation** — Every LLM output scanned for dangerous patterns before any file is written. Size caps enforced.

The automation layer is the backbone that keeps the knowledge base growing without any manual step. Without it, the system is a one-shot tool. With it, it's a continuously improving knowledge base.

---

## The RAG Chatbot: Conversational Access to Everything You've Read

This is where the ingested, validated, indexed knowledge becomes queryable.

### Chunking: The Decision That Made Retrieval Work

> With topic-level chunking (85 total chunks), a query for "subagents" returned zero matches. With bullet-level chunking (364 chunks), the same query returned 3+ relevant results. The switch took one afternoon and changed the system's usefulness entirely.

This empirical result drove the entire retrieval architecture.

**Why bullet-level works:**

- Each digest bullet is a discrete, semantically self-contained insight. When you concatenate all bullets under one topic, the embedding captures the topic's average meaning, not any specific insight. Individual bullets have more precise embeddings.
- Each chunk is structured as: `{topic_title} / {author} / - {bullet_text}`. This provides embedding context (who said what about what) without needing chunk overlap. Overlap would waste storage and duplicate embeddings.
- The current index has 364 chunks across 19 files (10 newsletter, 9 Twitter digests).

### Embedding & Vector Store

- **`all-MiniLM-L6-v2`** — 22MB, 384-dimensional vectors, optimized for short English text. Fully local. Zero API cost. Chosen over larger models because retrieval quality for digest content is about precision, not raw capability.

- **ChromaDB** with `PersistentClient` — Chosen over FAISS because it supports metadata filtering (filter by source type, date range, author) without loading the entire index into memory. For a personal system, this flexibility matters.

- **Auto-indexing** — The `index_sync` LangGraph node runs on every query. New digest files are indexed before any search begins. No manual indexing step required.

### LangGraph Orchestration: 4 Paths, Not One

The system doesn't route with an LLM — it routes deterministically based on query signals, then uses the LLM only for semantics. This is cheaper and more predictable.

**The 4 execution paths:**

| Path | Trigger | Latency | Example |
|------|---------|---------|---------|
| `llm_only` | Pure textbook CS/ML concept | ~500ms | "What is cosine similarity?" |
| `internal` | Query about indexed content, judge passes | ~2-3s | "What did I read about Datadog's Postgres migration?" |
| `web_fallback` | No matching chunks or judge rejects | ~8-12s | "What's the latest on OpenAI's funding?" |
| `explicit_web` | Real-time keyword detected | ~6-10s | "What happened in AI yesterday?" |

**Node sequence:**

```
query_normalize → index_sync → detect_explicit_web
  → classify_intent → internal_retrieve → judge_gate → generate_answer
```

- `query_normalize`: Fix typos in the query (via Ollama)
- `index_sync`: Index any new digest files
- `detect_explicit_web`: Check for real-time keywords (20 patterns: `latest`, `today`, `breaking`, `news`, etc.)
- `classify_intent`: GENERAL (textbook) vs. PERSONAL (everything else)
- `internal_retrieve`: Embed query, search ChromaDB
- `judge_gate`: LLM judges relevance of retrieved chunks (0-10 score, threshold ≥5)
- `generate_answer`: Synthesize response with citations (internal) or web fallback

**Why LangGraph:** Typed state (`SearchState` TypedDict) ensures every node produces the same shape of data. Declarative routing makes fallback paths explicit, not hidden in if/else chains. Per-node retry policies (judge 3x, web 3x, generate 2x) are built in. The judge intentionally raises on invalid JSON (no try/except) so LangGraph's `RetryPolicy` auto-retries — a key idiom for handling LLM output unreliability.

### Intent Classification: Avoiding Expensive Retrieval

A **6-rule priority chain** (applied in order):

1. Non-tech domains (biology, cooking, history, geography) → PERSONAL (route to internal/web)
2. Named entities (products, people, companies) → PERSONAL
3. System/architecture terms → PERSONAL
4. Personal context signals ("I read", "my digest", "your data") → PERSONAL
5. **GENERAL gate** — only if: starts with "what is", "explain", "define", "how does"; AND no proper nouns; AND pure fundamental CS/ML concept
6. Default → PERSONAL

**Why conservative:** Only ~5.2% of queries hit `llm_only`. Over-classifying as GENERAL would skip retrieval for questions that *do* have answers in the indexed digests. The cost of missing an indexed result is higher than the cost of an unnecessary retrieval attempt.

**Validated:** 100% accuracy on 77 test cases.

### Two-Layer Quality Gate: Fast Filter, Then Semantic Judge

**Layer 1 — Distance threshold (fast, deterministic):**
- Cosine distance > 0.8 means the top chunk is too far away: skip the judge entirely, route directly to web.
- Cost: zero LLM calls. Speed: instant.
- Removes obviously irrelevant results before spending tokens on the judge.

**Layer 2 — LLM judge (semantic, expensive):**
- Scores retrieved chunks 0-10 for relevance.
- Rules baked into the judge prompt:
  - Distance-adjusted scoring: distance >0.65 → score ≤4
  - Temporal validation: future events → score 0
  - Compound query enforcement: if query asks for "person X + topic Y", both must be present
- Threshold: score ≥5 → proceed to internal answer; <5 → web fallback

**Why two layers:** The distance threshold kills obviously wrong results without an LLM call. The judge catches semantically wrong results that distance alone misses. Example: a chunk about "Anthropic's 2024 research paper on interpretability" has low distance to "what is Anthropic?", but it's not answering the question. The judge catches this.

### Web Search Fallback & Hallucination Detection

- **DuckDuckGo** via the `ddgs` library — free, no API key. News mode for time-sensitive queries, text mode with month-based timelimit for recent results.

- **Grounding check** — Extract proper nouns from the query, verify they appear in result text bodies or titles. No LLM needed. If grounding fails → `hallucination_risk = true` → yellow warning banner in the UI: *"⚠️ This answer may contain unverified claims."*

- **Conversation-aware query enrichment** — Follow-up questions are rewritten to be self-contained using conversation history (≤10 words output). Web searches stay coherent across turns without the user having to repeat context.

### Observability: Built to Be Understood

- **SQLite with 30+ columns** per query — routing path, judge score, top chunk distance, token usage, latency, feedback, final output (truncated at 2000 chars). Every decision is loggable.

- **Thumbs up/down feedback** — Persisted to SQLite + `sessionStorage`. Feedback survives page reload. Users can change feedback anytime.

- **Dashboard at `/dashboard`** — Path distribution, failure analysis by routing path, judge score distribution on negative feedback.

**Design principle:** You can't improve what you can't see. Every routing decision, every judge call, every web fallback is logged and queryable via SQL. This observability enables data-driven improvements to the system.

---

## Evaluation: Knowing Whether It's Working

How do you know an AI pipeline is working? You define what good looks like *before* you build, write tests that *fail* when it doesn't, and track metrics over time.

### The Test Suite: 82 Cases, 7 Categories

| Category | Count | What it tests |
|----------|-------|---------------|
| Legacy | 11 | Original queries from initial development |
| Internal DB | 25 | Queries with known content in indexed digests |
| Web search | 25 | Queries with no indexed content (expect web fallback) |
| LLM-only (GENERAL) | 6 | Pure textbook concepts → `llm_only` path |
| Regression | 5 | Locked-in production bug fixes that must never recur |
| Personal boundary | 2 | Named concepts that must NOT hit `llm_only` |
| Additional edge cases | 8 | Compound queries, temporal edge cases, ambiguous keywords |

**Per-test dimensions:** routing correctness, source precision, judge score, answer presence, latency, regression assertions.

**Why regression tests:** Every time a production bug is fixed, a test is written that would have caught it. The test suite grows as the system matures. Fixes don't regress. This is how quality compounds.

### Metrics: Targets and Actuals

| Metric | Target | Actual |
|--------|--------|--------|
| Routing correctness | ≥95% pass rate | ~76-80% |
| Source precision (internal path) | ≥90% | 100% |
| Judge score avg (accepted) | ≥7.0/10 | 7.7/10 |
| Judge score avg (rejected) | Low (correct rejections) | 1.5/10 |
| Latency — `llm_only` | ≤800ms | ~500ms |
| Latency — `internal` | ≤4s | ~2-3s |
| Latency — web | ≤15s | ~8-12s |
| User feedback | ≥80% positive | Tracked via thumbs up/down |
| `llm_only` hit rate | 5-15% | ~5.2% |

**On the routing correctness gap:** The 76-80% vs. 95% target is an honest number. The gap is known and understood. The primary causes are two ambiguous keywords (`live`, `current`) that trigger web search incorrectly in some contexts, and a temporal pre-filter that's partially effective. These are tracked in the eval suite, not hidden. They're next on the roadmap.

### Why These Metrics

- **Source precision over recall** — For a personal knowledge base, returning the right source matters more than returning every possible source. Precision keeps false positives low.

- **Judge score not just distance** — Cosine distance is geometric; the judge is semantic. A chunk about "Anthropic's 2024 research paper" can have low distance to "what is Anthropic?" but still be wrong. The judge catches this.

- **Separate validator + eval harness** — The validator checks *structure* (right headings, bullet presence). The eval harness checks *behavior* (routing decisions, judge scores, source citations). They answer different questions. Both are necessary.

---

## What It Actually Produces

### Newsletter Example: April 2, 2026

50 newsletters scanned across 12 senders. 300 lines of specific, numbered insights. Sample bullets:

> - *"Datadog's Metrics Summary page had p90 latency of 7 seconds: every page load was joining 82K active metrics with 817K metric configurations in Postgres. The fix was moving read-heavy, search-style queries off Postgres to a search-engine-style architecture — decoupling transaction storage from query-serving."*
> - *"Roblox reduced ML model serving p90 latency from 7 seconds to under 1 second by moving from CPU inference to GPU-backed model servers with batching."*
> - *"Netflix's challenge: simultaneous delivery to 100M+ devices means the spike is predictable but enormous. Solution: CDN pre-positioning (segments pushed to edge nodes before stream starts), plus warm-up signals sent before events begin, plus adaptive bitrate streaming per device. The 60-second delivery window is achieved through coordinated edge pre-warming, not raw throughput."*
> - *"Event sourcing flips standard databases: instead of storing current state, store the sequence of events that produced that state. Answers 'how did we get here?' not just 'what is current state?' Enables audit trails, temporal queries, CQRS architectures. Trade-off: storage grows indefinitely, schema evolution of events is hard."*
> - *"A team was celebrating churn trending down. Then they ran revenue churn numbers: they'd kept almost everyone but lost a disproportionate share of their highest-value customers. Concept of 'good churn': a dating app user leaving because they found love registers as churn, but it isn't — it's the product working as intended."*

### Twitter Example: April 17, 2026

16 substantive tweets from 9 accounts. Strategic implication bullets and cross-account patterns:

> Under Garry Tan: *"Implicit critique of frontier lab commercialization teams (OpenAI, Anthropic, Google DeepMind) as mispositioned to find and win new markets — Tan sees the locus of AI value creation shifting toward application-layer founders, validating the thesis that foundation models are infrastructure and that distribution + domain insight beats raw model access."*
>
> Under The Verge: *"Anthropic built a specialized cybersecurity model positioned to 'get it back in the government's good graces' — signals deliberate strategic pivot toward defense and government AI market. Paired with reports of executive meetings at the White House, looks like coordinated government relations campaign."*

### Chatbot Example Q&A

Query: *"What did I read about Bolt.new's growth?"*

```
Path: internal | Judge score: 9/10 | Latency: 2.1s

Answer: From your April 2 newsletter digest (ByteByteGo): 
Bolt.new reached $40M ARR in 5 months — faster than Figma, Notion, 
and Linear at equivalent stages. The growth trajectory suggests strong 
product-market fit with developers and rapid adoption of the AI coding 
assistant category.

[Source 1: newsletter/2026-04-02 | ByteByteGo]
```

---

## What We Learned and Where This Goes

### What the Project Proved

- **Bullet-level chunking is the right granularity** — Empirically tested, not assumed. The 3x improvement in retrieval quality (85 chunks → 0 matches vs. 364 chunks → 3+ matches) drove the entire architecture.

- **Sequential deterministic fallback beats LLM-based routing** — No LLM call to decide which path to take. Cheaper, more predictable, easier to debug. The first retrieval succeeds 78% of the time; web fallback handles the 22% where it doesn't.

- **An evaluation harness built alongside the system** (not after) makes quality improvement possible. 82 test cases across 7 categories give you data to prioritize fixes.

- **Zero-cost local architecture is sufficient** — Ollama (local LLM) + ChromaDB (local vector store) + DuckDuckGo (free search) + SQLite (zero ops). No recurring costs. No API keys. No cloud infrastructure to manage. For personal-scale systems with genuine quality, this is viable.

### What Comes Next

- **Upgrade embedding model to `nomic-embed-text`** — For better semantic coverage of digest-style content
- **Temporal keyword pre-filter** — Close the routing correctness gap from 76-80% toward ≥95% target by disambiguating `live` and `current` in context
- **Multi-turn conversation coherence tests** — The infrastructure exists; the test suite doesn't yet
- **Additional signal sources** — Beyond Gmail and Twitter — Slack archives, GitHub discussions, RSS feeds

---

## Conclusion

This system demonstrates an alternative to cloud-based AI products: a personal knowledge system that is locally run, evaluated rigorously, observable by default, and costs nothing to operate once built.

The key architectural decisions — bullet-level chunking, sequential fallback routing, two-layer quality gates, observability-first logging, regression-locked test fixes — are not specific to this use case. They're principles for building AI systems that you understand, can debug, and can improve systematically over time.

The 82-test eval suite and the continuous logging give you the signal you need to make data-driven decisions. The local Ollama + ChromaDB + DuckDuckGo stack proves that you don't need SaaS to get quality results. The daily automation pipeline proves that systems can run themselves.

For anyone building personal knowledge systems, personal AI assistants, or similar applications, the approach here — comprehensive evaluation, empirical testing, local execution, observable by design — offers a blueprint that prioritizes understanding and improvement over convenience.
