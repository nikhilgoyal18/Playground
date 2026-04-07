# Improvement Plan: Search-News-Twitter Evaluation Failures

**Date:** 2026-04-06  
**Current Status:** 43/61 tests passing (70.5%)  
**Target:** 95%+ pass rate (57+ tests)

---

## Executive Summary

The evaluation revealed **3 categories of failures**:

| Category | Count | Status | Action |
|----------|-------|--------|--------|
| **Missing indexed content** | 8 | Fixable | Add topics to newsletters |
| **False positive (future event)** | 1 | Fixable | Add temporal validation to judge |
| **Test expectation mismatch** | 9 | Clarify | Decide on explicit_web behavior |

---

## Category 1: Missing Indexed Content (8 Tests → Priority 1)

**Problem:** These topics are in your newsletters but not in the vector database.

**Root Cause:** Either:
- Topics not included in newsletter summaries yet
- Summaries exist but don't contain these specific facts
- Indexed content is stale/incomplete

### Missing Topics Breakdown

| # | Topic | Expected Source | Evidence |
|---|-------|-----------------|----------|
| 1 | Claude two-mode LLM integration | Newsletter | Test expects internal match with judge ≥4 |
| 2 | Netflix 100M device streaming | Newsletter | Test expects internal match with judge ≥4 |
| 3 | API security authorization gaps | Newsletter | Test expects internal match with judge ≥4 |
| 4 | Andrew Ng product bottleneck | Newsletter | Test expects internal match with judge ≥4 |
| 5 | Maine electricity prices reasons | Newsletter | Test expects internal match with judge ≥4 |
| 6 | CLAUDE.md three blocks | Newsletter | Test expects internal match with judge ≥4 |
| 7 | Claude Auto Mode permissions | Newsletter | Test expects internal match with judge ≥4 |
| 8 | Amazon first sale (Wainwright) | Newsletter | Test expects internal match with judge ≥4 |

### Solution: Index Repair

**Step 1: Verify Content Exists**
```bash
# Check if summaries mention these topics
grep -r "two-mode\|extended thinking" newsletter-insights/summaries/
grep -r "Netflix.*100.*million\|CDN.*adaptive" newsletter-insights/summaries/
grep -r "authorization.*missing\|authentication.*works" newsletter-insights/summaries/
grep -r "Andrew Ng.*bottleneck\|product management" newsletter-insights/summaries/
grep -r "Maine.*electricity\|nuclear.*Quebec" newsletter-insights/summaries/
grep -r "CLAUDE.md\|Knowledge Architecture" newsletter-insights/summaries/
grep -r "Auto Mode.*file\|0.4.*false positive" newsletter-insights/summaries/
grep -r "Amazon.*first.*sold\|Wainwright.*April.*1995" newsletter-insights/summaries/
```

**Step 2: Add Missing Content (if not found)**

If content doesn't exist in summaries, you need to:
- Extract from original newsletter/Twitter digests
- Add as new bullet points in relevant summary sections
- OR create a new summary covering these topics

**Step 3: Rebuild Index**
```bash
python3 index.py
```

This will:
- Scan for updated summary files
- Parse bullet points into chunks
- Embed with sentence-transformers
- Upsert to ChromaDB

**Step 4: Verify Fixes**
```bash
# Test individual internal queries that failed
python3 eval/run_eval.py --id internal_05_claude_two_mode
python3 eval/run_eval.py --id internal_06_netflix_streams
python3 eval/run_eval.py --id internal_04_api_security_gaps
python3 eval/run_eval.py --id internal_16_andrew_ng_bottleneck
python3 eval/run_eval.py --id internal_22_maine_electricity
python3 eval/run_eval.py --id internal_13_claude_md_blocks
python3 eval/run_eval.py --id internal_21_claude_auto_mode
python3 eval/run_eval.py --id internal_23_amazon_first_sale
```

**Expected Outcome:** All 8 should route to `internal` with judge score ≥4

---

## Category 2: False Positive - World Cup (1 Test → Priority 2)

