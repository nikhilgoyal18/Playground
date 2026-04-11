"""
LangGraph-based orchestration for semantic search with internal/web fallback.
Replaces manual orchestration in search.py with explicit graph topology,
typed state, and per-node retry policies.

Graph flow:
  query_normalize → index_sync → route → [internal_retrieve → judge_gate → generate_answer] or [web_search]
"""

import json
import re
from typing import TypedDict, Optional, List, Literal
from typing_extensions import Annotated
import operator

import ollama
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy

from index import get_collection, get_model, index_new_files
from web_search import web_search

OLLAMA_MODEL = "llama3.2"
RELEVANCE_THRESHOLD = 0.8
JUDGE_SCORE_THRESHOLD = 5

EXPLICIT_WEB_KEYWORDS = {
    "latest", "last week", "last month", "last year", "yesterday", "today",
    "this week", "this month", "breaking", "news", "current", "stock", "price",
    "right now", "live", "recently", "just announced", "new release", "trending",
}

JUDGE_PROMPT = """You are a retrieval quality judge. Score whether retrieved chunks match the user's intent (0-10).

CRITICAL: Respond with ONLY valid JSON. No preamble, no explanation, no markdown.
- All keys must be quoted: "intent_score"
- All values must be quoted OR be integers: "good" or 8
- No trailing commas. No unquoted fields.

Strict template:
{"intent_score": 8, "intent_understood": "User wants AI features", "retrieval_quality": "good", "reasoning": "Chunks directly answer", "recommendation": "proceed"}

RETRIEVAL DISTANCE VALIDATION (CRITICAL):
- Retrieval distance shown in brackets: (retrieval distance: X.XXX)
- Distances < 0.3: Excellent match
- Distances 0.3-0.5: Good match
- Distances 0.5-0.65: Fair match (acceptable if content still relevant)
- Distances > 0.65: Poor match → LIKELY OFF-TOPIC → Score ≤4

TEMPORAL VALIDATION (CRITICAL):
If the query asks about a FUTURE EVENT that hasn't occurred in the April 2026 knowledge base:
- "Who won the 2026 FIFA World Cup?" → Future event (hasn't occurred)
- "What will happen..." → Future prediction
- "upcoming..." or "next..." → Not yet occurred
THEN SCORE = 0 (REJECT - send to web search for current data)

Scoring guide:
- 8-10: Chunks directly answer the query with complete, specific details AND retrieval distance < 0.5
- 6-7: Chunks address the CORE TOPIC with good matches (distance 0.3-0.5) but may lack some details
  * Example: Query "How did Shopify CEO use Karpathy Loop?" + Chunk about it with distance 0.35 = SCORE 6-7
- 5: Marginal match - chunks mention main entities BUT distance is high (0.5-0.65) OR details are very sparse
- 3-4: Related domain but different subtopic OR distance > 0.65 (poor retrieval)
- 0-2: Off-topic, future event, missing core entities, OR distance > 0.65 with zero semantic connection

SPECIFIC TERM MATCHING:
- If query asks about a specific term/acronym/concept (e.g., "what is A2A?", "what is RAG?"), chunks MUST explicitly mention it
  * Query "what is A2A in AI?" + chunks that say "AI agents" (without mentioning A2A) = Score 2-3 (REJECT - send to web)
  * Query "how does RAG work?" + chunks mentioning RAG system = Score ≥6 (ACCEPT)
- Semantic equivalence is OK for known concepts, but NOT for novel acronyms/terms

CORE TOPIC MATCHING (WITH DISTANCE CONSIDERATION):
- If chunks mention main entities AND distance < 0.5: score ≥6
- If chunks mention main entities BUT distance > 0.65: score ≤4 (poor retrieval, reject)
- Accept partial coverage ONLY if distance < 0.6 (good enough match to still be relevant)
- REJECT when: Completely off-topic OR future event OR distance > 0.65 OR missing query's specific terms/acronyms"""

SYSTEM_PROMPT = """You are a search assistant for a personal knowledge base of newsletter and Twitter digests.

Answer the user's question using ONLY the provided context chunks below.
- The chunks have already been validated as relevant to the query. Use them.
- Cite your sources inline using [Source N] notation matching the context headers.
- Be concise. Synthesize across sources when multiple chunks are relevant.
- Do not fabricate names, numbers, or claims not present in the context.
- Only say "I don't have enough relevant content in the indexed summaries to answer this question."
  if the chunks are genuinely about a completely different topic than the question."""

