# AI Setup Review: Search-News-Twitter
**Reviewer:** Claude (Seasoned AI Prompt Engineer)  
**Date:** 2026-04-07  
**Scope:** Instruction hierarchy, file routing, token efficiency, AI navigability

---

## Summary

The project has a clear entry point (`CLAUDE.md`) and good overall intent, but the current structure forces Claude to load or navigate far more content than most sessions require. The biggest problem is three overlapping files in `bugs-and-fixes/` that collectively repeat the same bugs, the same root causes, and the same code fixes across ~880 lines — most of which is only ever needed once. `CHUNKING_STRATEGY.md` (264 lines) and `EVAL_RESULTS.md` (434 lines) are dense reference artifacts that are unlikely to be needed in most sessions, but there are no signals telling the agent when to skip them.

---

## 🔴 Critical Issues

### 1. Three overlapping files in `bugs-and-fixes/`

`bugs-and-fixes.md`, `FIXES_APPLIED_SUMMARY.md`, and `IMPROVEMENT_PLAN.md` all describe the same 3 bugs with the same root causes and largely the same code fixes. Each file says it's the authoritative reference — none of them are.

**Combined line count:** ~880 lines  
**Unique content per file:** ~30%  
**Duplication rate:** ~70%

Specific overlaps:
- Bug descriptions, root causes, and fix code appear verbatim in all three files
- "Key Learnings" section is copied across all three
- Recommendations appear in all three with the same action items
- `bugs-and-fixes.md` even has a note "Do NOT create separate bug/fix documentation files" — which was then ignored

**Fix:** Merge all three into a single `bugs-and-fixes/BUGS.md`. Retire the other two files. One file, one source of truth.

---

### 2. `CLAUDE.md` is loading too much into every session

`CLAUDE.md` is ~155 lines and is loaded into every session. It currently contains:

- How it works (good — core context)
- One-time setup instructions (Ollama install, pip install, `python3 index.py`) — not needed after setup
- Full CLI usage reference with 6 example commands — reference material, not core instructions
- Full keyword trigger list for explicit web routing — duplicates what's in code
- 4 troubleshooting scenarios — never needed unless something breaks
- 6 SQLite audit queries — only needed during analysis sessions
- How chunking works (briefly) — then `CHUNKING_STRATEGY.md` covers this in full

**Fix:** Strip `CLAUDE.md` to ~50 lines: what the project does, the search flow (1-7 steps), key files, and CLI syntax (just the basic form). Move setup, troubleshooting, SQL queries, and keyword lists to a `REFERENCE.md` that Claude reads only when needed.

---

## 🟡 Significant Improvements

### 3. `CHUNKING_STRATEGY.md` (264 lines) has no routing signal

This file contains valuable background on chunking decisions, embedding model tradeoffs, overlap policy, glossary, and re-chunking steps. But there's nothing in `CLAUDE.md` or the folder structure that tells the agent when to read it vs. skip it.

In most sessions (run a search, debug a query, add a feature), this file is irrelevant. There is no cost to reading it except token budget — and at 264 lines, that cost is real.

**Fix:** Add a one-line pointer in `CLAUDE.md` under the Files table: `CHUNKING_STRATEGY.md — read only when modifying index.py or changing chunking behavior`. This gives the agent explicit permission to skip it.

---

### 4. `EVAL_RESULTS.md` (434 lines) heavily overlaps with the bugs files

`EVAL_RESULTS.md` contains:
- The same 3 bug descriptions as the `bugs-and-fixes/` files
- Per-test results that are superseded by later test runs
- The same root cause analysis repeated from `bugs-and-fixes.md`
- The same code fixes in a third copy

It's the original analysis artifact — useful for historical reference, but it's become a stale mirror of other files. It should not be read as part of any active workflow.

**Fix:** Add a routing note at the top: `"Historical analysis file. For current bug status see bugs-and-fixes/BUGS.md. For current pass rates, run the eval harness."` This tells the agent the file is archival, not operational.