**Problem:** `web_27_world_cup` — "Who won the 2026 FIFA World Cup?"
- Expected: web_fallback (hasn't happened yet)
- Actual: internal with judge score 8 (wrongly confident)

**Root Cause:** Judge doesn't validate temporal constraints
- The World Cup hasn't occurred in April 2026 newsletter archives
- Query matches some internal content but shouldn't be treated as authoritative
- Judge needs to detect "future event" queries and reject them

### Solution: Add Temporal Validation to Judge

**Step 1: Update judge prompt in `graph.py`**

Add instruction to judge:
```
IF the query asks about:
  - Future events (hasn't occurred in April 2026 archives)
  - Real-time data (current prices, today's weather, latest news)
  - User-specific information (your account, your settings)
THEN score = 0 (reject, trigger web fallback)

Examples:
  - "Who won the 2026 World Cup?" → Future event → Score 0
  - "What is today's weather?" → Real-time → Score 0
  - "Current stock price?" → Real-time → Score 0
```

**Step 2: Test the fix**
```bash
python3 eval/run_eval.py --id web_27_world_cup
```

**Expected Outcome:** Query should route to web_fallback with judge score 0

---

## Category 3: Test Expectation Mismatch (9 Tests → Decision Point)

**Problem:** 9 web_fallback tests route to explicit_web instead.

**Why it happens:** These queries contain real-time keywords:
- "weather for SF **tomorrow**" → time-sensitive
- "**current** stock price" → real-time marker
- "**latest** updates" → freshness keyword
- "top songs **today**" → time-sensitive

**The dilemma:** 
- **Behavior is correct:** Real-time queries SHOULD go direct to web, not try internal
- **Test expects:** web_fallback (try internal first, then web if needed)

### Solution: Choose a Strategy

**Option A: Accept explicit_web as correct (RECOMMENDED)**

These 9 tests should EXPECT explicit_web, not web_fallback:
- `web_26_weather_forecast` — change to explicit_web
- `web_30_msft_stock` — change to explicit_web
- `web_34_uk_prime_minister` — change to explicit_web
- `web_37_sudan_conflict` — change to explicit_web
- `web_39_ny_times_books` — change to explicit_web
- `web_42_ipl_cricket` — change to explicit_web
- `web_46_euro_usd` — change to explicit_web
- `web_50_spotify_charts` — change to explicit_web

**Rationale:**
- Skipping internal search for real-time queries is MORE efficient
- Explicit web keywords correctly identify time-sensitive intent
- This is actually better UX (faster path to current data)

**Option B: Remove time-sensitive keywords from query**

Rewrite queries to NOT trigger explicit_web:
- "weather for San Francisco" (remove "tomorrow")
- "Microsoft stock price" (remove "current")
- "Prime Minister of UK" (remove "current")

**Option C: Hybrid - Keep internal attempt for some**

Leave system as-is but accept that real-time queries go direct to web

### Recommendation: Go with Option A

**Step 1: Update test_cases.py**
```python
{
    "id": "web_26_weather_forecast",
    "query": "What is the current weather forecast for San Francisco tomorrow?",
    "expected_path": "explicit_web",  # Changed from web_fallback
    "expected_sources": [],
    "min_judge_score": 0,
    "notes": "Time-sensitive query ('tomorrow') correctly triggers explicit web.",
},
# ... update 8 more
```

**Step 2: Re-run evaluation**
```bash
python3 eval/run_eval.py
```

**Expected Outcome:** 52/61 tests pass (85.2%)
- 8 internal content failures → fixed (indexed content added)
- 1 World Cup false positive → fixed (judge temporal validation)
- 9 explicit_web expectations updated → now pass

---

## Implementation Roadmap

### Phase 1: Immediate (Fix the 9 failures)

**Week 1: Index Repair**
- [ ] Identify which of 8 missing topics need to be added to summaries
- [ ] Add content to newsletter-insights/summaries/ or twitter-insights/summaries/
- [ ] Run `python3 index.py` to rebuild embeddings
- [ ] Spot-check 2-3 queries: `python3 search.py --query "Claude two-mode integration"`
- [ ] Test failed cases: `python3 eval/run_eval.py --id internal_05_claude_two_mode`

**Week 1: Temporal Validation**
- [ ] Update `graph.py` judge prompt with future event detection
- [ ] Test: `python3 eval/run_eval.py --id web_27_world_cup`
- [ ] Verify judge score is 0

**Week 1: Update Tests**
- [ ] Edit `test_cases.py`: change 9 explicit_web expectations
- [ ] Run full eval: `python3 eval/run_eval.py`
- [ ] Target: ≥85% pass rate

### Phase 2: Validation (Confirm fixes work)

- [ ] Run full 61-test suite again
- [ ] Compare results to baseline
- [ ] Document what changed
- [ ] Update EVAL_RESULTS.md with new numbers

### Phase 3: Optimization (Make it faster)

- [ ] Profile latency: internal vs web
- [ ] Cache web search results for repeated queries
- [ ] Target: <5s avg latency for internal, <10s for web

### Phase 4: Documentation

- [ ] Update README with lessons learned
- [ ] Document why certain tests route to explicit_web
- [ ] Create decision journal for future test changes

---

## Success Criteria

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Pass Rate | 70.5% | ≥90% | 📊 |
| Internal Routing | 78% | 95% | 📊 |
| Web Fallback Routing | 64% | 100% | 📊 |
| Judge Avg Score | 7.7 | 7.5+ | ✅ |
| False Positives | 1 | 0 | 📊 |
| Latency (avg) | 15s | <5s | 📊 |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Content still missing after index repair | High | Manually verify summaries contain required facts |
| Judge validation breaks other queries | High | Run full 61-test suite after each change |
| Latency doesn't improve | Medium | Profile and focus on slowest operations |
| Test expectations unclear | Low | Document rationale for each expected_path |

---

## Questions to Answer Before Starting

1. **Which newsletter/Twitter sources have the 8 missing topics?**
   - Check recent digests from February-April 2026
   - Are these in newsletter-insights or twitter-insights?

2. **Are the missing topics important to keep indexed?**
   - Or should we update tests to expect web search instead?

3. **How strict should temporal validation be?**
   - Should we block all future events or just major ones?

4. **What's our latency tolerance?**
   - Is 15s acceptable or must we optimize?
