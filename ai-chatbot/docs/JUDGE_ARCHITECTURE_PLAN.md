<!-- Created: 2026-04-19 | Updated: 2026-04-19 -->

# Judge Architecture: Expansion Plan

## Context

The current pipeline has one judge: `judge_gate` in `graph.py`. It runs after internal ChromaDB retrieval and before answer generation, scoring chunk relevance 0-10. Score ≥ 5 proceeds to `generate_answer`; score < 5 falls back to web search.

This is a **pre-generation retrieval judge only**. Research (TruLens RAG Triad, RAGAS, CRAG) shows a single retrieval judge is necessary but not sufficient — it cannot catch:

1. **Post-generation hallucination** — the LLM synthesizing claims not grounded in retrieved chunks
2. **Web result contamination** — raw DuckDuckGo results being fed to the LLM without relevance filtering

The existing `hallucination_risk` flag in `web_search` is computed but **never gates output** — it logs but doesn't act. This is a data flow bug.

---

## Current Pipeline Blind Spots

| Node | Gap | Impact |
|---|---|---|
| `generate_answer` | No post-generation faithfulness check | LLM can hallucinate beyond retrieved chunks |
| `web_search` | `hallucination_risk` not wired to output gate; raw results unfiltered | ~9.4x higher hallucination rate from web sources (vs. internal KB) |
| `llm_only` | Zero validation on parametric answer | Outdated/wrong answers pass through silently |

---

## What NOT to Add

- **`query_normalize` judge** — Normalization drift is a minor risk; no evidence it breaks queries meaningfully in practice
- **`classify_intent` confidence scoring** — Currently 100% accuracy on 77 test cases with a conservative PERSONAL default; not broken
- **A full RAGAS suite** — 5-metric RAGAS evaluation is appropriate for offline batch analysis, not inline per-request judging at this scale

---

## Recommended Judges (Prioritized)

### Priority 1 — Faithfulness Judge (after `generate_answer`)

**Why this first:**
The internal path is the *primary success path* — queries that clear the judge gate and get a generated answer. There is currently no check that the generated answer stays within the bounds of what the chunks actually said. This is the most impactful gap on the most common path.

