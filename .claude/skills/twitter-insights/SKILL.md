---
description: >
  Scan Twitter/X home timeline for new tweets and produce a DEEP, insight-rich digest.
  Extract strategic implications, competitive context, and cross-account patterns.
  CRITICAL: Must include 3-4 specific insights per tweet (not paraphrases).
  Use when the user asks for twitter insights, tweet digest, latest tweets,
  or anything about scanning/reading/summarizing their Twitter timeline.
  Trigger phrases: "twitter digest", "scan tweets", "latest tweets",
  "today's tweets", "what's on my twitter", "twitter timeline", "twitter insights",
  "tweet summary", "show me my twitter feed", "give me today's twitter scan".
allowed-tools: Bash(python3 fetch_tweets.py*), Write, Read
---

# Twitter Insights — DEEP DIGEST

Scan the Twitter/X home timeline for new tweets and produce a **strategic, insight-rich digest**.

⚠️ **CRITICAL QUALITY GATE:** This skill produces digests for decision-making, not curiosity. Every bullet point must contain an actionable insight, not a paraphrase.

## Steps

1. Change into the `twitter-insights/` directory (relative to the Playground root).

2. Run the fetcher:
   ```bash
   python3 fetch_tweets.py
   ```
   This outputs a JSON array of new tweets to stdout and updates `data/scanned.json`. If it exits with an auth error, remind the user to refresh their cookies as described in `twitter-insights/CLAUDE.md`.

3. Parse the JSON output. Each item has:
   - `id` — tweet ID
   - `author_username` — Twitter handle
   - `author_name` — display name
   - `text` — tweet text
   - `created_at` — timestamp
   - `like_count`, `retweet_count`, `reply_count` — engagement metrics

4. If the array is empty, respond:
   > No new tweets since the last scan. Check back later.

5. Otherwise, produce a digest using these **strict rules**:

   ### Filtering Rules
   - **Skip low-signal:** pure link shares, one-word reactions, puzzle answers, deals without context
   - **Skip low-engagement:** tweets with total engagement < 3 UNLESS the account is known expert (Garry Tan, Chamath, etc.) or content is clearly high-signal
   - **Keep only substantive:** tweets that contain a claim, observation, or insight worth extracting

   ### Grouping by Account
   - Group all tweets from same account under one `##` heading
   - Use author's display name as heading, with handle in parentheses: `## Name (@handle)`
   - Include primary topic tag for account: `## Name (@handle) `AI/ML``
   - Sort sections by **number of substantive tweets** (most prolific first)
   - Include count: `*N substantive tweets*`

   ### Per-Tweet Analysis (CRITICAL SECTION)
   
   **Title creation:**
   - Create a **descriptive title that signals the strategic insight**, not a quote from the tweet
   - ❌ Bad: "When your working life rewards you..." (copy-paste)
   - ✅ Good: "Complexity-time tradeoff as operational risk" (insight-focused)
   - Include topic tag: `### Title `Topic``
   
   **Bullet point requirements (MANDATORY - NO EXCEPTIONS):**
   - Write **3-4 bullets per tweet minimum** (not 1-2)
   - **Each bullet must contain a specific insight, not a paraphrase**
   - **Interpretation rule:** For each tweet, answer these questions in bullets:
     1. What is the core claim or observation?
     2. What does it imply strategically or competitively?
     3. What specific data/names/numbers/frameworks does it mention?
     4. Who should act on this, and why?
   
   **Content standards:**
   - Include specifics: company names, exact numbers, frameworks, percentages, valuations
   - Extract implications: "This suggests...", "Implication:", "Means that...", "Supports thesis that..."
   - Note competitive context: market trends, investor sentiment, positioning shifts
   - Flag decision relevance: How would a founder, investor, or product leader use this?
   
   **Example (CORRECT):**
   ```
   ### Cybertruck production validates hardware-software integration `Product`
   - Elon claims Cybertruck is Tesla's best product ever made — suggests confidence in production quality and design validation
   - "Until you've tried it out, you have no idea, because there's nothing like it" implies the design is so novel that prior frame-of-reference is insufficient
   - Engagement (43K) suggests strong consumer interest; success would validate Tesla's vertical integration model
   - Implication: Integrated EV platforms (hardware + energy + software) outperform traditional auto competitors
   ```
   
   **Example (WRONG - WILL BE REJECTED):**
   ```
   ### Cybertruck is awesome
   - Cybertruck is awesome
   - 43,000 engagement
   ```

   ### Cross-Account Synthesis
   - **Add a "Summary Themes" section at the end**
   - List 3-5 major themes that appear across multiple accounts
   - Flag when 2+ accounts independently mention the same insight = **market consensus forming**
   - Include brief explanation of why the pattern matters
   
   **Example:**
   ```
   ## Summary Themes
   
   1. **AI commoditization acceleration** — Chamath, Garry Tan, Forbes independently messaging that AI is displacing knowledge work; market consensus forming
   2. **Open source as competitive moat** — Multiple voices positioning local-first, open-weight models as superior to API-dependent systems
   3. **Valuation divergence signals thesis shift** — Anthropic up 84%, OpenAI down 12%; investors repricing from "bigger = better" to "efficient + safe = defensible"
   ```

6. Write the digest to `summaries/YYYY-MM-DD.md` using today's date. Format:

```markdown
# Twitter Digest — YYYY-MM-DD

> N substantive tweets from M accounts. Extracted strategic insights about [theme1, theme2, theme3].

---

## [Display Name] (@handle) `[Primary Tag]`
*N substantive tweets*

### [Insight-Driven Title] `[Topic Tag]`
- Core claim or observation with strategic context
- Specific implication or what this means competitively
- Named entities, numbers, frameworks referenced
- Decision relevance: who should act on this and why

### [Another Insight-Driven Title] `[Topic Tag]`
- ...

---

## [Next Account]
...

---

## Summary Themes

1. **Theme 1** — How it appears across accounts, why it matters
2. **Theme 2** — ...
```

### Quality Checklist (BEFORE SUBMITTING)
- [ ] No tweet is represented by fewer than 3 bullets
- [ ] No bullet is a paraphrase of tweet text
- [ ] Every bullet contains specific insight (implication, context, or data)
- [ ] Company names, numbers, percentages are explicitly stated
- [ ] Cross-account patterns are synthesized in Summary Themes
- [ ] Titles signal strategic insight, not quote tweet text
- [ ] Decision relevance is clear ("Implication:", "Matters for:", etc.)
- [ ] Engagement counts are contextualized (e.g., "43K engagement suggests X")

7. Display the digest to the user and mention the file it was saved to.

---

## Reference Material

See `twitter-insights/DIGEST_QUALITY_IMPROVEMENT.md` for before/after examples and the exact standards this skill must follow. Non-negotiable.
