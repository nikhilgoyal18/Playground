# AI Playground

A workspace for independent AI-powered projects. Each subfolder is a self-contained project with its own CLAUDE.md and tools.

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

## Auto-invoke Skills

| Natural language intent | Skill to invoke |
|------------------------|-----------------|
| newsletters, newsletter digest, newsletter scan, latest newsletters, summarize newsletters, "give me today's newsletters" | `newsletter-insights` |
| twitter, tweet digest, tweet scan, latest tweets, summarize tweets, twitter timeline, "give me today's tweets" | `twitter-insights` |
| reddit problems, scan reddit, reddit insights, market research reddit, reddit pain points, what problems on reddit, reddit opportunities | `reddit-problems` |
| research reddit problems, deep dive reddit, analyze reddit opportunities, find solutions for reddit problems | `reddit-research` |
| search my digests, ask me about, find articles about, what have I read about, look up in my summaries, have I read anything about, chat with my knowledge base, ask my digests | `ai-chatbot` |
| questions and answers, let's do Q&A, Q&A session, generate interview questions, add to questions and answers, interview prep from this | `qa-session` |

## AI Chatbot Evaluation & Quality

See **`ai-chatbot/eval/METRICS_AND_GUARDRAILS.md`** for:
- **11 evaluation metrics** (routing correctness, source precision, judge score quality, latency, token usage, etc.)
- **15 guardrails** (distance threshold, judge gate, keyword bypass, intent classifier, conversation cap, input validation, etc.)
- **Baseline metrics** from 2026-04-06 evaluation (76-80% pass rate, judge scores, path distribution)
- **4 historical bugs** with root causes and fixes
- **SQL audit trail queries** for inspecting production data

Current status: ~76-80% pass rate on 71 test cases. Target: ≥95%.

## Adding a New Project

1. Create a new subfolder under `Playground/`
2. Add a `CLAUDE.md` describing the project's purpose and tools
3. Add an entry to the Projects table above
4. Optionally create a skill in `.claude/skills/`
