# Learning Document: Hybrid Conversation Mode Implementation

**Date:** 2026-04-08  
**Context:** Added multi-turn conversation to AI Chatbot web UI  
**Status:** Shipped and validated  
**Architecture:** Stateless backend, client-owns-history (sessionStorage), conversation-aware answer generation and web query enrichment

---

## Executive Summary

Implemented a hybrid conversation mode where each turn does an independent RAG retrieval but conversation history is injected into answer generation and web query enrichment. The system preserves conversation context across page refreshes using `sessionStorage`, supports clearing chat, and prevents race conditions with input lockout during requests.

**Key outcomes:**
- ✅ Multi-turn conversation with DOM restoration on refresh
- ✅ Context-aware web search via `_enrich_web_query()` LLM rewrite
- ✅ Conversation ID tagging for multi-turn audit trail in SQLite
- ✅ Fixed judge score crash (string/int TypeError)
- ✅ Proper error logging for 500-level failures

---

## Architecture Decision: Hybrid vs. Context-Anchored vs. Generic Chat

### The Question
How should follow-up questions work in a multi-turn RAG system?

### Three Options Evaluated

1. **Context-anchored** — Reuse first query's chunks for all follow-ups
   - Pros: Simple, fast, no re-retrieval
   - Cons: Can't pivot topics; if first retrieval was weak, all follow-ups suffer
   - Verdict: ❌ Too constraining

2. **Fully generic chat** — Each turn is independent, history is just memory
   - Pros: Natural, no friction, works for any topic
   - Cons: RAG becomes secondary to conversation memory; risk of hallucination on out-of-KB topics
   - Verdict: ❌ Defeats the purpose of RAG

3. **Hybrid** — Fresh retrieval per turn, history injected only at answer generation
   - Pros: Every answer grounded in fresh chunks; follow-ups feel coherent; can pivot naturally
   - Cons: More complex; every turn has full retrieval latency
   - Verdict: ✅ **CHOSEN** — Best balance

### Why Hybrid Wins
The whole point of RAG is to stay grounded in indexed content. If you let conversation history dominate, you lose that guarantee. Hybrid keeps every answer anchored while making follow-ups natural.

---

## Design: Stateless Backend, Stateful Client

### Client (sessionStorage)
- Stores two parallel structures:
  - `snt_conv_history` — plain `[{role, content}, ...]` for backend (capped at 6 entries before sending)
  - `snt_conv_messages` — full metadata for DOM restoration (sources, judge score, path, tokens, duration)
  - `snt_conv_id` — UUID per session for multi-turn tracing

### Backend (app.py)
- Validates `conversation_history` on every request
  - Checks structure (list of dicts with `role` and `content`)
  - Silently drops malformed entries, logs warning
  - Server-side cap at 6 entries (defense in depth)
- Passes history and ID through to graph state
- Includes ID in SQLite logs

### Graph (graph.py)
- History injected **only at answer generation**, not at retrieval/routing/judging
- Each turn still does fresh RAG independently

### Key Learning
Stateless backend scales better and is simpler to reason about. The client is responsible for state persistence. Browser's `sessionStorage` is perfect for this — outlives `Cmd+R` but dies on tab close (intentional scoping).

---

## Implementation Details

### 1. sessionStorage vs. JS Memory

**Why sessionStorage?**
- Raw JS array loses on page refresh
- `sessionStorage` persists within a tab session
- Survives `Cmd+R`; dies when tab closes (proper scoping)
- No server-side session to manage

**Issue found:** Restored messages had no metadata (sources, log UI). Fixed by storing full message objects in separate key `snt_conv_messages`.

### 2. History Capping

**Why 6 entries (3 exchanges)?**
- LLM prompts grow with each turn; no bound = prompt overflow
- Recent context is most relevant for coherent follow-ups
- 3 exchanges covers most follow-up patterns
- Tested: 6 entries = ~200 tokens overhead (acceptable)