---

### 5. `PLAN.md` "Shipped" section duplicates `CLAUDE.md` Updates header

`CLAUDE.md` has a "Latest Updates (April 2026)" section with shipped features. `PLAN.md` has a "Shipped" section with the same list. They diverge slightly (PLAN.md includes LangGraph orchestration detail that CLAUDE.md omits), but neither is the clear owner.

The "Backlog / Ideas" section of `PLAN.md` is the only truly unique content.

**Fix:** Remove the "Shipped" section from `PLAN.md` and keep only the backlog. Or drop the Updates header from `CLAUDE.md` and let `PLAN.md` be the single owner of both shipped and pending work.

---

## 🟢 Suggestions & Polish

### 6. `eval/` folder has no index or routing signal

The `eval/` folder contains `run_eval.py`, `test_cases.py`, `EVAL_RESULTS.md`, and `__init__.py`. When an agent needs to run evaluation or check test pass rates, there's nothing in `CLAUDE.md` pointing here.

**Fix:** Add one line to the Files table in `CLAUDE.md`: `eval/ — evaluation harness; run python3 eval/run_eval.py to check pass rates`. This costs nothing and gives the agent a reliable navigation path.

### 7. Keyword list in `CLAUDE.md` is not the source of truth

`CLAUDE.md` lists explicit web keywords that "trigger direct web search." But the actual list lives in `graph.py` (`EXPLICIT_WEB_KEYWORDS`). When someone updates the list in code, the docs drift silently.

**Fix:** Remove the keyword list from `CLAUDE.md` and replace with: `"See EXPLICIT_WEB_KEYWORDS in graph.py for the current list."` One less thing to keep in sync.

### 8. `data/query_cache.json` is not documented anywhere

`data/query_cache.json` exists (presumably for caching normalized queries) but is not listed in the Files table in `CLAUDE.md` and is not explained in the README. An agent trying to debug caching behavior has no documented reference.

**Fix:** Add a one-line entry to the Files table: `data/query_cache.json — query normalization cache (auto-managed)`.

---

## ✅ What's Working Well

- **Clear primary entry point.** `CLAUDE.md` is unambiguously the root; it's auto-loaded and positioned correctly as the project's AI-facing home file.
- **`PLAN.md` is appropriately short.** The backlog section is concise and useful without being bloated.
- **eval/ is well-scoped.** The folder is clearly for evaluation tooling, named predictably, and separated from production code.
- **SQLite logging documentation is thorough.** The audit queries in `CLAUDE.md` are genuinely useful reference material — the only issue is they're always loaded rather than on-demand.
- **`bugs-and-fixes/` folder intent is correct.** Isolating bug tracking from the main CLAUDE.md is the right call. The folder just has too many files doing the same job.
- **File naming is human-readable and predictable** across the project.

---

## Next Steps (Priority Order)

1. **Merge `bugs-and-fixes/` into one file** — Delete `FIXES_APPLIED_SUMMARY.md` and `IMPROVEMENT_PLAN.md`, consolidate into `BUGS.md`. Eliminates ~600 lines of duplication immediately.

2. **Slim `CLAUDE.md` to ~50 lines** — Move setup steps, troubleshooting, SQL audit queries, and keyword list to a `REFERENCE.md`. Add routing signal: "Read `REFERENCE.md` only for setup, debugging, or analysis tasks."

3. **Add routing signals to remaining reference files** — One-line note on `CHUNKING_STRATEGY.md` ("read when changing chunking"), `EVAL_RESULTS.md` ("historical; see BUGS.md for current status"), and `eval/` ("run eval harness here").

4. **Fix keyword list ownership** — Remove the duplicated keyword list from `CLAUDE.md`; point to `graph.py` as the source.

5. **Document `query_cache.json`** — Add one line to the Files table.
