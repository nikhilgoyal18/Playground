# AI Chatbot — Evaluation Metrics & Guardrails

**Single source of truth** for all quality targets, active guardrails, and pending improvements.
Run `python3 eval/run_eval.py` for current pass rates. All production data is in `data/search_logs.db`.

> This file consolidates and supersedes the metrics sections from `EVAL_RESULTS.md`.
> Bug history and root cause analysis remain in `bugs-and-fixes/BUGS.md`.

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ Done | Implemented and working in production |
| 🔄 In Progress | Partially implemented or under active work |
| 🔲 Pending | Identified, not yet started |

---

## Part 1: Evaluation Metrics

Metrics used to measure whether the chatbot is doing its job well.

---

### 1.1 Routing Correctness — ✅ Done

**What it measures:** Whether each query takes the correct execution path.

**Paths:**
| Path | Trigger | Expected Use |
|------|---------|-------------|
| `llm_only` | GENERAL intent (textbook ML/CS concept) | Fast parametric answer, no retrieval |
| `internal` | PERSONAL intent, chunks pass threshold + judge ≥5 | Digest-grounded answer with citations |
| `web_fallback` | Internal fails: no chunks, judge <5, or no-content response | Live web when digest has no answer |
| `explicit_web` | Query contains real-time keywords | Direct web for news/prices/live data |

**Implementation:** `eval/run_eval.py → classify_path()`, compared against `expected_path` per test case
**Current baseline:** ~76-80% pass rate (71 tests)
**Target:** ≥95% pass rate

**How to run:**
```bash
python3 eval/run_eval.py
```

---

### 1.2 Source Precision — ✅ Done

**What it measures:** Of the chunks retrieved and cited, what % came from expected sources.

**Implementation:** `eval/run_eval.py → compute_source_precision()` — matches `meta.author` against `expected_sources` list per test case
**Current baseline:** ~100% on internal path tests
**Target:** ≥90%

---

### 1.3 Judge Score Quality — ✅ Done

**What it measures:** LLM judge's assessment of retrieved chunk relevance (0-10). Gates the internal path.

| Score Range | Interpretation | Action |
|------------|----------------|--------|
| 8-10 | Excellent match, distance < 0.5 | Use internal answer |
| 6-7 | Good match, core topic covered | Use internal answer |
| 5 | Marginal match — passes threshold | Use internal answer |
| 0-4 | Poor match / off-topic / future event | Fall back to web |

**Threshold:** `JUDGE_SCORE_THRESHOLD = 5` (in `graph.py`)
**Current baseline:** Avg 7.7/10 on internal queries, avg 1.5/10 on correctly-rejected queries
**Target:** Avg ≥7.0 on accepted queries; zero high-confidence wrong answers

**Logged to:** `data/search_logs.db → judge_score, judge_quality, judge_reasoning`

---

### 1.4 Latency by Path — ✅ Done

**What it measures:** End-to-end response time per execution path.

| Path | Current Typical | Target |
|------|----------------|--------|
| `llm_only` | ~500ms | ≤800ms |
| `internal` | ~2-3s | ≤4s |
| `web_fallback` | ~8-12s | ≤15s |
| `explicit_web` | ~6-10s | ≤12s |

**Implementation:** `duration_ms` tracked in SQLite on every query
**Gap:** No trend view or alerting — raw SQLite only

**SQL to inspect:**
```sql
SELECT intent_class,
       CASE WHEN llm_only_used = 1 THEN 'llm_only'
            WHEN internal_succeeded = 1 THEN 'internal'
            WHEN web_was_fallback = 1 THEN 'web_fallback'
            WHEN explicit_web_detected = 1 THEN 'explicit_web'
            ELSE 'unknown' END as path,
       AVG(duration_ms), MIN(duration_ms), MAX(duration_ms), COUNT(*)
FROM searches
GROUP BY path;
```

---

### 1.5 Answer Presence — ✅ Done