INTENT_CLASSIFIER_PROMPT = """You are a routing classifier. Classify the user's query as GENERAL or PERSONAL.

GENERAL: A pure textbook definition or explanation of a fundamental ML/CS concept. The query asks about core concepts, algorithms, or mechanisms with no applications, systems, or named products.

PERSONAL: Everything else — technical architectures, how-to guides, news, events, people, companies, products, systems, applications, and any questions that might benefit from recent information or your personal reading history.

Output ONLY the single word: GENERAL or PERSONAL. No explanation. No punctuation.

Examples — GENERAL (pure fundamental concepts):
- "what is a neural network?" → GENERAL
- "explain backpropagation" → GENERAL
- "what is cosine similarity?" → GENERAL
- "how does attention work?" → GENERAL
- "define overfitting" → GENERAL
- "how does backpropagation work?" → GENERAL

Examples — PERSONAL (everything else):
- "what is RAG?" → PERSONAL (named system/product)
- "explain transformer architecture" → PERSONAL (named architecture)
- "agentic RAG systems" → PERSONAL (system/architecture)
- "database indexing trade-offs" → PERSONAL (application/system design)
- "what is the Karpathy Loop?" → PERSONAL (named concept)
- "how does photosynthesis work?" → PERSONAL (biology, needs web)
- "how to make risotto" → PERSONAL (how-to, needs web)
- "latest news" → PERSONAL (recent info needed)

Strict rules (apply in order, rules must be fully satisfied):
1. If the query mentions photosynthesis, biology, physics, chemistry, cooking, history, geography, weather, Roman, ancient, medieval, fall of, Empire, or historical → PERSONAL
2. If the query names any product, person, company (Google, Claude, Anthropic, Andrew Ng, Shopify, Bolt) → PERSONAL
3. If the query contains: architecture, system, pattern, trade-off, framework, library, tool, how to, how do, current, latest, recent, stock, price → PERSONAL
4. If the query contains "I read", "my digest", "you told me", "last time" → PERSONAL
5. Only if ALL of the following are true, AND none of rules 1-4 triggered:
   - Starts with "what is", "explain", "define", or "how does"
   - AND does NOT contain proper nouns, brand names, or application-specific terms
   - AND is about a fundamental CS/ML concept (algorithms, techniques, mathematical concepts, mechanisms - things found in a ML textbook)
   → Then GENERAL
6. All other cases → PERSONAL"""

LLM_ONLY_SYSTEM_PROMPT = """You are a knowledgeable assistant. Answer the user's question clearly and concisely from your own knowledge.
- Be concise and direct.
- Do not reference any context documents, digests, or search results — there are none.
- Do not hedge with "I don't have access to..." for general knowledge questions.
- If you genuinely don't know the answer, say so briefly."""


class SearchState(TypedDict):
    """Shared state across all graph nodes."""
    # Input
    query: str
    normalized_query: str
    source: Optional[str]
    top_k: int
    date_from: Optional[str]

    # Routing
    explicit_web_detected: bool

    # Intent classification
    intent_class: Optional[str]       # "GENERAL" | "PERSONAL" | None
    intent_classify_skipped: bool     # True if explicit_web_detected
    llm_only_answer: Optional[str]    # Answer from generate_llm_answer

    # Internal retrieval
    docs: List[str]
    metas: List[dict]
    distances: List[float]
    chunks_passed_threshold: Optional[bool]

    # Judge
    judge_score: Optional[int]
    judge_quality: Optional[str]
    judge_intent_understood: Optional[str]
    judge_reasoning: Optional[str]
    judge_parse_error: bool

    # Answer
    internal_answer: Optional[str]
    internal_answer_generated: Optional[bool]
    internal_succeeded: bool
    internal_no_content_response: bool
    web_answer: Optional[str]
    web_result_count: int
    web_succeeded: bool
    web_was_fallback: bool

    # Audit
    final_output: Optional[str]
    errors: Annotated[List[str], operator.add]
    duration_ms: Optional[int]
    timestamp: str

    # Token tracking (accumulated across all LLM nodes)
    total_llm_tokens_in: Annotated[int, operator.add]
    total_llm_tokens_out: Annotated[int, operator.add]

    # Conversation
    conversation_history: List[dict]
    conversation_id: Optional[str]


# ============================================================================
# Node functions
# ============================================================================

