#!/bin/bash
# Daily Digest Automation
# Runs at 2 PM via launchd — fetches tweets + newsletters, generates digests, pushes to GitHub

PLAYGROUND="/Users/nikhil/Documents/AI/Playground"
DATE=$(date +%Y-%m-%d)
LOG="$PLAYGROUND/scripts/logs/digest-$DATE.log"

# Explicit paths for launchd (minimal PATH env)
export PATH="/Users/nikhil/.local/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:/usr/bin:/bin"
export HOME="/Users/nikhil"

mkdir -p "$PLAYGROUND/scripts/logs"

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"
}

# Notify on failure
on_error() {
    log "ERROR: Daily digest failed (exit $?)"
    osascript -e 'display notification "Daily digest failed — check scripts/logs/" with title "Playground Automation"' 2>/dev/null || true
}
trap on_error ERR

# Rotate logs older than 30 days
find "$PLAYGROUND/scripts/logs" -name "digest-*.log" -mtime +30 -delete 2>/dev/null || true

log "=== Daily Digest Starting — $DATE ==="

# ─────────────────────────────────────────
# Twitter Pipeline
# ─────────────────────────────────────────
run_twitter() {
    local summary_file="$PLAYGROUND/twitter-insights/summaries/$DATE.md"

    if [ -f "$summary_file" ]; then
        log "[Twitter] Digest already exists for today — skipping (idempotent)"
        return 0
    fi

    log "[Twitter] Fetching tweets..."
    local tweets
    tweets=$(cd "$PLAYGROUND/twitter-insights" && python3 fetch_tweets.py 2>>"$LOG") || {
        log "[Twitter] Fetch failed"
        return 1
    }

    if [ "$tweets" = "[]" ] || [ -z "$tweets" ]; then
        log "[Twitter] No new tweets — skipping"
        return 0
    fi

    local count
    count=$(echo "$tweets" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
    log "[Twitter] Fetched $count tweets — generating digest..."

    local skill
    skill=$(cat "$PLAYGROUND/.claude/skills/twitter-insights/SKILL.md")

    local prompt
    prompt="$(printf 'You are generating a Twitter digest. Follow the formatting rules below EXACTLY.\n\nFORMATTING INSTRUCTIONS:\n%s\n\n---\n\nRAW TWEET DATA (JSON):\n%s\n\n---\n\nIMPORTANT: Output ONLY the complete markdown digest. Start your response with the line "# Twitter Digest — %s" and include nothing before it. No preamble, no explanation, no commentary.' "$skill" "$tweets" "$DATE")"

    local tmp_file
    tmp_file=$(mktemp /tmp/twitter-digest-XXXXXX.md)

    claude -p "$prompt" > "$tmp_file" 2>>"$LOG" || {
        log "[Twitter] claude -p failed"
        rm -f "$tmp_file"
        return 1
    }

    # Validate output starts with a markdown heading
    local first_line
    first_line=$(head -1 "$tmp_file")
    if [[ "$first_line" != "#"* ]]; then
        log "[Twitter] Output validation failed — first line: '$first_line'"
        rm -f "$tmp_file"
        return 1
    fi

    mkdir -p "$(dirname "$summary_file")"
    mv "$tmp_file" "$summary_file"
    log "[Twitter] Digest saved to $summary_file"
    return 0
}

# ─────────────────────────────────────────
# Newsletter Pipeline
# ─────────────────────────────────────────
run_newsletter() {
    local summary_file="$PLAYGROUND/newsletter-insights/summaries/$DATE.md"

    if [ -f "$summary_file" ]; then
        log "[Newsletter] Digest already exists for today — skipping (idempotent)"
        return 0
    fi

    log "[Newsletter] Fetching newsletters..."
    local newsletters
    newsletters=$(cd "$PLAYGROUND/newsletter-insights" && python3.14 scan_newsletters.py 2>>"$LOG") || {
        log "[Newsletter] Fetch failed"
        return 1
    }

    if [ "$newsletters" = "[]" ] || [ -z "$newsletters" ]; then
        log "[Newsletter] No new newsletters — skipping"
        return 0
    fi

    local count
    count=$(echo "$newsletters" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
    log "[Newsletter] Fetched $count newsletters — generating digest..."

    local skill
    skill=$(cat "$PLAYGROUND/.claude/skills/newsletter-insights/SKILL.md")

    local prompt
    prompt="$(printf 'You are generating a Newsletter digest. Follow the formatting rules below EXACTLY.\n\nFORMATTING INSTRUCTIONS:\n%s\n\n---\n\nRAW NEWSLETTER DATA (JSON):\n%s\n\n---\n\nIMPORTANT: Output ONLY the complete markdown digest. Start your response with the line "# Newsletter Digest — %s" and include nothing before it. No preamble, no explanation, no commentary.' "$skill" "$newsletters" "$DATE")"

    local tmp_file
    tmp_file=$(mktemp /tmp/newsletter-digest-XXXXXX.md)

    claude -p "$prompt" > "$tmp_file" 2>>"$LOG" || {
        log "[Newsletter] claude -p failed"
        rm -f "$tmp_file"
        return 1
    }

    # Validate output starts with a markdown heading
    local first_line
    first_line=$(head -1 "$tmp_file")
    if [[ "$first_line" != "#"* ]]; then
        log "[Newsletter] Output validation failed — first line: '$first_line'"
        rm -f "$tmp_file"
        return 1
    fi

    mkdir -p "$(dirname "$summary_file")"
    mv "$tmp_file" "$summary_file"
    log "[Newsletter] Digest saved to $summary_file"
    return 0
}

# ─────────────────────────────────────────
# Run both pipelines independently
# ─────────────────────────────────────────
twitter_ok=0
run_twitter || twitter_ok=1

newsletter_ok=0
run_newsletter || newsletter_ok=1

# ─────────────────────────────────────────
# Git commit and push (if anything changed)
# ─────────────────────────────────────────
if [ "$twitter_ok" -eq 0 ] || [ "$newsletter_ok" -eq 0 ]; then
    log "[Git] Staging changes..."
    cd "$PLAYGROUND"

    git add \
        twitter-insights/summaries/ \
        newsletter-insights/summaries/ \
        twitter-insights/data/scanned.json \
        newsletter-insights/data/scanned.json \
        2>>"$LOG" || true

    if git diff --cached --quiet; then
        log "[Git] Nothing to commit — already up to date"
    else
        git commit -m "Daily digest — $DATE [automated]" 2>>"$LOG"
        git push origin main --force-with-lease 2>>"$LOG"
        log "[Git] Pushed to GitHub"
    fi
else
    log "[Git] Both pipelines failed — skipping commit"
fi

log "=== Daily Digest Complete ==="

# Final failure check
if [ "$twitter_ok" -ne 0 ] && [ "$newsletter_ok" -ne 0 ]; then
    log "Both pipelines failed"
    exit 1
fi
