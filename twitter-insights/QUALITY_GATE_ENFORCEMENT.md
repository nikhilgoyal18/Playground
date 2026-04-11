# Twitter Digest Quality Gate Enforcement

**Status:** ACTIVE (2026-04-11)  
**Penalty for shallow digests:** Will not be permitted.

---

## The Problem (What We Fixed)

Previous Twitter digests were **too shallow** — they just copied tweet text as bullets with minimal interpretation. Result: not actionable for decision-making.

**Before:**
```
### Cybertruck is so awesome
- Cybertruck is so awesome. Until you've tried it out, you have no idea
- 43,000 engagement
```

**After (required now):**
```
### Cybertruck production validates hardware-software integration
- Elon claims Cybertruck is Tesla's best product ever made — suggests confidence in production quality
- Implies Cybertruck design is so novel that prior frame-of-reference is insufficient
- 43K engagement suggests strong consumer interest; validates Tesla's vertical integration thesis
- Implication: If true, supports thesis that integrated EV platforms outperform traditional auto
```

---

## Three-Layer Enforcement System

### Layer 1: Updated Skill Definition (`SKILL.md`)

The skill now includes **explicit, non-negotiable quality standards**:

✅ **Minimum 3-4 bullets per tweet** (not 1-2)  
✅ **Each bullet contains insight** (not paraphrase)  
✅ **Required content per tweet:**
   - Core claim or observation
   - Strategic implication or competitive context
   - Specific data: numbers, company names, frameworks
   - Decision relevance: who should act and why

✅ **Titles signal strategic insight** (not copy-paste quote)  
✅ **Summary Themes section** synthesizes cross-account patterns  
✅ **Quality checklist** before submission

**How this prevents shallow digests:** Any human following the skill MUST include deep insights. The standard is written down and unambiguous.

---

### Layer 2: Automated Validation (`validate_digest.py`)

A Python script that **rejects shallow digests** before they can be committed:

```bash
python3 validate_digest.py summaries/2026-04-11.md
```

**What it checks:**
- ❌ Fewer than 3 bullets per tweet → ERROR
- ❌ Bullets without insight keywords → ERROR
- ❌ Titles that look like paraphrases → ERROR
- ❌ Very short bullets (< 30 chars) without context → ERROR
- ❌ Missing Summary Themes section → ERROR

**Exit code:**
- `0` = PASS (digest meets all standards)
- `1` = FAIL (lists every problem)

**How this prevents shallow digests:** Even if someone ignores the skill standards, the validator catches it and won't allow the commit.

---

### Layer 3: Memory + Feedback (`feedback_twitter_digest_quality.md`)

Captured the user's standards in persistent memory:

- **Rule:** Extract insights (implications, context, specifics), not paraphrases
- **Why:** A digest is only useful if it answers "What does this MEAN?"
- **How to apply:** 3-4 bullets per tweet, each with actionable insight

**How this prevents shallow digests:** Future Claude instances will remember this standard and apply it automatically.

---

## How to Use the Validator

### Before Committing Any Digest

```bash
cd twitter-insights
python3 validate_digest.py summaries/YYYY-MM-DD.md
```

If it returns ✅ PASS, you can commit. If ❌ FAIL, fix the issues listed and re-run.

### Validation Errors Explained

| Error | Fix |
|-------|-----|
| "Only 2 bullets (need ≥3)" | Add 1+ more bullets with specific insights |
| "Bullet too short and lacks insight" | Expand to include implication or specific data |
| "Only 1 insight-rich bullets" | Rewrite bullets to include: implications, context, decisions, specific data |
| "Title looks like paraphrase" | Rename to signal strategic insight ("Validates X", "Disrupts Y", "Signals Z") |
| "No Summary Themes section found" | Add section at end synthesizing cross-account patterns |

### Example Fix

**Failing digest bullet:**
```
- Cloud infrastructure costs are rising
```

**Fixed version:**
```
- OpenAI paused 31,000-GPU UK facility due to 4x electricity costs vs US; capital efficiency becoming critical constraint during pre-IPO runway
```

Why this is better:
- ✅ Named company (OpenAI)
- ✅ Specific number (31,000 GPUs, 4x cost)
- ✅ Market implication (capital efficiency critical)
- ✅ Strategic context (pre-IPO runway)
- ✅ Decision relevance (affects infrastructure strategy)

---

## Integration with Git Workflow

**Recommended pre-commit check:**

Add to your shell alias or pre-commit hook:

```bash
# Before committing twitter-insights changes
python3 twitter-insights/validate_digest.py twitter-insights/summaries/2026-04-11.md || {
    echo "❌ Digest validation failed. Fix issues above and re-run validator."
    exit 1
}
```

This ensures no shallow digest ever gets committed.

---

## Quality Targets

Going forward, **every Twitter digest must:**

| Standard | Metric | Target |
|----------|--------|--------|
| **Depth** | Bullets per tweet | ≥3 minimum |
| **Insight** | % of bullets with implication/context/data | 100% |
| **Specificity** | Named companies, numbers, percentages | All mentioned |
| **Patterns** | Cross-account synthesis (Summary Themes) | Required |
| **Validation** | Pass `validate_digest.py` | All digests |

---

## What Happens If Standards Are Not Met

If a digest is submitted that:
- Has fewer than 3 bullets per tweet, OR
- Contains paraphrases instead of insights, OR
- Lacks specific data, OR
- Fails the validator

**Action:** Digest will be flagged for revision. User can either:
1. Rewrite manually and re-validate, OR
2. Ask Claude to deepen the digest using the validator output as feedback

**Why:** Shallow digests are not valuable for decision-making. The effort to generate them isn't worth it if they're not actionable.

---

## How to Deep-Dive a Digest

If you have a shallow draft, use this prompt with the validator output:

```
The Twitter digest failed validation:
<paste validator errors here>

Please rewrite to pass validation:
- Add 1+ insights bullet to each tweet
- Include competitive context, specific data, decision relevance
- Synthesize cross-account patterns in Summary Themes
- Run python3 validate_digest.py to confirm it passes
```

Claude will then deepen each tweet until it passes.

---

## Reference

- **Skill definition:** `.claude/skills/twitter-insights/SKILL.md`
- **Validator:** `twitter-insights/validate_digest.py`
- **Quality standards:** `twitter-insights/DIGEST_QUALITY_IMPROVEMENT.md`
- **Memory:** `.claude/projects/.../memory/feedback_twitter_digest_quality.md`

---

## Commit History

- `37e4c78` — Implement strict quality gates (validator + skill standards)
- `e57a063` — Deepen April 11 digest with full insights
- `cca36cc` — Document quality improvement standards

All future digests must meet or exceed the April 11 standard (now ✅ passing validator).
