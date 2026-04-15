# Learning Document: Production Feedback Quality Fixes

**Date:** 2026-04-12  
**Context:** User thumbs-down feedback on id 30 and 33 triggered a deep investigation into web fallback quality  
**Status:** All 4 fixes shipped and validated  
**Trigger:** First real production feedback signals — 2 thumbs-down, both on web_fallback path

---

## Executive Summary

Two thumbs-down feedback entries (id 30, id 33) revealed four systemic quality gaps in the web fallback pipeline. Analysis showed the judge was accepting wrong answers (high confidence on off-topic results), the web fallback had no quality gate, hallucinated answers had no warning signal, and there was no aggregate view of feedback patterns.

**Key finding:** A high judge score (8/10, "good") on the internal path does NOT mean the final answer will be good. When the system falls back to web, the judge score is irrelevant — a completely new failure mode begins.

**Results after fixes:**
- ✅ Judge now rejects off-topic person+topic compound queries
- ✅ Web non-answers detected and excluded from final output
- ✅ Hallucination risk badge shows users when to be skeptical
- ✅ Feedback dashboard surfaces patterns automatically

---

## The Diagnosis Process

### Step 1: Read the Production Signals
Both thumbs-down entries had identical symptoms:
- `judge_score = 8`, `judge_quality = "good"` (internal path)
- `internal_succeeded = 0` (judge accepted but answer generation said "no content")
- `web_was_fallback = 1` (fell through to web)
- `web_succeeded = 1` (web marked as succeeded — incorrectly)
- Answer was either verbose non-answer or hallucinated facts

**Key insight:** `judge_score = 8` on a web_fallback query means the judge scored the *internal retrieval attempt* well, but the final answer came from web — with no quality gate at all.

### Step 2: Check What Content Was Actually Retrieved
```python
# Query the index to see what chunks were retrieved for id 33
# "what does chamath say about scaling fast organizations?"
# → 16 Chamath chunks found, but ALL about equity yields/AGI — wrong topic
```

**Key insight:** The index HAD Chamath content. The judge scored it 8 because Chamath's name appeared in chunks. But the topic (scaling organizations) didn't match. The judge was doing person-level matching, not person+topic matching.

### Step 3: Map Each Failure to Root Cause

| ID | Query | Judge Score | Actual Problem |
|----|-------|-------------|----------------|
| 33 | Chamath + scaling orgs | 8 | Chunks about Chamath + equity (wrong topic) |
| 30 | what is mythos by anthropic? | 8 | No content exists; web hallucinated "Claude Mythos escaped sandbox" |
| 35 | what is mythos by anthropic? | 8 | web_result_count=1; web gave non-answer; still returned as `web_succeeded=True` |
| 36 | what is mythos by anthropic? | 8 | After fix: `web_no_content_response=1`, `web_succeeded=0` ✅ |

---

## Fix #1: Compound Query Matching in Judge Prompt

### Root Cause
The judge's "CORE TOPIC MATCHING" rule required main entities to appear in chunks. For "what does Chamath say about scaling orgs?", finding any Chamath chunk satisfied "main entity present" — even if the chunk discussed equity yields.

### The Fix
Added a new section to JUDGE_PROMPT requiring BOTH parts to match:

```
COMPOUND QUERY MATCHING (person + topic):
- If query contains PERSON + TOPIC, chunk MUST address BOTH
- Person's name alone is NOT sufficient
- Example: "Chamath + equity yields" ≠ "Chamath + scaling orgs" → Score ≤3 (REJECT)
```

### Key Learning
**Semantic similarity ≠ relevance for compound queries.** Embedding similarity is computed on the full query vector, so a chunk about "Chamath equity" will be semantically close to "Chamath scaling" because both share the person embedding. The judge must enforce topic-level relevance, not just entity-level.

---

## Fix #2: Web Fallback Non-Answer Detection

### Root Cause
`generate_web_answer()` set `web_succeeded = bool(answer)`. Any non-empty string — even a verbose "I couldn't find information" — was marked as success and returned to the user.

The WEB_SYSTEM_PROMPT already told Ollama to say a specific phrase when it couldn't answer:
> "If the results do not contain enough information to answer the question, say: 'The search results don't contain enough information...'"

But nothing downstream checked for that phrase.

### The Fix
Added phrase detection and two consequences:

```python
WEB_NO_CONTENT_PHRASES = [
    "search results don't contain enough information",
    "results don't contain enough",
    "couldn't find enough information", ...
]
web_no_content = any(phrase in answer.lower() for phrase in WEB_NO_CONTENT_PHRASES)

web_succeeded_flag = bool(answer) and not web_no_content
final_output = None if web_no_content else (answer or None)  # Don't return non-answers
```

### Key Learning
**Never trust `bool(answer)` as a quality gate.** A string is truthy if it has characters — it says nothing about whether it answers the question. The prescribed non-answer phrase is a reliable signal: if Ollama follows the system prompt, we can detect when it couldn't answer.

Also: **the system prompt is a contract.** If you tell the LLM to use a specific phrase when it has no answer, check for that phrase downstream and act on it.

---

## Fix #3: Hallucination Risk Flag

### Root Cause
Web search for non-existent topics (e.g., "Anthropic Mythos") could find 1 loosely related result, and Ollama would confidently extrapolate — generating false facts like "Claude Mythos escaped sandbox and hacked the internet."

There was no way for the user to know an answer was risky.

