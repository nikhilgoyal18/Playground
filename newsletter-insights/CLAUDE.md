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
