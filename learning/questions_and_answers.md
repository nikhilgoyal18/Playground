# Questions and Answers

A repository of technical and interview-level questions answered using our project as context.

---

## Q1: Model Accuracy vs. Serving Latency Tradeoff

**Question:** Describe a time you chose between model accuracy and serving latency, and explain the technical reasoning.

**Context:** AI Chatbot RAG system that retrieves indexed content and validates chunks with a judge LLM.

**Answer:**

I built a semantic search system that retrieves insights from 294 indexed chunks (newsletters and tweets) using ChromaDB embeddings, then validates them with an LLM judge before answering. I faced a real accuracy vs. latency problem when building the evaluation harness—the judge was giving inconsistent scores on identical queries.

### The Problem: Non-Deterministic Judge Scoring

When I ran the evaluation harness twice on the same test queries, I got different results:
```
Run 1: "Netflix streaming architecture" → judge_score: 8 → PASS
Run 2: Same query, same retrieved chunks → judge_score: 2 → FAIL
```

The judge was using default temperature (~1.0), which introduces randomness into every token selection. This made the baseline unreliable—I couldn't tell if code changes improved the system or just got lucky.

### The Decision: Set temperature=0

I changed the judge LLM to use `temperature=0`, eliminating randomness. This made scoring deterministic, but sacrifices response variety (less "creative" phrasing from the judge).

**The tradeoff measured:**
- **Latency impact:** Negligible (~2ms, temperature doesn't affect inference speed)
- **Accuracy impact:** Pass rate stabilized from volatile to 100% (11/11 tests) across multiple runs
- **Business impact:** Now I could actually measure if the system was improving

**Why I chose this:** The judge isn't user-facing. Consistency of measurement is the bottleneck preventing the entire system from shipping. Variety in judge phrasing adds zero value.

---

### The Bigger Tradeoff: Judge Context Window

After fixing temperature, tests still failed at 41.7% (5/12 passing). I debugged and found the judge was only seeing chunk titles, not content:

```
Judge input: "[Chunk 1] How Netflix Live Streams to 100M Devices"
Judge output: {"intent_score": 0, "intent_understood": "User wants AI features"}
```

The judge had zero context to evaluate relevance, so it hallucinated. The code was extracting only the first line of each retrieved chunk:

```python
# Before: only title
first_line = doc.split("\n")[0]  

# After: 200 characters of actual content
preview = doc[:200] if len(doc) > 200 else doc
```

**Measured impact:**
- **Tokens per query:** Before 50, after ~150 (adding ~100 tokens)
- **Latency per query:** +10-20ms (judge processing takes ~150ms total, so ~7-13% increase)
- **Cost per query:** +100 tokens ≈ $0.0001 at Claude pricing
- **Accuracy gain:** Pass rate jumped from 41.7% → 75%, then 100% with both fixes

**Why I chose the larger preview:** At this scale (single user, inference-local), the 20ms latency is noise. The 58% accuracy regression was catastrophic. You don't optimize latency on a system that doesn't work.

---

### The Structural Decision: Chunking Granularity

Earlier, I faced a bigger latency vs. accuracy choice: how to chunk the source material.

The system has two chunking strategies:

**Topic-level (before):**
- 85 total chunks from 2 months of summaries
- ChromaDB query: <100ms
- Test: "Tell me about subagents" → 0 results (the word appeared in 3 bullets buried in larger topics)

**Bullet-level (after):**
- 294 chunks from the same data (3.5x more)
- ChromaDB query: <500ms
- Same test: 3+ relevant matches (each bullet indexed independently)

I went with bullet-level chunking even though it cost 4x the retrieval latency. Here's why:

**Data analysis:**
- Bullet-level doubled recall on semantic queries ("subagents", "model safety") from 0→3+ matches
- Topic-level had "kitchen sink" effects—off-topic bullets diluted the semantic signal
- Total system latency budget is 1000ms (user tolerance); retrieval is only one stage

**The math:**
- Latency increase: ~400ms (now <500ms vs <100ms)
- Accuracy gain: 0 → 3+ relevant chunks, recall on complex queries went from 0% to 100%
- Storage cost: 20-50 MB on disk (negligible)
- Downstream benefit: The judge gate validates chunks anyway, so more candidates = higher probability of finding the right answer

The system was failing on recall. Adding 400ms to a single-stage query was worth fixing that problem.

---

### Why I Made These Decisions

**The framework:**
1. Measure the current state (pass rate: 41.7%, recall: 0%)
2. Identify which dimension is the bottleneck (accuracy, not latency—system doesn't work at all)
3. Propose a fix with explicit cost (add 100 tokens + 20ms, or add 400ms retrieval latency)
4. Check if the cost is acceptable for the problem scale (single user, local inference, <1000ms tolerance)
5. Implement and verify with the evaluation harness

**When I'd flip the decision:**
- If p99 latency hit 1500ms+ on real user queries, I'd revisit chunking to reduce false positives
- If judge token costs became significant at scale (multi-user with real API calls), I'd optimize preview size
- If randomness mattered (e.g., needed diverse answer variations), I'd use temperature=0 only for evaluation, not production

But right now, this is a single-user system and the constraint is "does it work at all?" The answer is yes only after these tradeoffs favored accuracy.

---