def query_normalize(state: SearchState) -> dict:
    """Fix typos in the query before anything else."""
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Fix typos in the user's search query. Return ONLY the corrected query, "
                        "no explanation, no quotes, no punctuation changes."
                    ),
                },
                {"role": "user", "content": state["query"]},
            ],
        )
        normalized = response.message.content.strip()
        tokens_in = getattr(response, 'prompt_eval_count', 0) or 0
        tokens_out = getattr(response, 'eval_count', 0) or 0
        return {
            "normalized_query": normalized or state["query"],
            "total_llm_tokens_in": tokens_in,
            "total_llm_tokens_out": tokens_out,
        }
    except Exception as e:
        return {"normalized_query": state["query"], "errors": [f"query_normalize error: {str(e)}"]}


def index_sync(state: SearchState) -> dict:
    """Index any new summary files before searching."""
    try:
        index_new_files(verbose=False)
        return {}
    except Exception as e:
        return {"errors": [f"index_sync error: {str(e)}"]}


def detect_explicit_web(state: SearchState) -> dict:
    """Detect explicit web keywords and update state using word-boundary matching."""
    query_lower = state["normalized_query"].lower()
    # Use word-boundary regex to avoid matching keywords inside words
    # e.g., "live" should not match "livelihood", "current" should not match in "currently"
    pattern = r'\b(' + '|'.join(re.escape(kw) for kw in EXPLICIT_WEB_KEYWORDS) + r')\b'
    explicit_web = bool(re.search(pattern, query_lower))
    return {"explicit_web_detected": explicit_web}


def route_explicit_web(state: SearchState) -> Literal["web_search", "classify_intent"]:
    """Route based on explicit web keywords."""
    if state.get("explicit_web_detected"):
        return "web_search"
    return "classify_intent"


def classify_intent(state: SearchState) -> dict:
    """Classify query as GENERAL (LLM-only) or PERSONAL (needs retrieval/web)."""
    if state.get("explicit_web_detected"):
        return {"intent_class": "PERSONAL", "intent_classify_skipped": True}
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": INTENT_CLASSIFIER_PROMPT},
                {"role": "user", "content": state["normalized_query"]},
            ],
            options={"temperature": 0},
        )
        raw = response.message.content.strip().upper()
        intent = raw if raw in ("GENERAL", "PERSONAL") else "PERSONAL"
        return {
            "intent_class": intent,
            "intent_classify_skipped": False,
            "total_llm_tokens_in": getattr(response, 'prompt_eval_count', 0) or 0,
            "total_llm_tokens_out": getattr(response, 'eval_count', 0) or 0,
        }
    except Exception as e:
        return {
            "intent_class": "PERSONAL",
            "intent_classify_skipped": False,
            "errors": [f"classify_intent error: {str(e)}"],
        }


def route_after_intent(state: SearchState) -> Literal["llm_only", "internal_retrieve"]:
    """Route to LLM-only answer or internal retrieval based on intent classification."""
    if state.get("intent_class") == "GENERAL":
        return "llm_only"
    return "internal_retrieve"


def route_after_llm_only(state: SearchState) -> Literal["internal_retrieve", Literal[END]]:
    """If llm_only failed (Ollama error), fall back to internal_retrieve."""
    if state.get("llm_only_answer") is None:
        return "internal_retrieve"
    return END


def generate_llm_answer(state: SearchState) -> dict:
    """Answer a GENERAL intent query using only LLM parametric knowledge — no retrieval."""
    conv_history = state.get("conversation_history") or []
    messages = [{"role": "system", "content": LLM_ONLY_SYSTEM_PROMPT}]

    if conv_history:
        history_lines = [
            f"{'User' if t.get('role') == 'user' else 'Assistant'}: {t.get('content', '')}"
            for t in conv_history
        ]
        messages.append({
            "role": "user",
            "content": f"Prior conversation:\n{chr(10).join(history_lines)}\n\n---\n\nQuestion: {state['normalized_query']}"
        })
    else:
        messages.append({"role": "user", "content": state["normalized_query"]})

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        answer = response.message.content
        return {
            "llm_only_answer": answer,
            "final_output": answer,
            "total_llm_tokens_in": getattr(response, 'prompt_eval_count', 0) or 0,
            "total_llm_tokens_out": getattr(response, 'eval_count', 0) or 0,
        }
    except Exception as e:
        return {
            "llm_only_answer": None,
            "final_output": None,
            "errors": [f"generate_llm_answer error: {str(e)}"],
        }