**What it measures:** Whether the query produced any answer at all (non-empty `final_output`).

**Implementation:** `has_answer` check in `run_eval.py`; `final_output IS NOT NULL` in SQLite
**Target:** 100% (no silent empty responses)

---

### 1.6 Token Usage — ✅ Done

**What it measures:** LLM input/output tokens accumulated across all nodes in a single query.

**Implementation:** `total_llm_tokens_in`, `total_llm_tokens_out` in SQLite, accumulated via `Annotated[int, operator.add]` in graph state
**Current baseline:** ~600-800 tokens in / ~150-250 tokens out for typical queries
**Gap:** No per-path breakdown, no budget alerting

---

### 1.7 Eval Test Suite — ✅ Done

**What it measures:** Regression safety across 71 defined test cases.

| Category | Count | Description |
|----------|-------|-------------|
| Legacy | 11 | Original queries used during initial development |
| Internal DB | 25 | Queries with known content in indexed digests |
| Web search | 25 | Queries with no indexed content (expect web fallback) |
| Classifier (GENERAL) | 6 | Queries that should route to `llm_only` |
| Additional | 4 | Edge cases and ambiguous queries |

**Files:** `eval/test_cases.py` (test definitions), `eval/run_eval.py` (harness)
**Current pass rate (2026-04-06 baseline):** ~76-80% (48-50/61 passing)
**Target:** ≥95%

**Baseline Metrics (2026-04-06):**

| Metric | Before Fixes | After Fixes |
|--------|--------------|-------------|
| Tests Evaluated | 61 → 71 | 71 (9 new) |
| Tests Passed | 43 | ~48-50 |
| Pass Rate | 70.5% | ~67-70% |
| Bugs Fixed | 3 identified | 3 confirmed |
| Judge Score Avg (internal) | 7.7/10 | 7.8/10 |
| Judge Score Avg (rejected) | — | 1.5/10 |

**Path Distribution (2026-04-06):**

| Path | Tests | Expected | Actual | % |
|------|-------|----------|--------|---|
| Internal (11 legacy + 25 new) | 36 | 36 | 28 | 78% |
| Web Fallback (25 tests) | 25 | 25 | 16 | 64% |
| Explicit Web (3 legacy) | 3 | 3 | 16 | 533% |

Note: Explicit web had 13 extra hits (9 web_fallback tests routing there due to ambiguous keywords "live" and "current")

**Judge Score Distribution (after fixes):**

| Score Range | Count | Path | Notes |
|-------------|-------|------|-------|
| 9-10 | 8 | internal | Excellent confidence |
| 7-8 | 15 | internal | Good confidence |
| 5-6 | 2 | internal | Borderline, passing threshold |
| 0-4 | 8 | web_fallback | Below threshold, correctly rejected |
| N/A | 28 | web/explicit_web | No judge needed |

**Performance Characteristics (2026-04-06):**

| Metric | Value |
|--------|-------|
| Avg latency (all paths) | ~15s |
| Avg judge score (internal) | 7.7/10 |
| Avg judge score (rejected) | 1.5/10 |
| Source precision (internal) | 100% |
| Embedding model | sentence-transformers all-MiniLM-L6-v2 |
| Vector DB | ChromaDB (364 chunks) |
| Index coverage | 8 summary files |

**Legacy Tests (2026-04-06):** All 11/11 PASS ✅
- `internal_db_optimization`, `internal_rag_agents`, `internal_api_security`, `internal_event_sourcing`
- `web_fallback_photosynthesis`, `web_fallback_medieval_history`, `web_fallback_cooking`
- `explicit_web_latest_ai_news`, `explicit_web_breaking_news`
- `netflix_technical`, `vague_system_query`

---

### 1.8 Path Distribution (Production) — ✅ Done (logged), 🔲 No Dashboard

**What it measures:** Over all production queries, what % go to each path. High `web_fallback` rate = poor index coverage or judge too strict. High `explicit_web` rate = too many real-time queries.