**What it does:**
- Runs after `generate_answer`, before serving the response
- Decomposes the generated answer into atomic claims
- Verifies each claim is grounded in the retrieved chunks
- Produces a faithfulness score: `(grounded claims) / (total claims)`, 0-10
- If score < 7: do not serve the unfaithful internal answer → route to `web_search` as fallback
- If Ollama fails: log and serve the answer anyway (fail open, don't block the user)

**Latency consideration (from Full-Stack Lead):**
This judge adds latency to the critical path of every successful internal query. Mitigate by:
- Using a tight, focused prompt — no rubric, just binary claim-by-claim matching
- Setting a strict timeout (e.g. 3s); fail open if exceeded
- Tracking `faithfulness_latency_ms` separately to monitor impact

**Implementation notes (from AI Engineer):**
- Follow existing judge pattern: temperature=0, RetryPolicy(max_attempts=3), JSON output
- Add `faithfulness_score` and `faithfulness_judge_skipped` to SearchState
- Log both to SQLite — enables correlation analysis between judge_score and faithfulness_score
- Prompt should be version-controlled as a named constant in `graph.py` alongside `JUDGE_PROMPT`

**Files to modify:**
- `graph.py` — add `faithfulness_judge` node and `route_after_faithfulness` edge function
- `logger.py` — add `faithfulness_score INTEGER`, `faithfulness_judge_skipped INTEGER` columns
- `eval/test_cases.py` — add 3-5 test cases where a hallucinated answer should be caught
- `eval/run_eval.py` — add `faithfulness_score` to output table and pass/fail logic

---

### Priority 2 — Web Search Relevance Judge (inside `web_search` node)

**Why this second:**
Web sources have a ~9.4x higher hallucination rate than internal KB sources (published research on cancer chatbots; confirmed by CRAG architecture findings). The existing `hallucination_risk` flag is computed but never gates output — fixing this is a one-line bug fix that should happen regardless of the judge work. The per-result relevance judge then improves the quality of what gets fed to the LLM.

**What it does (two parts):**

*Part A — Fix the existing bug (do immediately):*
Wire `hallucination_risk = True` to block serving the answer. When `hallucination_risk` is set, return a "I couldn't find reliable results for this" response instead of the potentially hallucinated answer.

*Part B — Per-result relevance filter (new judge):*
- Before feeding DuckDuckGo results to the answer LLM, score each result
- Input: (query, result title + body snippet)
- Judge: binary RELEVANT / IRRELEVANT at temperature=0
- Only pass RELEVANT results to the answer LLM
- If 0 results pass: set `web_no_content = True`
- Use a cheap, fast model for this — it's a binary call, not a scoring rubric

**Implementation notes (from AI Engineer):**
- The binary judge is intentionally simpler than `judge_gate` — no score, no rubric, just RELEVANT/IRRELEVANT
- Reduces token waste: irrelevant snippets won't pad the answer generation prompt
- Track `web_results_total` vs `web_results_filtered` in state for observability
- Log both to SQLite

**Files to modify:**
- `web_search.py` — add `score_web_result(query, result)` function using Ollama
- `graph.py` — update `web_search` node to call relevance filter; wire `hallucination_risk` to gate output
- `logger.py` — add `web_results_total INTEGER`, `web_results_filtered INTEGER` columns
- `eval/test_cases.py` — add test for a web query where noisy results should be filtered

---

### Priority 3 — LLM-Only Answer Quality Judge (after `llm_only`) — Deferred

**Why defer:**
Only ~5% of traffic hits the `llm_only` path. The GENERAL definition is deliberately narrow (textbook ML/CS concepts only), and `llama3.2` has strong parametric accuracy on these. The ROI of a third inline judge for 5% of traffic is low relative to the added latency and complexity.

**Revisit when:**
- GENERAL traffic grows above 10% of total queries
- User feedback identifies specific hallucinations on the llm_only path
- A lightweight answer relevance check can be added with < 200ms overhead

---

## Success Metrics (PM Lens)

Before shipping each judge, define the baseline and target:

| Metric | Baseline (current) | Target after implementation |
|---|---|---|
| Avg faithfulness score (internal path) | Unmeasured | Track; alert if avg < 7.0 |
| Web hallucination_risk blocks per day | 0 (flag computed, never blocks) | Measure; reduce unfaithful web answers served |
| Web results filtered per query | 0 (all passed through) | Track avg; expect 1-2 filtered per query on noisy topics |
| 61-test eval pass rate | Baseline before starting | Must not regress after each judge is added |

---

## Engineering Sequencing (Full-Stack Lead Lens)

**Step 1 (1 hour):** Fix `hallucination_risk` wiring in `graph.py` — make it gate output. This is a bug fix with no new node, no new prompt, no latency impact. Ship it independently.

**Step 2 (half day):** Faithfulness judge — new node, new prompt, new state fields, new logger columns, new eval test cases.

**Step 3 (half day):** Web relevance filter in `web_search.py` + per-result scoring.

**Step 4:** Run full 61-test eval harness after each step. Zero regressions required before proceeding to next step.

---

## Verification

```bash
# After each step, run the full eval harness
cd ai-chatbot
python3 eval/run_eval.py

# Check new judge scores in SQLite
sqlite3 data/search_logs.db "SELECT path, judge_score, faithfulness_score, hallucination_risk, web_results_total, web_results_filtered FROM search_logs ORDER BY id DESC LIMIT 20;"

# Confirm hallucination_risk=1 rows no longer reach final_output
sqlite3 data/search_logs.db "SELECT id, query, final_output FROM search_logs WHERE hallucination_risk=1 ORDER BY id DESC LIMIT 5;"
```

---

## Reviewer Notes

**From AI Engineer perspective:**
- All new judges must use temperature=0 and RetryPolicy(max_attempts=3) — same pattern as existing `judge_gate`
- New prompts should be named constants in `graph.py`, not inline strings
- New state fields must be added to `make_initial_state()` in both `app.py` and `search.py` — they share initial state construction
- Add per-judge latency fields to state for observability

**From Full-Stack Lead perspective:**
- Don't add all three judges at once. Ship each independently with a passing eval harness between steps
- The faithfulness judge adds latency to every successful query — set a timeout and fail open
- `hallucination_risk` wiring is a pre-existing bug that should ship immediately, decoupled from the judge work

**From PM perspective:**
- Priority 2 Part A (hallucination_risk bug fix) is the smallest valuable step — ship it today
- Faithfulness judge has the broadest impact (covers majority traffic on internal path)
- LLM-only judge is low ROI at current traffic levels — don't build it until there's evidence of a problem
- Define success metrics before building, not after
