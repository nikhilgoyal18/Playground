# Twitter Insights

Connects to Twitter/X and surfaces what's worth learning from the accounts you follow — organized by topic, on demand.

## How It Works

Run `/twitter-insights` from the Playground root. Claude will:
1. Execute `fetch_tweets.py` to fetch new tweets from your home timeline
2. Classify each one by topic
3. Write a digest to `summaries/YYYY-MM-DD.md`

Only tweets not previously seen are processed. State is tracked in `data/scanned.json`.
Retweets are skipped — only original tweets are included.

## One-Time Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Get your cookies
1. Open [twitter.com](https://twitter.com) in your browser and make sure you're logged in
2. Open **DevTools** (F12 or Cmd+Option+I)
3. Go to **Application** → **Cookies** → `https://twitter.com`
4. Find and copy the **Value** of two cookies: `auth_token` and `ct0`

### 3. Create the .env file
Create a file called `.env` in this folder (`twitter-insights/.env`) with this content:
```
AUTH_TOKEN=paste_auth_token_here
CT0=paste_ct0_here
```

### 4. Verify it works
```bash
python3 fetch_tweets.py --auth-check
```
You should see: `Auth check passed — cookie is valid.`

## Cookie Refresh

The `auth_token` cookie typically stays valid for weeks to months. If you see an auth error, just repeat steps 2–4 above with a fresh cookie value.

## Files

| File | Purpose |
|------|---------|
| `fetch_tweets.py` | Fetches home timeline via twikit, outputs new tweets as JSON |
| `.env` | Stores your `AUTH_TOKEN` cookie (never commit this) |
| `data/scanned.json` | Tracks already-processed tweet IDs |
| `summaries/` | Generated digests saved as `YYYY-MM-DD.md` |