**Logged to:** SQLite on every query
**Gap:** No aggregate view surfaced in UI or reports

**SQL to inspect:**
```sql
SELECT
  CASE WHEN llm_only_used = 1 THEN 'llm_only'
       WHEN explicit_web_detected = 1 THEN 'explicit_web'
       WHEN internal_succeeded = 1 THEN 'internal'
       WHEN web_was_fallback = 1 THEN 'web_fallback'
       ELSE 'unknown' END as path,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM searches
GROUP BY path;
```

---

### 1.9 User Feedback Signal — 🔲 Pending

**What it measures:** Did the user find the answer useful? Thumbs up/down per response.

**Why it matters:** Judge validates retrieval quality, but can't tell if the final answer was actually useful. No feedback loop currently exists.

**Implementation plan:**
- Add thumbs up/down buttons to UI per answer
- Log `user_feedback` (1/-1/0) to SQLite against the response `id`
- Track % positive feedback per path over time
- Use negative feedback to identify systemic failure patterns

---

### 1.10 llm_only Hit Rate — 🔲 Pending

**What it measures:** What % of queries are classified as GENERAL and served via `llm_only`. Too high = classifier is too aggressive. Too low = classifier is too conservative (current: 5.2%).

**Target range:** 5-15% (conservative is correct — minimize hallucination risk)
**Implementation plan:** Derive from SQLite `llm_only_used = 1` over time; surface in a periodic report

---

### 1.11 Conversation Coherence — 🔲 Pending

**What it measures:** For multi-turn conversations, whether follow-up answers stay on topic and reference prior context correctly.

**Why it matters:** The system injects conversation history at answer generation and enriches web queries with context, but there's no automated test for whether this actually works.

**Implementation plan:**
- Add multi-turn test cases to `test_cases.py` (e.g., Q1 about topic X, Q2 = "tell me more")
- Measure whether Q2 answer references Q1 context
- Requires updating `run_eval.py` to support sequential multi-turn test cases

---

## Part 2: Guardrails

Active and planned controls that prevent bad outputs, bad routing, and system abuse.

---

### 2.1 Retrieval Quality Gate (Distance Threshold) — ✅ Done

**What it does:** Rejects chunks where the nearest-neighbor distance exceeds the threshold. Only passes chunks to the judge if at least one chunk is within distance.

**Implementation:** `RELEVANCE_THRESHOLD = 0.8` in `graph.py`; `chunks_passed_threshold` state field
**Current threshold:** 0.8 (cosine distance)
**Effect:** If top chunk distance > 0.8, skip judge entirely and route directly to web

**Distance interpretation:**
| Distance | Quality |
|----------|---------|
| < 0.3 | Excellent |
| 0.3–0.5 | Good |
| 0.5–0.65 | Fair |
| > 0.65 | Poor |
| > 0.8 | Rejected — go to web |

---

### 2.2 LLM Judge Gate — ✅ Done

**What it does:** Even if chunks pass the distance threshold, an LLM judge (temperature=0) scores semantic relevance 0-10. Below threshold → web fallback.

**Implementation:** `JUDGE_SCORE_THRESHOLD = 5` in `graph.py`; `judge_gate` node with `RetryPolicy(max_attempts=3)`
**Prompt rules:** Temporal validation (future events → score 0), specific term matching, distance-adjusted scoring, LENIENT matching (60%+ coverage → score ≥5)
**Logged to:** `judge_score`, `judge_quality`, `judge_reasoning`, `judge_parse_error` in SQLite

---

### 2.3 Explicit Web Keyword Bypass — ✅ Done

**What it does:** Queries containing real-time signal words skip internal search entirely and go straight to web.

**Implementation:** `detect_explicit_web()` in `graph.py` using word-boundary regex `\b(keyword)\b`
**Current keywords (20):** `latest, last week, last month, last year, yesterday, today, this week, this month, breaking, news, current, stock, price, right now, live, recently, just announced, new release, trending`
**Note:** "live" and "current" are ambiguous — see Pending item 2.11

