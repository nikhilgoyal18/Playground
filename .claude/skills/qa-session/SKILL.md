---
description: >
  Generate high-quality interview Q&A entries grounded in the work you just completed.
  Extracts technical tradeoffs, measurements, and architecture decisions from your recent implementation,
  then creates interview-style questions and answers using the "good answer" framework.
  Appends entries to learning/questions_and_answers.md with sequential numbering (Q2, Q3, etc).
  
  Trigger phrases: "questions and answers", "let's do Q&A", "Q&A session", "generate interview questions", 
  "add to questions and answers", "interview prep from this", "let's do questions and answers based on this"
allowed-tools: Read, Write, Bash(git log*), Bash(git diff*), Bash(git show*)
---

# QA Session

Generate interview-level questions from recent project experience and append them to your learning repository.

## Steps

### Step 1 — Determine the next question number

Read `learning/questions_and_answers.md` to find the highest question number already in the file.

```bash
head -50 learning/questions_and_answers.md
```

If the file contains Q3, the next question is Q4. If it contains Q1, the next is Q2.

### Step 2 — Understand what was just built

Run:
```bash
git log --oneline -15
```

to see recent commits. Use the commit messages and what the user described in their request to identify what was implemented (e.g., "evaluation harness", "chunking strategy", "judge gate", "conversation mode").

If the user explicitly described what they built in their message, use that as the primary context. Otherwise, infer from git log.

### Step 3 — Extract technical details

Read the relevant source files to extract:
- **Specific numbers:** latency in ms, pass rates (%), token counts, chunk counts, accuracy improvements
- **Before/after states:** what was the system state before the change, after the change
- **Architecture decisions:** why this approach vs alternatives
- **Tradeoffs:** what was traded off (accuracy, latency, tokens, complexity) and at what cost
- **Measurement methodology:** how you verified the improvement

**Common files to read based on what was built:**
- `ai-chatbot/graph.py` — for routing, judge gate, LLM decisions
- `ai-chatbot/eval/run_eval.py` — for evaluation metrics, pass rates, latency
- `ai-chatbot/index.py` — for chunking strategy, embedding details
- `ai-chatbot/CHUNKING_STRATEGY.md` — for chunk design decisions
- `learning/2026-04-06_RAG_Evaluation_Journey.md` — for context on previous decisions
- `ai-chatbot/CLAUDE.md` — for system overview
- Recent git commits and diffs with `git show <commit_hash>`

Extract exact measurements, not vague summaries. Example:
- ✓ "Pass rate jumped from 41.7% (5/12) to 75% (9/12)"
- ✗ "Things improved a lot"

### Step 4 — Generate 3–5 high-quality Q&A pairs

For each question, follow the "good answer" framework:

**Answer structure:**
1. **Open with the concrete situation** — explain what system you were building and what problem you faced (1–2 paragraphs)
2. **State the problem with numbers** — e.g., "pass rate was 41.7%", "latency jumped from 80ms to 350ms"
3. **Show the investigation** — walk through how you diagnosed the issue, what data informed your decision
4. **State the decision with measured cost and benefit** — what you changed, why, and quantify the tradeoff:
   - Latency impact (before vs after in ms)
   - Accuracy impact (before vs after in % or count)
   - Cost or resource impact (tokens, storage, complexity)
   - Product impact (functionality gained or preserved)
5. **End with "When I'd flip this decision"** — describe the conditions under which you'd reverse the choice (scale, new constraints, business changes)

**What to avoid (these are "bad answers"):**
- Vague language ("it was faster", "quality improved")
- No numbers or measurements
- No architecture or implementation detail
- No reasoning framework (how did you decide between options?)
- Unsubstantiated claims ("things improved after launch")

**Question themes** (pick angles like these):
- Technical tradeoffs: accuracy vs latency, cost vs quality, simplicity vs capability
- Debugging and root cause analysis: how you identified a problem and fixed it
- Architecture decisions: why this design over alternatives
- Evaluation and measurement: how you know if something works
- Scaling challenges: what breaks at larger scale and how to handle it

### Step 5 — Append to `learning/questions_and_answers.md`

Format each new Q&A pair using this template:

```markdown
---

## Q[N]: [Question Title]

**Question:** [Full question text, phrased as an interview question]

**Context:** [Which project/system/feature the answer draws from, e.g., "AI Chatbot RAG system"]

**Answer:**

[Your detailed answer following the good answer framework above. Start with the concrete situation,
state the problem with numbers, show your investigation and decision-making process,
quantify the tradeoff, and end with when you'd flip the decision.]

---
```

**Important:** Append to the file, do NOT overwrite. Insert the new entries before the final blank line if one exists.

Use the exact same formatting, spacing, and style as Q1 in the file (Markdown H2 for question, bold labels for Question/Context/Answer, H3 for major sub-sections within the answer, `**bold**` for inline headers like "**The Problem:**" and "**Why I chose this:**", horizontal rules `---` to separate major concepts).

### Step 6 — Report to user

Display:
- A summary: "Added Q2–Q4 (3 new questions)" or similar
- A one-line summary of each new question, e.g.:
  - "Q2: Judge determinism (temperature setting vs evaluation consistency)"
  - "Q3: Chunking granularity (semantic precision vs retrieval latency)"
  - "Q4: How to measure quality in a single-user system"
- The file path: `learning/questions_and_answers.md`

Example:

> Added Q2–Q4 to your learning repository.
> 
> - **Q2:** Why F1 score is wrong for single-user RAG systems (and what metrics matter instead)
> - **Q3:** Debugging non-deterministic LLM outputs in evaluation harnesses
> - **Q4:** How to choose between embeddings models (speed vs quality tradeoff)
> 
> Saved to: `learning/questions_and_answers.md`
