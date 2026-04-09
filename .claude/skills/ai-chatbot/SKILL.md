---
description: >
  Semantic search and Q&A across all indexed digests using RAG (ChromaDB + Claude).
  Use when the user wants to search their digests, ask questions about past content,
  or look up what they've read about a specific subject.
  Trigger phrases: "search my digests", "search newsletters and twitter", "find articles about",
  "what have I read about", "search news twitter", "look up in my summaries",
  "what did newsletters say about", "what did twitter say about", "search my knowledge base",
  "have I read anything about", "find tweets or newsletters about".
allowed-tools: Bash(python3 index.py*), Bash(python3 search.py*), Read
---

# AI Chatbot

Semantic search and Q&A across all indexed digests using RAG.

## Steps

1. Change into the `ai-chatbot/` directory:
   ```bash
   cd /Users/nikhil/Documents/AI/Playground/ai-chatbot
   ```

2. Extract a clean, focused search query from the user's message. If their question is
   implicit (e.g., "what have I read about RAG?"), formulate it as a concise search string
   (e.g., "RAG retrieval augmented generation").

3. Run the search:
   ```bash
   python3 search.py --query "<query>" [--source newsletter|twitter] [--top-k 8] [--date-from YYYY-MM-DD]
   ```

   Optional flags:
   - `--source newsletter` or `--source twitter` — filter to one source type
   - `--top-k N` — number of chunks to retrieve (default 5; use 8–10 for broader topics)
   - `--date-from YYYY-MM-DD` — limit to summaries from this date onward

4. The script will:
   - Auto-index any new summary files from both projects before searching
   - Retrieve semantically relevant chunks from ChromaDB
   - Generate a cited answer from Claude using only the retrieved content

5. Display the full answer and source table to the user.

6. If the script reports "No sufficiently relevant content found", tell the user:
   > No relevant content was found in the indexed summaries for that query.
   > Try rephrasing your question, or run `/newsletter-insights` or `/twitter-insights`
   > to add more content to the knowledge base first.

## Troubleshooting

- **"Index is empty"** → Run `python3 index.py` first to build the initial index.
- **"ModuleNotFoundError"** → Run `pip install -r requirements.txt` in the project directory.
- **"ANTHROPIC_API_KEY not set"** → Create a `.env` file with `ANTHROPIC_API_KEY=your_key`.
