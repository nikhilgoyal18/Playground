---
description: >
  Deep research on extracted Reddit problems — find existing solutions, gaps, and market opportunities.
  Use after running /reddit-problems. Trigger phrases: "research reddit problems", "deep dive reddit",
  "find solutions for reddit problems", "reddit research", "market opportunity analysis",
  "analyze reddit opportunities", "what solutions exist for reddit problems".
allowed-tools: WebSearch, Read, Write
---

# Reddit Research — Web Search + Market Report

Research existing solutions for problems extracted by `/reddit-problems`, classify the opportunity landscape, and produce a market research report.

## Steps

### 1. Load problems

Read `reddit-insights/data/problems.json`.

If the file doesn't exist, tell the user:
> Run `/reddit-problems` first to extract and rank problems before researching them.

### 2. Determine research scope

- If the user specified problem numbers (e.g. "research problems 1, 3, 5"), use those ranks
- Otherwise, auto-select all problems where `researched: false`, up to the **top 5** by `composite_score`

Tell the user exactly which problems you'll be researching (by number and title) and proceed.

### 3. Research each problem

For each selected problem, run **at most 3 web searches** — be efficient, stop when you have enough to classify:

**Search 1** (always): `[problem_statement] tool app software solution`
→ Looking for: product names, SaaS tools, GitHub repos, browser extensions, CLI tools

**Search 2** (if Search 1 is thin): `[core problem keywords] site:producthunt.com OR site:alternativeto.net`
→ Looking for: niche tools, launch announcements, alternative comparisons

**Search 3** (only if a specific competitor was found and you need more detail): `[product name] pricing limitations reviews`
→ Looking for: price point, what it doesn't do, user complaints

For each problem, determine:

**Solution Status** — pick one:
- `No solution` — no tools found that address this problem
- `Partial solution` — tools exist but don't fully solve it
- `Expensive solution` — solution exists but is enterprise/high-cost only
- `Crowded space` — multiple mature tools already exist
- `Open source only` — free tools exist but no polished commercial offering

**Competitors** — list up to 3 relevant tools/products with:
- Name
- One-sentence description
- The specific gap or limitation

**Gap** — the specific unmet need, even if solutions exist

**Opportunity Score** — 1-10:
- 10 = clear gap + validated high demand + no good solution
- 7-9 = partial solution with real gaps + strong demand signals
- 4-6 = crowded but differentiation possible
- 1-3 = well-solved problem, low opportunity

### 4. Write the research report

Write to `reddit-insights/problems/YYYY-MM-DD-research.md` (use today's date):

```markdown
# Reddit Market Research — YYYY-MM-DD

> Deep research on N problems from the YYYY-MM-DD scan. Problems researched: #1, #2, #3.

---

## Problem #1 — [Title]
**Opportunity Score: 8/10** | Category: Developer Tools | Intensity: high

### The Problem
[Clean problem statement from problems.json]

### Existing Solutions
| Tool | Type | Gap |
|------|------|-----|
| ToolName | SaaS | Specific limitation |
| AnotherTool | Open source | What it lacks |

**Solution Status**: Partial solution

### The Gap
[Specific unmet need — what no current tool does well]

### Opportunity
[Why this is worth building: Reddit engagement evidence + solution gap + target user]

---

## Problem #2 — [Title]
...

---

## Opportunity Summary

| Rank | Problem | Score | Status | Category |
|------|---------|-------|--------|----------|
| 1 | [Title] | 8/10 | Partial solution | Developer Tools |
| 2 | [Title] | 7/10 | No solution | DevOps/Infrastructure |
```

### 5. Update cache

Update `reddit-insights/data/problems.json` — set `researched: true` for each problem that was researched.

### 6. Present summary

Display the Opportunity Summary table and highlight the top 2–3 problems worth pursuing, with a one-sentence rationale for each.