def internal_retrieve(state: SearchState) -> dict:
    """Embed query and retrieve chunks from ChromaDB."""
    try:
        collection = get_collection()

        if collection.count() == 0:
            return {
                "docs": [],
                "metas": [],
                "distances": [],
                "chunks_passed_threshold": False,
            }

        model = get_model()
        query_embedding = model.encode([state["normalized_query"]], show_progress_bar=False).tolist()[0]

        # Build where filter
        where = None
        conditions = []
        if state.get("source"):
            conditions.append({"source_type": state["source"]})
        if state.get("date_from"):
            conditions.append({"date": {"$gte": state["date_from"]}})
        if len(conditions) == 1:
            where = conditions[0]
        elif len(conditions) > 1:
            where = {"$and": conditions}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(state["top_k"], collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        # Check threshold
        passed = bool(docs and distances and distances[0] <= RELEVANCE_THRESHOLD)

        return {
            "docs": docs,
            "metas": metas,
            "distances": distances,
            "chunks_passed_threshold": passed,
        }
    except Exception as e:
        return {
            "docs": [],
            "metas": [],
            "distances": [],
            "chunks_passed_threshold": False,
            "errors": [f"internal_retrieve error: {str(e)}"],
        }


def judge_gate(state: SearchState) -> dict:
    """LLM intent judge — raises on parse error to trigger RetryPolicy."""
    chunk_summaries = []
    distances = state.get("distances", [])

    for i, (doc, meta) in enumerate(zip(state["docs"], state["metas"]), start=1):
        # Show first 200 chars of chunk for judge to evaluate
        preview = doc[:200] if len(doc) > 200 else doc
        distance = distances[i-1] if i-1 < len(distances) else None
        distance_str = f" (retrieval distance: {distance:.3f})" if distance is not None else ""
        chunk_summaries.append(
            f"[Chunk {i}]{distance_str} {meta['source_type'].upper()} | {meta['author']} | {meta['title']}\n{preview}"
        )
    chunks_text = "\n\n".join(chunk_summaries)
    user_msg = f"User query: {state['normalized_query']}\n\nRetrieved chunks:\n\n{chunks_text}"

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        options={"temperature": 0},  # Deterministic for consistent evaluation
    )
    raw = response.message.content.strip()

    # Strip markdown code fences if present
    if "```" in raw:
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1].lstrip("json").strip()

    # RAISES on invalid JSON — triggers RetryPolicy
    verdict = json.loads(raw)

    tokens_in = getattr(response, 'prompt_eval_count', 0) or 0
    tokens_out = getattr(response, 'eval_count', 0) or 0

    return {
        "judge_score": int(verdict["intent_score"]),
        "judge_quality": verdict["retrieval_quality"],
        "judge_intent_understood": verdict["intent_understood"],
        "judge_reasoning": verdict["reasoning"],
        "judge_parse_error": False,
        "total_llm_tokens_in": tokens_in,
        "total_llm_tokens_out": tokens_out,
    }


def generate_answer(state: SearchState) -> dict:
    """Generate answer from internal chunks."""
    # Build context blocks
    context_blocks = []
    for i, (doc, meta) in enumerate(zip(state["docs"], state["metas"]), start=1):
        tag_part = f" | {meta['tag']}" if meta.get("tag") else ""
        header = (
            f"[Source {i}] {meta['source_type'].upper()} | "
            f"{meta['date']} | {meta['author']} | {meta['title']}{tag_part}"
        )
        context_blocks.append(f"{header}\n{doc}")

    context_text = "\n\n---\n\n".join(context_blocks)

    conv_history = state.get("conversation_history") or []
    user_content = f"Context:\n\n{context_text}\n\n---\n\nQuestion: {state['normalized_query']}"
    if conv_history:
        history_lines = []
        for turn in conv_history:
            role = "User" if turn.get("role") == "user" else "Assistant"
            history_lines.append(f"{role}: {turn.get('content', '')}")
        history_text = "\n".join(history_lines)
        user_content = f"Prior conversation:\n{history_text}\n\n---\n\n{user_content}"

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    answer = response.message.content

    # Check if LLM says it has no content (multiple patterns for robustness)
    answer_lower = answer.lower()
    no_content = any([
        "don't have enough relevant content" in answer_lower,
        "couldn't find" in answer_lower and "information" in answer_lower,
        "i don't have enough" in answer_lower,
        "not enough information" in answer_lower,
        "no information" in answer_lower and ("summaries" in answer_lower or "context" in answer_lower),
    ])

    tokens_in = getattr(response, 'prompt_eval_count', 0) or 0
    tokens_out = getattr(response, 'eval_count', 0) or 0

    return {
        "internal_answer": answer,
        "internal_answer_generated": True,
        "internal_no_content_response": no_content,
        "internal_succeeded": not no_content,
        "final_output": answer if not no_content else None,
        "total_llm_tokens_in": tokens_in,
        "total_llm_tokens_out": tokens_out,
    }