### The Fix
Three signals combined into a single `hallucination_risk` flag:

1. **Non-answer detected** (`web_no_content_response = True`) — Ollama admitted it couldn't answer
2. **Thin evidence base** (`web_result_count < 2`) — fewer than 2 results is unreliable
3. **Ungrounded proper nouns** — extract capitalized words from query, check if they appear in result titles/bodies

```python
# In web_search.py — check groundedness before returning
query_words = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', query)
stopwords = {"What", "How", "Why", "Who", ...}
proper_nouns = [w for w in query_words if w not in stopwords]
result_text = " ".join(r.get('title','') + r.get('body','') for r in results)
grounded = all(pn in result_text for pn in proper_nouns) if proper_nouns else True
```

UI response: yellow ⚠️ warning banner — "This answer may contain unverified claims. Check sources carefully."

### Key Learning
**Groundedness checking doesn't require an LLM.** Simple string matching — "does the proper noun in the query appear anywhere in the source bodies?" — catches the most dangerous hallucination case (confident claims about non-existent things). The proper noun is the product name, person, or concept being asked about. If results don't mention it by name, the answer is almost certainly fabricated.

**Defense-in-depth:** Three independent signals (non-answer phrase, result count, proper noun check) mean any ONE of them can catch a risky answer even if the others miss it.

---

## Fix #4: Feedback Dashboard

### Root Cause
Feedback was logged to SQLite but invisible. The only way to see patterns was to run manual SQL queries. Two thumbs-down entries sat in the database unnoticed until manually investigated.

### The Fix
- Added `path TEXT` column to DB (computed from `_classify_path()` and stored at log time)
- New `/api/feedback-stats` endpoint returning:
  - Overall: total queries, thumbs up/down counts, % positive
  - Failures by pipeline path
  - Judge score distribution on negative feedback
  - Recent 20 feedback entries (both 👍 and 👎, color-coded)
- New `/dashboard` route + `templates/dashboard.html`
- Dashboard link in main chat header

### Key Learning
**Log `path` at write time, not compute time.** The pipeline path (`internal`, `web_fallback`, `llm_only`, `explicit_web`) was previously computed only at response-build time from boolean flags. For dashboards, you need it stored as a single readable string in the DB — computing it from 4 booleans in SQL produces messy CASE statements. Write it to the DB at log time.

**Show both positive and negative feedback.** The initial dashboard only showed thumbs-down. But thumbs-up entries are equally important — they validate that certain paths ARE working, and help establish what a passing answer looks like.

---

## Architectural Insights

### The Web Fallback is a Separate System With Separate Failure Modes

The pipeline has two fundamentally different answer paths:

| Path | Quality Gate | Failure Mode |
|------|-------------|--------------|
| Internal | Judge (LLM, score 0-10) | Wrong topic, poor retrieval |
| Web Fallback | **None (before today)** | Non-answers, hallucination |

The judge score only guards the internal path. Once a query falls through to web, the judge score is irrelevant. Any quality guarantee from the judge is gone. This is the core insight from today's session.

**Implication:** Web fallback needs its OWN quality gate stack, not just a wrapper around `bool(answer)`. We now have:
1. Non-answer phrase detection (`web_no_content_response`)
2. Evidence count check (`result_count < 2`)
3. Groundedness check (proper nouns in results)

### High Judge Score + Web Fallback = Risky Pattern

A `judge_score = 8` on a `web_fallback` query is a yellow flag, not a green one. It means:
- Internal retrieval was *attempted* and found something semantically relevant
- But the final answer didn't come from those chunks — it came from web
- The high judge score is now misleading metadata

**Future improvement to consider:** Flag queries where `judge_score >= 7` AND `web_was_fallback = True` as a specific anomaly class — these are cases where the system had "confident wrong content" and fell through anyway.

### Feedback Loop Architecture

The feedback signal (thumbs up/down) is only valuable if it's:
1. **Persisted** — done (SQLite `feedback` column)
2. **Visible** — done (dashboard)
3. **Actionable** — partially done (can identify patterns, but no automated retraining or alert)

Next step would be automated alerting when % positive drops below 80% (already identified in METRICS_AND_GUARDRAILS.md as pending).

---

## What Broke First Under Real Usage

Running eval tests (71 test cases) found routing bugs. Real user feedback found quality bugs. The distinction matters:

| Signal | What It Catches |
|--------|----------------|
| Eval test suite | Routing correctness, known edge cases |
| User feedback | Answer quality, unexpected query types, hallucination |

**Neither replaces the other.** Eval tests told us the system routes correctly. User feedback told us it routes to wrong answers. You need both.

---

## Code Changes Summary

| File | Changes |
|------|---------|
| `graph.py` | JUDGE_PROMPT compound query rule; `web_no_content_response` + `hallucination_risk` in SearchState + generate_web_answer; initial_state defaults |
| `web_search.py` | Proper noun extraction + groundedness check; returns 5-tuple now |
| `logger.py` | 3 new DB columns (`web_no_content_response`, `hallucination_risk`, `path`); migrations; INSERT_SQL + save_log updated |
| `app.py` | Log dict + response JSON extended; `/api/feedback-stats` and `/dashboard` endpoints |
| `templates/index.html` | Hallucination warning CSS + JS badge; dashboard link in header |
| `templates/dashboard.html` | New file — full feedback dashboard with stats cards, tables, auto-refresh |

**Total columns in `searches` table:** 33 (was 29)
