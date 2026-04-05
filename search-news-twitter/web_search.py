"""
Web search agent using DuckDuckGo and Ollama LLM.
Retrieves live web results and summarizes them for the user.
"""

import ollama
from ddgs import DDGS

OLLAMA_MODEL = "llama3.2"

WEB_SYSTEM_PROMPT = """You are a web search assistant. Answer the user's question using ONLY the web search results provided below.
- Cite sources inline using [Source N] notation matching the result headers.
- Be concise and synthesize across sources when relevant.
- If the results do not contain enough information to answer the question, say: "The search results don't contain enough information to answer this question."
- Do not fabricate information not present in the results."""


def web_search(query, max_results=5):
    """
    Search the web using DuckDuckGo and summarize results with Ollama.

    Args:
        query: User's search query
        max_results: Number of web results to retrieve (default: 5)
    """
    try:
        results = list(DDGS().text(query, max_results=max_results))
    except Exception as e:
        print(f"Web search failed: {e}")
        return

    if not results:
        print("No web search results found.")
        return

    # Build context blocks with [Source N] labels
    context_blocks = []
    for i, result in enumerate(results, start=1):
        header = f"[Source {i}] WEB | {result['title']}\nURL: {result['href']}"
        body = result['body']
        context_blocks.append(f"{header}\n{body}")

    context_text = "\n\n---\n\n".join(context_blocks)

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": WEB_SYSTEM_PROMPT},
                {"role": "user", "content": f"Web search results:\n\n{context_text}\n\n---\n\nQuestion: {query}"},
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
    for i, result in enumerate(results, start=1):
        print(f"  [{i}] {result['title']}")
        print(f"      {result['href']}")