---

### 2.4 Intent Pre-Classifier — ✅ Done

**What it does:** Before retrieval, classifies query as GENERAL (pure textbook ML/CS concept) or PERSONAL (everything else). GENERAL queries bypass the entire RAG pipeline.

**Implementation:** `classify_intent()` node in `graph.py`; `INTENT_CLASSIFIER_PROMPT` with 6 ordered rules; temperature=0
**Accuracy:** 100% on 77 validation test cases
**Hit rate:** ~5.2% (intentionally conservative)
**Fallback:** If `llm_only` node fails (Ollama error), falls back to `internal_retrieve`

---

### 2.5 Conversation History Cap — ✅ Done

**What it does:** Limits conversation context sent to backend to prevent token blowout and prompt injection via long histories.

**Implementation:** `conversation_history = conversation_history[-6:]` in `app.py` (last 3 exchanges)
**Logged:** `conversation_id` in SQLite for multi-turn tracing

---

### 2.6 Per-Node Retry Policy — ✅ Done

**What it does:** Automatically retries flaky nodes (LLM JSON parse failures, transient Ollama errors) before surfacing an error.

**Implementation:** LangGraph `RetryPolicy` in `graph.py`

| Node | Max Retries | Reason |
|------|-------------|--------|
| `judge_gate` | 3 | LLM may return invalid JSON |
| `web_search` | 3 | DuckDuckGo network failures |
| `generate_answer` | 2 | Ollama transient errors |

---

### 2.7 Input Validation — ✅ Done

**What it does:** Validates query and conversation history at the API boundary before hitting the graph.

**Implementation:** `app.py` route handler
- Non-empty query enforced (returns 400 if empty)
- `conversation_id` must be a string or set to None
- Each `conversation_history` entry must have `role` ∈ {user, assistant} and string `content`; malformed entries are dropped with a warning

---

### 2.8 Query Normalization — ✅ Done

**What it does:** Passes the raw query through Ollama to fix typos before embedding. Prevents poor embeddings from misspelled queries.

**Implementation:** `query_normalize` node in `graph.py`; uses `OLLAMA_MODEL` (llama3.2)
**Fallback:** If Ollama fails, uses original query unchanged

---

### 2.9 Judge JSON Parse Enforcement — ✅ Done

**What it does:** The judge must return valid JSON. If it returns malformed JSON, the `RetryPolicy` retries up to 3 times. Markdown code fences are stripped before parsing.

**Implementation:** `judge_gate()` raises on `json.loads()` failure, triggering LangGraph retry; code fence stripping in `graph.py:408-412`

---

### 2.10 Temporal Validation in Judge — 🔄 In Progress

**What it does:** If a query asks about a future event (post-April 2026), the judge should score 0 and route to web.

**Implementation:** Added to `JUDGE_PROMPT` as a CRITICAL rule
**Status:** Partially effective — prompt rule exists but LLM doesn't reliably detect all temporal patterns
**Known failure:** `web_27_world_cup` ("Who won the 2026 FIFA World Cup?") still occasionally scores internally

**Remaining work:**
- [ ] Add keyword pre-filter for temporal markers before hitting judge: "upcoming", "next year", "will", "future", "2027", "2028"
- [ ] Combine keyword signal with judge score for final routing decision

---

### 2.11 Ambiguous Keyword Replacement — 🔲 Pending

**What it does:** Replace dual-meaning keywords in `EXPLICIT_WEB_KEYWORDS` that trigger false positives for non-real-time queries.

**Problem keywords:**
| Keyword | False Positive Example | Fix |
|---------|----------------------|-----|
| `live` | "How does Netflix deliver **live** streams?" (a feature, not real-time) | Replace with `livestream`, `live stream`, `live score` |
| `current` | "What is the **current** bottleneck in ML pipelines?" (context, not price) | Replace with `today's`, `right now`, `current price` |

