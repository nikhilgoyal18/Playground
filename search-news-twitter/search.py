"""
Semantic search across newsletter and Twitter summaries using RAG.
Auto-indexes new summary files before each query.

Usage:
    python3 search.py --query "database performance trade-offs"
    python3 search.py --query "RAG systems" --source newsletter --top-k 8
    python3 search.py --query "AI tools" --source twitter --date-from 2026-04-01
"""

import argparse
import json
from pathlib import Path

import ollama

from index import get_collection, get_model, index_new_files

OLLAMA_MODEL = "llama3.2"

# Cosine distance threshold — above this score the result is considered not relevant.
# Cosine distance ranges 0 (identical) to 2 (opposite). 0.7 ≈ similarity < 0.3.
RELEVANCE_THRESHOLD = 0.7

# Intent judge: below this score, skip answer generation
JUDGE_SCORE_THRESHOLD = 5

JUDGE_PROMPT = """You are a retrieval quality judge for a personal RAG knowledge base.

The knowledge base contains ONLY newsletter digests and Twitter digests. It does NOT contain general web knowledge, current events outside those digests, or any other sources.

Given a user query and the titles + content of the top retrieved chunks, evaluate whether the retrieval correctly captured the user's intent.

Respond with ONLY a valid JSON object, no other text:
{
  "intent_score": <integer 0-10>,
  "intent_understood": "<one sentence: what the user is actually looking for>",
  "retrieval_quality": "<good|partial|poor>",
  "reasoning": "<2-3 sentences explaining the score>",
  "recommendation": "<proceed|refine|no_data>"
}

Scoring:
- 8-10: Retrieved chunks directly and fully address the query intent
- 5-7: Partial match — some chunks relevant, others tangential
- 3-4: Weak match — chunks loosely related but miss the core intent
- 0-2: Poor match — chunks off-topic, or user is asking about something not in this knowledge base"""

SYSTEM_PROMPT = """You are a search assistant for a personal knowledge base of newsletter and Twitter digests.

Answer the user's question using ONLY the provided context chunks below.
- Do not use any knowledge outside the context.
- If the context does not contain enough information to answer, say: "I don't have enough relevant content in the indexed summaries to answer this question."
- Cite your sources inline using [Source N] notation matching the context headers.
- Be concise. Synthesize across sources when multiple chunks are relevant.
- Do not fabricate names, numbers, or claims not present in the context."""


def judge_retrieval(query, docs, metas):
    """Score whether retrieved chunks match the user's query intent (0-10)."""
    chunk_summaries = []
    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        first_line = doc.split("\n")[0]
        chunk_summaries.append(
            f"[Chunk {i}] {meta['source_type'].upper()} | {meta['author']} | {meta['title']}\n{first_line}"
        )
    chunks_text = "\n\n".join(chunk_summaries)
    user_msg = f"User query: {query}\n\nRetrieved chunks:\n\n{chunks_text}"

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response.message.content.strip()
        # Strip markdown code fences if the model wraps its JSON
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception:
        # If judge fails, default to proceeding — don't block on judge errors
        return {
            "intent_score": 7,
            "intent_understood": "unknown",
            "retrieval_quality": "unknown",
            "reasoning": "Judge parse error — proceeding.",
            "recommendation": "proceed",
        }


def build_where_filter(source, date_from):
    conditions = []
    if source:
        conditions.append({"source_type": source})
    if date_from:
        conditions.append({"date": {"$gte": date_from}})

    if len(conditions) == 0:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}


def search(query, source=None, top_k=5, date_from=None):
    collection = get_collection()

    if collection.count() == 0:
        print("Index is empty. Run `python3 index.py` first.")
        return

    model = get_model()
    query_embedding = model.encode([query], show_progress_bar=False).tolist()[0]
    where = build_where_filter(source, date_from)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs or distances[0] > RELEVANCE_THRESHOLD:
        print(
            "No sufficiently relevant content found in the indexed summaries for that query.\n"
            "Try rephrasing, or run the newsletter/twitter digest tools to add more content first."
        )
        return

    # Intent judge — semantic check before answer generation
    verdict = judge_retrieval(query, docs, metas)
    score = verdict.get("intent_score", 0)
    print(
        f"\nIntent Judge | score: {score}/10 | "
        f"quality: {verdict.get('retrieval_quality')} | "
        f"{verdict.get('recommendation')}"
    )
    print(f"  Intent understood: {verdict.get('intent_understood', '')}")
    print(f"  Reasoning: {verdict.get('reasoning', '')}\n")

    if score < JUDGE_SCORE_THRESHOLD:
        print("Answer generation skipped — retrieval quality too low to produce a reliable answer.")
        print("Try rephrasing your query or adding more content with /newsletter-insights or /twitter-insights.")
        return

    # Build context blocks with [Source N] labels
    context_blocks = []
    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        tag_part = f" | {meta['tag']}" if meta.get("tag") else ""
        header = (
            f"[Source {i}] {meta['source_type'].upper()} | "
            f"{meta['date']} | {meta['author']} | {meta['title']}{tag_part}"
        )
        context_blocks.append(f"{header}\n{doc}")

    context_text = "\n\n---\n\n".join(context_blocks)

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n\n{context_text}\n\n---\n\nQuestion: {query}"},
            ],
        )
    except Exception as e:
        if "connection" in str(e).lower():
            print("Ollama is not running. Start it with: ollama serve")
            return
        raise

    print(f"\n{response.message.content}\n")
    print("---")
    print("Sources:")
    for i, (meta, dist) in enumerate(zip(metas, distances), start=1):
        src_label = meta["source_type"].upper().ljust(10)
        tag_part = f" [{meta['tag']}]" if meta.get("tag") else ""
        print(f"  [{i}] {src_label} | {meta['date']} | {meta['author']} | {meta['title']}{tag_part}")


def main():
    parser = argparse.ArgumentParser(
        description="Search newsletter and Twitter summaries with RAG"
    )
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument(
        "--source", choices=["newsletter", "twitter"], help="Filter by source type"
    )
    parser.add_argument(
        "--top-k", "-k", type=int, default=5, help="Number of chunks to retrieve (default: 5)"
    )
    parser.add_argument(
        "--date-from", help="Only search summaries from this date onward (YYYY-MM-DD)"
    )
    args = parser.parse_args()

    # Auto-index any new summary files before searching
    index_new_files(verbose=True)

    search(
        query=args.query,
        source=args.source,
        top_k=args.top_k,
        date_from=args.date_from,
    )


if __name__ == "__main__":
    main()
