<!-- Created: 2026-01-01 | Updated: 2026-04-27 -->

# AI Playground

A workspace for independent AI-powered projects. Each subfolder is a self-contained project with its own CLAUDE.md and tools.

## Collaboration Rules

1. **No flattery or filler**: Never respond with "good question", "great point", "strong instincts", etc.
2. **Keep priorities clear and work focused**: If session priorities are unclear, ask. Call out ratholing or scope creep and redirect. If a requirement's purpose is unclear, ask why before proceeding.
3. **Push back on poor ideas**: Flag half-baked ideas and explain why. Raise architectural issues, tech debt risk, or skipped concerns before writing code.
4. **Respect the existing architecture**: Before creating a new function, capability, directory, file, or output path, review what already exists and extend it by default vs. building from scratch.
5. **Build it well**: Default to the right way over the easy way, or flag the tradeoff explicitly. Don't overengineer or prematurely abstract, but don't slap things together. If taking a shortcut, say so and explain the tradeoff.

## Projects

| Project | Folder | Purpose |
|---------|--------|---------|
| Newsletter Insights | `newsletter-insights/` | Scan Gmail newsletters and surface key learnings by topic |
| Twitter Insights | `twitter-insights/` | Scan Twitter home timeline and surface key learnings by topic |
| Reddit Insights | `reddit-insights/` | Extract tech problems from subreddits and identify market opportunities |
| AI Chatbot | `ai-chatbot/` | Semantic search and intelligent Q&A across all digests |

## Global Conventions

- **Skills** live in `.claude/skills/` and are invoked with `/skill-name`
- **Project state** (tracking files, caches) lives in `<project>/data/`
- **Outputs** (summaries, reports) live in `<project>/summaries/` or `<project>/outputs/`
- Never commit `credentials.json`, `token.json`, or `.env` files
- **Never delete user-facing data** (logs, databases, interaction history) as a shortcut to fix schema issues. Instead, use targeted `ALTER TABLE` migrations to add missing columns while preserving existing rows. User interactions are valuable data.
- **Documentation MD files** (CLAUDE.md, REFERENCE.md, BUGS.md, METRICS_AND_GUARDRAILS.md, and any other hand-authored docs — not auto-generated digests or summaries) must include the following comment at the very top of the file:
  ```
  <!-- Created: YYYY-MM-DD | Updated: YYYY-MM-DD -->
  ```
  Update the `Updated` date whenever the file is meaningfully changed.

## Auto-invoke Skills

Core user-facing skills auto-triggered by natural language intent:

| Natural language intent | Skill to invoke |
|------------------------|-----------------|
| newsletters, newsletter digest, newsletter scan, latest newsletters, news feed, news, summarize newsletters, "give me today's newsletters" | `newsletter-insights` |
| twitter, tweet digest, tweet scan, latest tweets, twitter updates, twitter feed, summarize tweets, twitter timeline, "give me today's tweets" | `twitter-insights` |
| reddit problems, scan reddit, reddit insights, market research reddit, reddit pain points, what problems on reddit, reddit opportunities | `reddit-problems` |
| research reddit problems, deep dive reddit, analyze reddit opportunities, find solutions for reddit problems | `reddit-research` |
| search my digests, ask me about, find articles about, what have I read about, look up in my summaries, have I read anything about, chat with my knowledge base, ask my digests | `ai-chatbot` |
| questions and answers, let's do Q&A, Q&A session, generate interview questions, add to questions and answers, interview prep from this | `qa-session` |
| any prompt combining multiple intents above (e.g. "news and Twitter", "newsletters and tweets", "today's updates") | invoke ALL matching skills in parallel |

**Multi-intent rule:** When a single prompt matches more than one row above, invoke all matching skills simultaneously in parallel — do not pick just one.

## AI Chatbot Quality

See **`ai-chatbot/eval/METRICS_AND_GUARDRAILS.md`** for evaluation metrics, guardrails, baseline results, and historical bugs.

