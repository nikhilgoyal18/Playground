"""Validate intent classifier prompt accuracy before implementation."""
import ollama
from test_cases import TEST_CASES

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

PERSONAL_PATHS = {"internal", "web_fallback", "explicit_web", "web"}
GENERAL_PATHS = {"llm_only"}

correct = 0
wrong = []
general_hits = 0
for tc in TEST_CASES:
    expected_intent = "GENERAL" if tc["expected_path"] in GENERAL_PATHS else "PERSONAL"
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": INTENT_CLASSIFIER_PROMPT},
            {"role": "user", "content": tc["query"]},
        ],
        options={"temperature": 0},
    )
    raw = response.message.content.strip().upper()
    actual = raw if raw in ("GENERAL", "PERSONAL") else "PERSONAL"
    ok = actual == expected_intent
    if ok:
        correct += 1
    if actual == "GENERAL":
        general_hits += 1
    if not ok:
        wrong.append((tc["id"], tc["query"], expected_intent, actual))

print(f"\nAccuracy: {correct}/{len(TEST_CASES)} ({100*correct/len(TEST_CASES):.1f}%)")
print(f"GENERAL hit rate: {general_hits}/{len(TEST_CASES)} ({100*general_hits/len(TEST_CASES):.1f}%) — latency overhead indicator")
print(f"\nFailed ({len(wrong)}):")
for id_, q, exp, got in wrong:
    print(f"  [{id_}] expected={exp} got={got}  '{q}'")