**Where it's capped:**
- Client: Before each POST (slices to last 6)
- Server: On receipt (second cap, defense in depth)

### 3. Query Enrichment for Web Search

**The Problem:** "Tell me more about MCP" without context goes to DuckDuckGo ambiguously. MCP could mean:
- Model Context Protocol (from first turn)
- Microsoft Certified Professional (generic web interpretation)

**The Solution:** `_enrich_web_query()` function
```python
def _enrich_web_query(query, conversation_history):
    # Use Ollama to rewrite the query to be self-contained
    # "Tell me more about MCP" + prior context → "Model Context Protocol implementation details"
    # Temperature=0 for deterministic rewriting
```

Only runs when conversation history is non-empty. Ensures web searches stay consistent with the knowledge base context.

### Key Learning
Web search is vulnerable to ambiguity. Without enrichment, follow-up queries silently diverge into different topics. A single LLM rewrite (temperature=0) solves this elegantly.

---

## Bugs Fixed During Implementation

### Bug #4: Judge Score String/Int TypeError

**The Problem:** 
Graph crashed with `TypeError: '<' not supported between instances of 'str' and 'int'` on certain queries, returning 500 to the user with no DB log.

**Root Cause:**
Judge LLM occasionally returns `"intent_score": "8"` (string) instead of `"intent_score": 8` (int). The routing logic did `score < 5` — comparing string to int — which Python 3 forbids.

**The Fix:**
Cast to `int()` at **both** the storage and comparison points:
- `judge_gate`: `"judge_score": int(verdict["intent_score"])`
- `route_after_judge`: `score = int(state.get("judge_score") or 0)`

**Why Two Places?**
Defense in depth. If only at storage, existing string rows in DB would break future reads. If only at comparison, DB stores strings. Both sites are protected.

### Key Learning
Never trust LLM JSON field types. Always cast immediately upon extraction, regardless of prompt instructions. The LLM may return `"8"` even if you ask for 8.

---

## UX Details

### Conversation Active Badge
Subtle indicator in header showing conversation is not at first turn. Disappears after "Clear chat". Helps users understand what context is active.

### Input Lockout During Requests
Send button + input disabled while awaiting response. Prevents race conditions from rapid multi-submit and reduces confusion about concurrent requests.

### DOM Restoration on Refresh
`restoreChat()` reconstructs messages from `sessionStorage` on page load, including full metadata. User doesn't see a blank chat after refresh.

### Clear Chat Button
Resets:
- sessionStorage history and conv_id
- DOM chat container
- Conversation active badge
- Next question starts fresh with new UUID

---

## Logging & Observability

### SQLite Schema Change
Added `conversation_id TEXT` column to `searches` table.

**Migration:** Automatic in `init_db()` — `ALTER TABLE ADD COLUMN` skips silently if already present (safe for existing DBs).

**Usage:** Trace full conversation:
```sql
SELECT id, timestamp, query, judge_score, path
FROM searches
WHERE conversation_id = 'uuid-here'
ORDER BY id
```

### New Troubleshooting
- Check `/tmp/snt_server.log` for 500 errors (traceback logging added)
- Query multi-turn conversations: group by `conversation_id`
- Verify history is persisted: browser DevTools → Application → Session Storage

---

## Token & Performance Considerations

### Token Overhead
- History injection: ~200 tokens per turn (6 entries max)
- Query enrichment: ~100 tokens per web search (LLM rewrite)
- Acceptable for multi-turn; doesn't degrade latency noticeably

### Latency Impact
- Web query enrichment adds 1-2 seconds (new Ollama call before DuckDuckGo)
- Only happens on web fallback path, not on internal hits
- No impact on direct internal retrieval path

---

## Key Learnings

### 1. Conversation History Belongs on the Client
Server session management is a liability. Let the client own state and send it on every request. Simpler, more stateless, easier to reason about.

### 2. Inject History Only at Answer Generation
Don't let it influence retrieval, routing, or judging. Each RAG turn should be independent. Only use history to make the final answer coherent.

