# Chunking Strategy: Bullet-Level Precision

## Overview

The search-news-twitter system chunks summary files at the **bullet-level** — each bullet point under a topic heading becomes its own searchable chunk. This document explains why, the tradeoffs, and how to modify the strategy if needed.

---

## Summary File Format

Source files come from `newsletter-insights/summaries/` and `twitter-insights/summaries/` in Markdown format:

```markdown
## Author Name or Twitter Handle

### Topic Heading `Tag`

- First bullet point
- Second bullet point
- Third bullet point

### Another Topic `Tag`

- Bullet text here
```

**Structure:**
- `## ` — Author line (one per file or section)
- `### ` — Topic heading with optional backtick-quoted tag (AI/ML, Engineering, Product, Business, Other)
- `- ` — Individual bullet points (insights, tips, findings, links, etc.)

---

## Chunking Strategy: Bullet-Level

### How It Works

Each bullet point becomes its own chunk. When the parser encounters a bullet:

```python
# Pseudocode from index.py
for bullet in current_bullets:
    text = f"{current_title}\n{current_author}\n- {bullet}"
    doc_id = f"{rel_path}::{chunk_index}"
    chunks.append({
        "id": doc_id,
        "text": text,
        "metadata": {
            "source_type": "newsletter" or "twitter",
            "date": "YYYY-MM-DD",
            "author": author_name,
            "title": current_title,
            "tag": "AI/ML" or "Engineering" or ...,
        }
    })
```

**Result:** Each chunk is roughly 50–200 characters. The chunk text includes the topic title and author as context.

### Example

Input:
```
## ByteByteGo

### How Netflix Live Streams to 100M Devices in 60 Seconds `Engineering`

- CDN pre-positioning: segments pushed to edge nodes before stream starts
- Warm-up signals sent to edge nodes to reduce delivery window
- Adaptive bitrate streaming handles per-device bandwidth variance
- P2P mesh during burst peaks reduces CDN egress cost
```

Output: 4 chunks

```
Chunk 1: "How Netflix Live Streams to 100M Devices in 60 Seconds\nByteByteGo\n- CDN pre-positioning: segments pushed to edge nodes before stream starts"
  metadata: {date: 2026-04-02, author: ByteByteGo, title: "How Netflix...", tag: Engineering, source_type: newsletter}

Chunk 2: "How Netflix Live Streams to 100M Devices in 60 Seconds\nByteByteGo\n- Warm-up signals sent to edge nodes to reduce delivery window"
  metadata: {...same...}

Chunk 3: "How Netflix Live Streams to 100M Devices in 60 Seconds\nByteByteGo\n- Adaptive bitrate streaming handles per-device bandwidth variance"
  metadata: {...same...}

Chunk 4: "How Netflix Live Streams to 100M Devices in 60 Seconds\nByteByteGo\n- P2P mesh during burst peaks reduces CDN egress cost"
  metadata: {...same...}
```

---

## Why Bullet-Level?

### Motivation

Initially, the system used **topic-level chunking** — all bullets under a topic heading were concatenated into one chunk. This resulted in:

- **85 total chunks** from ~2 months of newsletters/tweets
- **Poor precision:** off-topic bullets diluted semantic signals
- **Query misses:** "tell me about subagents" returned 0 matches despite 3 relevant bullets in the summaries

### Switched to Bullet-Level

After changing to bullet-level chunking:

- **294 total chunks** from the same data (3.5x more)
- **Better precision:** Each bullet is a discrete insight with focused embedding
- **Query hits:** "tell me about subagents" now returns 3+ relevant matches
- **Less noise:** No "kitchen sink" chunks with mixed topics

### Empirical Validation

