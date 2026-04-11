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

Core user-facing skills auto-triggered by natural language intent:

| Natural language intent | Skill to invoke |
|------------------------|-----------------|
| newsletters, newsletter digest, newsletter scan, latest newsletters, summarize newsletters, "give me today's newsletters" | `newsletter-insights` |
| twitter, tweet digest, tweet scan, latest tweets, summarize tweets, twitter timeline, "give me today's tweets" | `twitter-insights` |
| reddit problems, scan reddit, reddit insights, market research reddit, reddit pain points, what problems on reddit, reddit opportunities | `reddit-problems` |
| research reddit problems, deep dive reddit, analyze reddit opportunities, find solutions for reddit problems | `reddit-research` |
| search my digests, ask me about, find articles about, what have I read about, look up in my summaries, have I read anything about, chat with my knowledge base, ask my digests | `ai-chatbot` |
| questions and answers, let's do Q&A, Q&A session, generate interview questions, add to questions and answers, interview prep from this | `qa-session` |

Additional skills for reviewers, evaluators, and utilities are invoked by explicit command.

## AI Chatbot Quality

See **`ai-chatbot/eval/METRICS_AND_GUARDRAILS.md`** for evaluation metrics, guardrails, baseline results, and historical bugs.