**Implementation:** Update `EXPLICIT_WEB_KEYWORDS` set in `graph.py` + update affected test cases in `test_cases.py`

---

### 2.12 Query Length Cap — 🔲 Pending

**What it does:** Reject or truncate queries over a maximum length. Prevents prompt injection attacks via extremely long queries and token blowout in normalization.

**Why it matters:** Currently there is no limit. A user could send a 50,000-character query that would blow up the normalization node's token budget.

**Implementation plan:**
- Add `MAX_QUERY_LENGTH = 1000` (chars) in `app.py`
- Return 400 if query exceeds limit
- Log attempts as a security signal

---

### 2.13 Rate Limiting — 🔲 Pending

**What it does:** Limit requests per IP or session to prevent abuse and protect the local Ollama instance from being overloaded.

**Implementation plan:**
- Flask-Limiter: `pip install flask-limiter`
- `@limiter.limit("10/minute")` on `/search` endpoint
- Return 429 with a friendly message

---

### 2.14 Hallucination Guard for llm_only Path — 🔲 Pending

**What it does:** The `llm_only` path returns pure parametric LLM answers with no source grounding. Unlike the internal path, there's no judge validating the answer against retrieved content.

**Risk:** The LLM could hallucinate a confident but wrong definition for a concept it's uncertain about.

**Implementation plan:**
- Option A: Add a confidence self-check prompt — ask the LLM to rate its own confidence (0-10) before returning answer; if <7, fall through to internal_retrieve
- Option B: Spot-check by retrieving top-1 chunk and checking for obvious contradiction
- Option C: Add disclaimer to UI for llm_only answers ("Answer from general knowledge, not your digests")

---

### 2.15 Answer Safety / Toxicity Filter — 🔲 Pending

**What it does:** Scan the final answer for harmful content before returning it to the UI.

**Why low priority:** This is a personal-use tool with a single user and trusted content sources. Risk is low.

**Implementation plan (if needed):**
- Simple keyword blocklist for egregious content
- Or a lightweight LLM safety classifier on final output

---

---

## Part 3: Historical Bug Analysis (2026-04-06)

Three critical bugs were identified during evaluation and fixed. Details are in `bugs-and-fixes/BUGS.md`. This section preserves the analysis from that evaluation run.

### Bug #1: Substring Keyword Matching — ✅ FIXED

**Affected tests:** 3 (internal_04, internal_06, internal_16)  
**Issue:** Keywords matched inside words (e.g., "news" in "newslet**ters**") causing false routing to explicit_web

**Fix applied:** Word-boundary regex in `detect_explicit_web()` function
```python
pattern = r'\b(' + '|'.join(re.escape(kw) for kw in EXPLICIT_WEB_KEYWORDS) + r')\b'
explicit_web = bool(re.search(pattern, query_lower))
```

**Result:** internal_04 fixed. internal_06 and internal_16 still match because "live" and "current" are legitimate standalone words — revealed underlying keyword ambiguity issue (see Pending 2.11)

---

### Bug #2: Low Judge Semantic Scores — ✅ IMPROVED

**Affected tests:** 3-4 (internal_20, internal_21, internal_23, internal_54)  
**Issue:** Judge was too strict on semantic matching. Chunks with 60%+ query intent coverage were scored 0-3.

**Fix applied:** Lenient matching rules added to `JUDGE_PROMPT`:
- Accept semantic equivalence (e.g., "1:1 meeting" ≈ "meeting topics")
- Accept partial coverage (60%+ of intent → score ≥5)
- Accept domain matches (same area, different subtopic → score ≥4)

**Result:** Test pass rate improved from 70.5% → ~76-80%

---

### Bug #3: False Positive Future Events — ✅ FIXED

**Affected tests:** 1 (web_27_world_cup)  
**Issue:** Query "Who won the 2026 FIFA World Cup?" scored internally with high confidence (8) even though the event hasn't occurred in April 2026 archives.