### 3. Web Queries Need Context Enrichment
Ambiguous follow-ups ("tell me more about X") diverge without enrichment. A single temperature=0 LLM rewrite solves this cheaply.

### 4. Defense in Depth for User Input
Validate on both client and server. Cap history in both places. Cast numeric fields at extract time AND at use time. Users will find edge cases.

### 5. Conversation Metadata Must Be Separate from History
History for backend (text only, capped) vs. messages for DOM (full metadata). Two keys in sessionStorage are cleaner than one overloaded blob.

### 6. Refresh Recovery is Critical
Users hit `Cmd+R` mid-conversation. DOM restoration from sessionStorage is table stakes, not a nice-to-have. Without it, users feel like data is lost.

---

## What Went Wrong & Fixed

1. **First attempt:** History lost on refresh
   - Fix: Switched to `sessionStorage` + DOM restoration

2. **Second attempt:** Restored messages had no sources/log UI
   - Fix: Store full metadata in separate sessionStorage key

3. **Third attempt:** 500 crash on second query in conversation
   - Root cause: Judge score string/int comparison
   - Fix: Cast to int() at both storage and comparison

4. **Fourth attempt:** Web search diverged to wrong topic
   - Root cause: No query enrichment with context
   - Fix: `_enrich_web_query()` before DuckDuckGo

---

## Comparison to Other Approaches

### Approach A: Session Cookies + Backend State
- Pros: Works with HTTP-only cookies, more traditional
- Cons: Requires server-side session storage, scaling issue, more complex
- Rejected: ❌

### Approach B: JWT Token with Conversation Embedded
- Pros: Stateless, compact
- Cons: Token size grows with history, security questions (client sending state)
- Rejected: ❌

### Approach C: localStorage Instead of sessionStorage
- Pros: Persists across tab close
- Cons: Conversation stays after user closes browser (privacy issue)
- Rejected: ❌

### Our Approach: sessionStorage (Client-owned, Validated, Capped)
- Pros: Stateless, validated, scoped to tab, simple
- Cons: None identified
- Chosen: ✅

---

## Recommendations for Future Work

### Short Term
- [ ] Add UI indicator showing how many prior turns are in active context (e.g., "last 3 of 7 messages")
- [ ] A/B test history cap (currently 6 entries; could be 4 or 8)
- [ ] Monitor query enrichment success rate (is it staying on-topic?)

### Medium Term
- [ ] Sliding window of visible history vs. sent history (show all 20 messages, send last 6 to backend)
- [ ] Query enrichment caching (if same follow-up, reuse enriched query)
- [ ] Per-conversation settings (e.g., "lock to internal only" mode)

### Long Term
- [ ] Multi-session history (browse across past conversations)
- [ ] Export conversation as markdown
- [ ] Conversation tagging and search
- [ ] Analytics on conversation length, fallback rate, etc.

---

## Code Changes Summary

| File | Changes | Lines |
|------|---------|-------|
| `templates/index.html` | sessionStorage history + DOM restoration + UI | +80 |
| `app.py` | Validate & cap history, pass to state | +20 |
| `graph.py` | Inject history at generation, add query enrichment, cast judge score | +50 |
| `web_search.py` | Accept history param, inject at summarization | +10 |
| `logger.py` | Add conversation_id column, migrate DB | +10 |
| **Total** | | **~180 lines** |

**Risk Level:** LOW  
**Backward Compatible:** ✅ YES (new column nullable, new fields optional in state)

---

## Conclusion

Hybrid conversation mode successfully balances RAG grounding with multi-turn naturalness. Stateless backend with client-owned sessionStorage is simple and scales well. Query enrichment keeps web searches on-topic. The one crash (judge score typing) is a reminder to never trust LLM JSON field types.

The system is production-ready for multi-turn usage. Next focus: UI polish (context indicator) and monitoring (conversation analytics).