def _enrich_web_query(query: str, conversation_history: list) -> str:
    """Rewrite the web search query to be self-contained using conversation context."""
    if not conversation_history:
        return query
    history_lines = []
    for turn in conversation_history:
        role = "User" if turn.get("role") == "user" else "Assistant"
        history_lines.append(f"{role}: {turn.get('content', '')[:400]}")
    history_text = "\n".join(history_lines)
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Given a conversation and a follow-up query, rewrite the query to be "
                        "self-contained and specific for a web search. Keep it under 10 words. "
                        "Preserve specific terms, acronyms, and named entities from prior context exactly as used. "
                        "Return ONLY the rewritten query, no explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Conversation:\n{history_text}\n\nFollow-up query: {query}\n\nRewritten query:",
                },
            ],
            options={"temperature": 0},
        )
        rewritten = response.message.content.strip()
        return rewritten if rewritten else query
    except Exception:
        return query


def generate_web_answer(state: SearchState) -> dict:
    """Generate answer from web search."""
    conv_history = state.get("conversation_history") or []
    search_query = _enrich_web_query(state["normalized_query"], conv_history) if conv_history else state["normalized_query"]
    result = web_search(
        search_query,
        max_results=5,
        conversation_history=conv_history,
    )

    # web_search returns (answer, result_count, tokens_in, tokens_out)
    if isinstance(result, tuple) and len(result) == 4:
        answer, result_count, tokens_in, tokens_out = result
    elif isinstance(result, tuple) and len(result) == 2:
        # Backward compatibility with old 2-tuple format
        answer, result_count = result
        tokens_in, tokens_out = 0, 0
    else:
        # Fallback for other return types
        answer = result
        result_count = tokens_in = tokens_out = 0

    # web_was_fallback = True if we got here because internal failed, not explicit web
    was_fallback = not state.get("explicit_web_detected", False)

    return {
        "web_answer": answer or None,
        "web_succeeded": bool(answer),       # True only if answer has content
        "web_result_count": result_count,
        "web_was_fallback": was_fallback,
        "final_output": answer or None,
        "total_llm_tokens_in": tokens_in,
        "total_llm_tokens_out": tokens_out,
    }


# ============================================================================
# Conditional routing functions
# ============================================================================

def route_after_retrieval(state: SearchState) -> Literal["web_search", "judge_gate"]:
    """Route based on retrieval quality."""
    if not state.get("chunks_passed_threshold"):
        return "web_search"
    return "judge_gate"


def route_after_judge(state: SearchState) -> Literal["web_search", "generate_answer"]:
    """Route based on judge score."""
    score = int(state.get("judge_score") or 0)
    if score < JUDGE_SCORE_THRESHOLD:
        return "web_search"
    return "generate_answer"


def route_after_generate(state: SearchState) -> Literal["web_search", Literal[END]]:
    """Route based on whether answer generation succeeded."""
    if state.get("internal_no_content_response"):
        return "web_search"
    return END


# ============================================================================
# Graph construction
# ============================================================================

def build_graph():
    """Build and compile the search graph."""
    graph = StateGraph(SearchState)

    # Add nodes
    graph.add_node("query_normalize", query_normalize)
    graph.add_node("index_sync", index_sync)
    graph.add_node("detect_explicit_web", detect_explicit_web)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("llm_only", generate_llm_answer)
    graph.add_node("internal_retrieve", internal_retrieve)
    graph.add_node(
        "judge_gate",
        judge_gate,
        retry=RetryPolicy(max_attempts=3)
    )
    graph.add_node(
        "generate_answer",
        generate_answer,
        retry=RetryPolicy(max_attempts=2)
    )
    graph.add_node(
        "web_search",
        generate_web_answer,
        retry=RetryPolicy(max_attempts=3)
    )

    # Add edges
    graph.add_edge(START, "query_normalize")
    graph.add_edge("query_normalize", "index_sync")
    graph.add_edge("index_sync", "detect_explicit_web")
    graph.add_conditional_edges("detect_explicit_web", route_explicit_web)
    graph.add_conditional_edges("classify_intent", route_after_intent)
    graph.add_conditional_edges("llm_only", route_after_llm_only)
    graph.add_conditional_edges("internal_retrieve", route_after_retrieval)
    graph.add_conditional_edges("judge_gate", route_after_judge)
    graph.add_conditional_edges("generate_answer", route_after_generate)
    graph.add_edge("web_search", END)

    return graph.compile()