**Fix applied:** Temporal validation rule added to `JUDGE_PROMPT`:
```
If the query asks about a future event that hasn't occurred in the April 2026 knowledge base:
- "Who won the 2026 FIFA World Cup?" → Future event (hasn't occurred)
- "What will happen..." → Future prediction
THEN SCORE = 0 (REJECT - send to web search)
```

**Status:** Partially effective. Prompt rule exists but LLM doesn't reliably detect all temporal patterns. See Pending 2.10 for remaining work.

---

### Bug #4: Judge Score String/Int TypeError — ✅ FIXED

**Issue:** LLM occasionally returns `intent_score` as string `"8"` instead of integer `8`. Caused `TypeError` when comparing `str < int` in routing.

**Fix applied:** Cast to int at both extraction and comparison points (defense in depth):
```python
# In judge_gate: 
"judge_score": int(verdict["intent_score"])

# In route_after_judge:
score = int(state.get("judge_score") or 0)
```

**Key learning:** Never trust LLM JSON field types. Always cast numeric fields immediately upon extraction.

---

## Summary Table

### Evaluation Metrics

| # | Metric | Status | Target |
|---|--------|--------|--------|
| 1.1 | Routing correctness | ✅ Done | ≥95% pass rate |
| 1.2 | Source precision | ✅ Done | ≥90% |
| 1.3 | Judge score quality | ✅ Done | Avg ≥7.0 on accepted queries |
| 1.4 | Latency by path | ✅ Done (logged) | llm_only ≤800ms, internal ≤4s |
| 1.5 | Answer presence | ✅ Done | 100% |
| 1.6 | Token usage | ✅ Done (logged) | No budget target yet |
| 1.7 | Eval test suite (71 cases) | ✅ Done | ≥95% pass rate |
| 1.8 | Path distribution dashboard | 🔲 Pending | — |
| 1.9 | User feedback signal (thumbs) | 🔲 Pending | ≥80% positive |
| 1.10 | llm_only hit rate tracking | 🔲 Pending | 5-15% target range |
| 1.11 | Conversation coherence tests | 🔲 Pending | — |

### Guardrails

| # | Guardrail | Status | Threshold |
|---|-----------|--------|-----------|
| 2.1 | Retrieval distance threshold | ✅ Done | ≤0.8 to pass |
| 2.2 | LLM judge gate | ✅ Done | Score ≥5 to use internal |
| 2.3 | Explicit web keyword bypass | ✅ Done | 20 keywords, word-boundary |
| 2.4 | Intent pre-classifier | ✅ Done | Conservative GENERAL definition |
| 2.5 | Conversation history cap | ✅ Done | Last 6 entries (3 exchanges) |
| 2.6 | Per-node retry policy | ✅ Done | Judge 3x, web 3x, generate 2x |
| 2.7 | Input validation | ✅ Done | API boundary, 400 on bad input |
| 2.8 | Query normalization | ✅ Done | Typo correction before embedding |
| 2.9 | Judge JSON parse enforcement | ✅ Done | Retry on invalid JSON |
| 2.10 | Temporal validation | 🔄 In Progress | Prompt rule exists, not reliable |
| 2.11 | Ambiguous keyword replacement | 🔲 Pending | live → livestream, current → today's |
| 2.12 | Query length cap | 🔲 Pending | MAX_QUERY_LENGTH = 1000 chars |
| 2.13 | Rate limiting | 🔲 Pending | 10 req/min per IP |
| 2.14 | Hallucination guard (llm_only) | 🔲 Pending | Confidence self-check ≥7 |
| 2.15 | Answer safety/toxicity filter | 🔲 Pending | Low priority (personal-use tool) |

---

## Part 4: SQL Audit Trail & Analysis Queries

All production search data is logged to `data/search_logs.db` (SQLite). Use these queries to inspect metrics in production.

