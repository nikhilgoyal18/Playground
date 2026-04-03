# AI Playground

A workspace for independent AI-powered projects. Each subfolder is a self-contained project with its own CLAUDE.md and tools.

## Projects

| Project | Folder | Purpose |
|---------|--------|---------|
| Newsletter Insights | `newsletter-insights/` | Scan Gmail newsletters and surface key learnings by topic |

## Global Conventions

- **Skills** live in `.claude/skills/` and are invoked with `/skill-name`
- **Project state** (tracking files, caches) lives in `<project>/data/`
- **Outputs** (summaries, reports) live in `<project>/summaries/` or `<project>/outputs/`
- Never commit `credentials.json`, `token.json`, or `.env` files

## Adding a New Project

1. Create a new subfolder under `Playground/`
2. Add a `CLAUDE.md` describing the project's purpose and tools
3. Add an entry to the Projects table above
4. Optionally create a skill in `.claude/skills/`
