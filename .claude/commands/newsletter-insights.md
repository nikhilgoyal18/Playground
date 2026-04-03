---
description: Scan Gmail for new newsletters and produce a topic-grouped learning digest
allowed-tools: Bash(python scan_newsletters.py*), Write, Read
---

# Newsletter Insights Skill

Scan Gmail for new newsletters and produce a topic-grouped learning digest.

## Steps

1. Change into the `newsletter-insights/` directory (relative to the Playground root).

2. Run the scanner:
   ```bash
   python3.14 scan_newsletters.py
   ```
   This outputs a JSON array of new newsletter emails to stdout and updates `data/scanned.json`. If it exits with an error about missing credentials, remind the user to complete the one-time setup described in `newsletter-insights/CLAUDE.md`.

3. Parse the JSON output. Each item has:
   - `id` — Gmail message ID
   - `from` — sender name and email
   - `subject` — email subject line
   - `date` — received date (ISO 8601)
   - `body` — up to 3000 chars of the actual email body text

4. If the array is empty, respond:
   > No new newsletters since the last scan. Check back after more emails arrive.

5. Otherwise, produce a digest using the following rules:

   **Grouping:**
   - Group all issues from the same newsletter/sender under one `##` heading
   - Use the sender's display name (not email address) as the `##` heading
   - Sort sender sections by number of issues in this batch (most prolific first)
   - Skip emails from `no-reply@substack.com` (notification digests, not real newsletters)

   **Per issue:**
   - Each issue gets a `###` subsection: the subject line followed by a topic tag in backticks
   - Topic tags: `AI/ML`, `Engineering`, `Product`, `Business`, `Other`
   - Write 4–6 bullet points of **actual learnings extracted from the body** — not descriptions of what the newsletter is about
   - Include specific details from the body: numbers, percentages, framework names, tool names, step-by-step instructions, quotes, named companies — whatever substantive content is present
   - Skip issues where the body has no real content (e.g., "Listen now (33 mins)" podcast announcements with no transcript)

6. Write the digest to `summaries/YYYY-MM-DD.md` using today's date. Format:

```markdown
# Newsletter Digest — YYYY-MM-DD

> N newsletters scanned across X senders.

---

## [Sender Display Name]
*N issues this period*

### [Subject Line] `[Topic Tag]`
- Specific learning from the body
- Another specific insight with numbers/names if present
- Framework or approach described, named specifically
- Concrete takeaway the reader can act on

### [Another Subject Line] `[Topic Tag]`
- ...

---

## [Next Sender]
...
```

7. Display the digest to the user and mention the file it was saved to.