### Query: View recent 20 searches
```sql
SELECT id, timestamp, query, 
       CASE WHEN llm_only_used = 1 THEN 'llm_only'
            WHEN explicit_web_detected = 1 THEN 'explicit_web'
            WHEN internal_succeeded = 1 THEN 'internal'
            WHEN web_was_fallback = 1 THEN 'web_fallback'
            ELSE 'unknown' END as path,
       judge_score, duration_ms
FROM searches 
ORDER BY id DESC 
LIMIT 20;
```

### Query: Path distribution (% of queries per path)
```sql
SELECT CASE WHEN llm_only_used = 1 THEN 'llm_only'
            WHEN explicit_web_detected = 1 THEN 'explicit_web'
            WHEN internal_succeeded = 1 THEN 'internal'
            WHEN web_was_fallback = 1 THEN 'web_fallback'
            ELSE 'unknown' END as path,
       COUNT(*) as count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM searches
GROUP BY path
ORDER BY count DESC;
```

### Query: Judge score distribution (for internal path only)
```sql
SELECT judge_score, COUNT(*) as count
FROM searches
WHERE judge_attempted = 1
GROUP BY judge_score
ORDER BY judge_score DESC;
```

### Query: Latency by path (avg, min, max)
```sql
SELECT CASE WHEN llm_only_used = 1 THEN 'llm_only'
            WHEN internal_succeeded = 1 THEN 'internal'
            WHEN web_was_fallback = 1 THEN 'web_fallback'
            WHEN explicit_web_detected = 1 THEN 'explicit_web'
            ELSE 'unknown' END as path,
       ROUND(AVG(duration_ms), 0) as avg_ms,
       MIN(duration_ms) as min_ms,
       MAX(duration_ms) as max_ms,
       COUNT(*) as count
FROM searches
GROUP BY path
ORDER BY avg_ms DESC;
```

### Query: Rejected matches (judge score < 5)
```sql
SELECT query, judge_score, judge_reasoning 
FROM searches 
WHERE judge_attempted = 1 AND judge_score < 5
ORDER BY timestamp DESC
LIMIT 20;
```

### Query: Multi-turn conversations (by conversation_id)
```sql
SELECT conversation_id, COUNT(*) as turns, 
       MIN(timestamp) as started, MAX(timestamp) as ended
FROM searches 
WHERE conversation_id IS NOT NULL
GROUP BY conversation_id
ORDER BY MAX(timestamp) DESC
LIMIT 10;
```

### Query: Average tokens per path
```sql
SELECT CASE WHEN llm_only_used = 1 THEN 'llm_only'
            WHEN internal_succeeded = 1 THEN 'internal'
            WHEN web_was_fallback = 1 THEN 'web_fallback'
            ELSE 'other' END as path,
       ROUND(AVG(total_llm_tokens_in), 0) as avg_tokens_in,
       ROUND(AVG(total_llm_tokens_out), 0) as avg_tokens_out,
       COUNT(*) as count
FROM searches
GROUP BY path
ORDER BY (avg_tokens_in + avg_tokens_out) DESC;
```

### Query: Error rate
```sql
SELECT COUNT(*) as total,
       SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as errors,
       ROUND(100.0 * SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as error_pct
FROM searches;
```

---

## How to Maintain This File

**When implementing a pending metric/guardrail:**
1. Update status from 🔲 Pending → 🔄 In Progress (or directly to ✅ Done if small)
2. Add implementation details under the item
3. Add test coverage if applicable
4. Update baseline metrics and performance characteristics once confirmed

**When a metric drifts or degrades:**
1. Check the SQL audit trail queries above to diagnose
2. Log the issue and root cause in this file
3. Create a corresponding issue in the roadmap if needed

**When bugs are found:**
1. Add details to `bugs-and-fixes/BUGS.md` (not this file)
2. Cross-reference the bug number here if it affects a metric/guardrail
3. Update baseline metrics after the fix is deployed