The "subagents" query is the canonical test case:
- **Topic-level:** 85 chunks, 0 results (query fuzzy-matched but topic heading wasn't in any chunk text)
- **Bullet-level:** 294 chunks, 3+ results (each bullet mention now matches independently)

---

## Tradeoffs

### Pros

- **Precision:** Focused semantic matching; each bullet is a self-contained idea
- **Scalability:** Even with 1 year of summaries (~10k bullets), retrieval is fast
- **Deduplication:** Bullets about the same topic in different sources appear as separate chunks (allowing comparative analysis)
- **Flexibility:** Easy to weight chunks (e.g., recent bullets higher) without merging/re-chunking

### Cons

- **Memory:** More chunks = larger ChromaDB index (~294 chunks × 384 embedding dimensions)
- **Embedding time:** 294 chunks to embed vs. 85 (still < 5 seconds one-time)
- **Source deduplication:** If the same bullet appears in multiple summaries, it creates duplicate chunks (minor issue, rare)
- **Context loss:** Topic heading context is repeated in every chunk (by design, not a bug)

### Numbers

- **Disk footprint:** ChromaDB index on disk is ~20–50 MB (negligible)
- **Embedding cost:** One-time at index build (new summaries are ~50–100 bullets/week, embedded on-demand)
- **Retrieval latency:** <500ms for ChromaDB query + embedding (unchanged by chunk count up to ~1000 chunks)

---

## The Embedding Model: `all-MiniLM-L6-v2`

### Choice Rationale

- **Size:** 22 MB (fits in memory, fast load)
- **Speed:** Encodes 1000 bullets in ~1 second on CPU
- **Quality:** Designed for semantic search on English text (newsletters and tweets are English)
- **Open source:** No API calls, no rate limits, no costs
- **Track record:** Widely used in RAG systems; benchmarked on MS MARCO and other retrieval datasets

### Is It Right for Our Data?

**Strengths:**
- Short text (bullets are 50–200 chars) — MiniLM is optimized for this
- English-only — our data is 100% English
- General domain — works on tech, product, business, and personal insights

**Weaknesses:**
- No domain-specific training — a finance-specific or code-specific embedding model might be better for highly technical summaries
- Multilingual options (e.g., `multilingual-MiniLM`) sacrifice quality for English-only data
- Newer models (e.g., `bge-base-en`, released 2023) may have higher benchmarked recall, but the difference is small for casual retrieval

**Bottom line:** Adequate for personal knowledge base retrieval. If search quality degrades after 1+ year of data, consider upgrading to a larger model (e.g., `sentence-transformers/all-mpnet-base-v2`, 438 MB).

---

## Overlap & Re-chunking

### No Overlap

Unlike some RAG systems, chunks are **not overlapped**. Each bullet is independent because:

- Bullets are discrete insights (no sentence spanning multiple bullets)
- Overlap would duplicate context (title + author already in every chunk)
- Retrieval precision is more important than recall (we have a judge gate to validate results)

### Re-chunking: When & How

If you want to change the chunking strategy (e.g., to sentence-level or sliding window), follow this process:

1. **Delete the old index:**
   ```bash
   rm -rf db/chroma/
   rm data/indexed.json
   ```

2. **Modify `index.py`'s `flush_chunk()` function** to implement your new strategy

3. **Re-index:**
   ```bash
   python3 index.py
   ```

4. **Verify results:**
   ```bash
   python3 search.py --query "test query"
   ```

### Example: Sentence-Level Chunking

If you wanted one chunk per sentence instead of per bullet:

```python
def parse_summary_file(...):
    chunks = []
    # ...
    for bullet in current_bullets:
        # Split bullet into sentences
        sentences = re.split(r'(?<=[.!?])\s+', bullet)
        for sentence in sentences:
            text = f"{current_title}\n{current_author}\n- {sentence.strip()}"
            chunks.append({...})
```

This would increase chunk count by 2–5x (bullets are often multi-sentence) and likely improve recall at the cost of chunk cohesion.

---

## Monitoring & Improvement

### Metrics to Track

- **Retrieval precision:** % of retrieved chunks actually relevant to the query
- **Retrieval recall:** % of relevant chunks in the DB that were retrieved
- **Judge score distribution:** Are most queries scoring 0-2 (poor matches) or 8-10 (great matches)?

### Signals to Change Chunks

1. **High fallback rate:** If >50% of queries fall back to web search, internal retrieval may be missing relevant chunks
2. **Low judge scores:** If most judge scores are <5, chunks may be too granular or off-topic
3. **Embedding model updates:** If you switch models, re-chunk everything (old and new embeddings are incompatible)

---

## Glossary

| Term | Meaning |
|------|---------|
| **Chunk** | One searchable unit (bullet-level: one bullet per chunk) |
| **Embedding** | 384-dimensional dense vector from `all-MiniLM-L6-v2` |
| **ChromaDB** | Persistent vector database; stores chunks + embeddings |
| **Metadata** | Structured info per chunk (source_type, date, author, title, tag) |
| **Topic heading** | `### Foo \`AI/ML\`` line in the source markdown |
| **Bullet point** | `- This is a bullet` line in the source markdown |

---

## Summary

- **What:** Each bullet point becomes its own searchable chunk
- **Why:** Better precision, query recall (validated empirically with "subagents" test)
- **Tradeoff:** More chunks (294 vs 85), but still <1s retrieval latency
- **Model:** `all-MiniLM-L6-v2` (22 MB, optimized for short English text)
- **Customize:** Delete `db/chroma/` + `data/indexed.json`, modify `index.py`, re-run indexing

---

**Last updated:** 2026-04-06  
**Chunking type:** Bullet-level  
**Embedding model:** all-MiniLM-L6-v2  
**Typical index size:** 294 chunks / ~20-50 MB
