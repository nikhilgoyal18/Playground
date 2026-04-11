# Newsletter Insights

Connects to Gmail and surfaces what's worth learning from newsletters — organized by topic, on demand.

## How It Works

Run `/newsletter-insights` from the Playground root. Claude will:
1. Execute `scan_newsletters.py` to fetch new newsletters from Gmail
2. Classify each one by topic
3. Write a digest to `summaries/YYYY-MM-DD.md`

Only emails not previously scanned are processed. State is tracked in `data/scanned.json`.

## One-Time Setup

Before the first run, complete these steps:

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Google Cloud credentials
1. Go to [console.cloud.google.com](/) and create a project
2. Navigate to **APIs & Services → Library** → enable **Gmail API**
3. Go to **APIs & Services → OAuth consent screen**:
   - User type: External
   - Add scope: `https://www.googleapis.com/auth/gmail.readonly`
4. Go to **APIs & Services → Credentials**:
   - Create credentials → **OAuth client ID** → Desktop application
   - Download JSON → save as `credentials.json` in this folder

### 3. Authenticate
```bash
python scan_newsletters.py --auth
```
A browser window opens. Sign in with your Google account and grant access. This creates `token.json` which is reused on future runs.

## Files

| File | Purpose |
|------|---------|
| `scan_newsletters.py` | Queries Gmail API, outputs new newsletters as JSON |
| `credentials.json` | OAuth client credentials (never commit this) |
| `token.json` | Cached auth token (never commit this) |
| `data/scanned.json` | Tracks already-processed email IDs |
| `summaries/` | Generated digests saved as `YYYY-MM-DD.md` |

## Newsletter Detection

The script filters emails using Gmail query `from:@substack.com OR subject:newsletter`, which catches Substack publications and any email with "newsletter" in the subject line.

## Digest Quality Standards

Digests must be **comprehensive and learnable**—readers should gain actionable knowledge, not just headlines.

### Content Depth
- **Extract 10-12+ bullets per issue minimum** (not just 6-8). Each substantive newsletter deserves thorough coverage
- **Include exact numbers**: metrics, valuations, growth rates, percentages, thresholds (e.g., "$11B," "3.9x YoY," "3-to-1 minimum ratio")
- **Name concrete examples**: companies, products, frameworks, people (e.g., "Harvey," "Nick Chasinov," "Drata's 80+ engineers")
- **Provide comparative data**: side-by-side examples, real-world ratios, before/after (e.g., "QuickBooks $10k/yr vs accountant $120k/yr")
- **Quote key insights**: direct quotes when available, exact phrases (e.g., "If CAC > LTV, the business closes its doors")
- **Explain the why**: context, implications, and reasoning (not just facts)
- **Include workflows & mechanics**: step-by-step examples, product mechanics, how things work

### Actionability
- What can the reader do with this knowledge?
- What decisions or strategies does it inform?
- What gaps or opportunities does it highlight?

### What to Skip
- Verification codes, pure notifications, promotional fluff
- Issues with no substantive body content
- Link-only shares with no context

### Quality Check
Bad: "Key architectural patterns discussed"  
Good: "Drata's 80+ engineers achieved 4x more test cases and 86% faster QA cycles using AI-native testing. QA Wolf delivers 80% coverage in weeks with 24-hour maintenance; when CAC exceeds LTV, the business closes—not if, but when."
