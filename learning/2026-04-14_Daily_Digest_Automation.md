# Daily Digest Automation — macOS LaunchAgent Pipeline

**Date:** 2026-04-14
**Project:** AI Playground
**Status:** Working in production

---

## What Was Built

A fully automated daily digest pipeline that runs at 2:00 PM every day and requires no manual intervention. It:

1. Fetches new tweets via `twitter-insights/fetch_tweets.py` (uses local Twitter cookies from `.env`)
2. Fetches new newsletters via `newsletter-insights/scan_newsletters.py` (uses local Gmail OAuth `token.json`)
3. Passes the JSON output plus skill formatting instructions to `claude -p` (headless CLI) to generate markdown digests
4. Validates the output starts with `#` before accepting it
5. Git commits and pushes both summary files to GitHub

The result: every day at 2 PM, two new files appear in the repo with no human involved.

---

## Files Created

| File | Purpose |
|------|---------|
| `/Users/nikhil/Documents/AI/Playground/scripts/daily_digest.sh` | Main shell script — orchestrates fetch, generate, validate, commit |
| `/Users/nikhil/Library/LaunchAgents/com.nikhil.daily-digest.plist` | macOS LaunchAgent — schedules the job at 14:00 daily |
| `/Users/nikhil/Library/Scripts/daily-digest-launcher.sh` | Intermediate launcher script — created during debugging, ultimately unused |

---

## Approach 1: launchd Calling bash Directly

### What Was Tried

The initial plist called `/bin/bash` directly:

```xml
<key>ProgramArguments</key>
<array>
    <string>/bin/bash</string>
    <string>/Users/nikhil/Documents/AI/Playground/scripts/daily_digest.sh</string>
</array>
```

### What Failed

```
/bin/bash: /Users/nikhil/Documents/AI/Playground/scripts/daily_digest.sh: Operation not permitted
```

Exit code `126` appeared in `launchctl list` — permission denied, not a script error.

### Root Cause: macOS TCC

macOS Transparency, Consent, and Control (TCC) on macOS 26 (Tahoe) blocks background launchd processes from reading files in `~/Documents/` without Full Disk Access explicitly granted. This applies even to **user-level** LaunchAgents (not just root system daemons) because the process has no GUI ancestor in its process tree.

When launchd spawns `/bin/bash`, that bash process has no association with the user's GUI session. TCC sees it as an untrusted background process and blocks filesystem access to sandboxed directories like `~/Documents/`, `~/Desktop/`, and `~/Downloads/`.

### Things That Did Not Fix It

**Granting Full Disk Access to `/bin/bash` in System Settings:**
- System Settings → Privacy & Security → Full Disk Access → added `/bin/bash`
- Didn't stick reliably; even when it appeared to be granted, the launchd context didn't inherit it

**Creating a wrapper in `~/Library/Scripts/`:**
- Made `daily-digest-launcher.sh` in `~/Library/Scripts/` (outside the TCC-protected paths)
- Had the wrapper exec the script in `~/Documents/`
- Same TCC error — the wrapper is not what's blocked; it's the downstream read of the file in `~/Documents/`

**Trying crontab:**
- Attempted `crontab -` from within Claude Code's bash context
- Failed: couldn't write the crontab temp file due to the same TCC restrictions on the shell environment

---

## Fix: osascript `do shell script`

### The Solution

Changed `ProgramArguments` in the plist to call `osascript` with an inline AppleScript `do shell script` command:

```xml
<key>ProgramArguments</key>
<array>
    <string>/usr/bin/osascript</string>
    <string>-e</string>
    <string>do shell script "/bin/bash /Users/nikhil/Documents/AI/Playground/scripts/daily_digest.sh >> /Users/nikhil/Library/Logs/daily-digest-cron.log 2>&1"</string>
</array>
```

### Why This Works

`osascript do shell script` executes in the context of the user's active GUI session. Unlike a raw launchd bash process, it has a GUI ancestor and inherits the user's full TCC permissions — including access to `~/Documents/`. This is the same mechanism used by Automator and Script Editor.

The shell command inside `do shell script` runs as the logged-in user with all the same privileges as a Terminal session.

### Verification

After loading the updated plist with `launchctl load`, the job appeared in `launchctl list` with an actual PID (not `-`) during its run window, and the log file at `~/Library/Logs/daily-digest-cron.log` began writing. Tweets were fetched, digests generated, and the commit appeared on GitHub.

---

## Bug Found: Wrong Skill File Paths

### What Happened

On the first automated run after the TCC fix, the digests were generated but had completely wrong formatting. The Twitter summary was a flat list grouped by category with raw tweet text and no insight bullets. The newsletter summary was a numbered list with "Key takeaways:" headers instead of the proper sender-grouped `##` sections with `###` per issue.

### Root Cause

The script had incorrect paths for the skill instruction files:

```bash
# WRONG — what was originally in the script
skill=$(cat "$PLAYGROUND/.claude/skills/twitter-insights.md")
skill=$(cat "$PLAYGROUND/.claude/skills/newsletter-insights.md")

# CORRECT — actual paths
skill=$(cat "$PLAYGROUND/.claude/skills/twitter-insights/SKILL.md")
skill=$(cat "$PLAYGROUND/.claude/skills/newsletter-insights/SKILL.md")
```

The files don't exist at the wrong paths, so `cat` exited with an error — but only to stderr. The variable `$skill` was set to an empty string. The script continued without checking whether the load succeeded.

`claude -p` then received a prompt that contained the tweet/newsletter JSON data but zero formatting instructions. It generated a plausible-looking markdown file — one that passed the `#` validation check — but with none of the insight extraction, bullet structure, or sender grouping the skills define.

### How It Was Detected

The format corruption was obvious on inspection: the Twitter file had raw tweet text grouped by account name with no analysis bullets. Normal output extracts implications, context, and specifics from each tweet in 3-4 bullets. The newsletter file had numbered items and "Key takeaways:" sections instead of the `##` sender / `###` issue structure.

### Recovery Steps

1. Identified the last good commit before the bad run:
   ```bash
   git log --oneline -10
   ```

2. Restored `scanned.json` for both projects to pre-run state so they would re-fetch and re-process the same data:
   ```bash
   git show <prev-commit>:twitter-insights/data/scanned.json > /tmp/restore_twitter.json
   cp /tmp/restore_twitter.json twitter-insights/data/scanned.json

   git show <prev-commit>:newsletter-insights/data/scanned.json > /tmp/restore_newsletter.json
   cp /tmp/restore_newsletter.json newsletter-insights/data/scanned.json
   ```

3. Deleted the bad summary files.

4. Fixed the paths in `daily_digest.sh`.

5. Re-ran the `twitter-insights` and `newsletter-insights` skills manually to regenerate properly formatted digests.

6. Committed and pushed the corrected outputs.

### The Fix Applied

Added an explicit check after loading skill content:

```bash
skill=$(cat "$PLAYGROUND/.claude/skills/twitter-insights/SKILL.md")
if [[ -z "$skill" ]]; then
    echo "ERROR: Failed to load twitter-insights skill. Aborting." >&2
    return 1
fi
```

This causes the function to abort and log an error rather than silently passing an empty prompt to Claude.

---

## Script Design Decisions

### Independent Pipelines, No Top-Level `set -e`

Twitter and newsletter generation run in isolated functions. A failure in one does not abort the other. Git commit is skipped only if both fail.

```bash
twitter_ok=0
run_twitter || twitter_ok=1

newsletter_ok=0
run_newsletter || newsletter_ok=1

if [[ $twitter_ok -eq 1 && $newsletter_ok -eq 1 ]]; then
    echo "Both pipelines failed. Skipping git commit."
    exit 1
fi
```

### Idempotency

If today's summary file already exists in the summaries folder, the function returns immediately. The script is safe to run multiple times on the same day — it will not overwrite a good digest with a re-run.

```bash
OUTFILE="$PLAYGROUND/twitter-insights/summaries/$(date +%Y-%m-%d).md"
if [[ -f "$OUTFILE" ]]; then
    echo "Twitter digest already exists for today. Skipping."
    return 0
fi
```

### Output Validation

`claude -p` stdout is captured to a temp file. Before accepting the output, the script checks that the first line starts with `#`:

```bash
first_line=$(head -1 "$tmpfile")
if [[ "$first_line" != \#* ]]; then
    echo "ERROR: Claude output did not start with '#'. Output rejected." >&2
    cat "$tmpfile" >&2
    return 1
fi
mv "$tmpfile" "$OUTFILE"
```

This catches cases where Claude returns an error message, an apology, or preamble text instead of the digest. (Note: this check does NOT catch the silent `cat` failure case above — a properly formatted but wrong-content output still passes. The fix there is validating that `$skill` is non-empty before calling Claude.)

### Prompt Design

Each prompt embeds three things in order: the full SKILL.md content, the fetched JSON data, and a terminal instruction:

```bash
prompt="$skill

Here is today's data:
$json_data

Output ONLY the complete markdown digest. Start your response with \`# [Title] — $(date +%Y-%m-%d)\` and include nothing before it."
```

The terminal instruction overrides any tendency for Claude to add preamble, commentary, or sign-off text.

### PATH in the Plist

launchd starts with a minimal PATH that does not include Homebrew, Python framework, or user-installed binaries. The plist explicitly sets a PATH environment variable:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>/Users/nikhil/.local/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:/usr/bin:/bin</string>
</dict>
```

Key entries:
- `/Users/nikhil/.local/bin` — where `claude` CLI is installed
- `/Library/Frameworks/Python.framework/Versions/3.14/bin` — `python3` and `python3.14` for the fetch scripts
- Standard paths for `git`, `bash`, `osascript`

Without this, `claude: command not found` and `python3: command not found` would silently kill the pipeline.

### Log Rotation

The script deletes digest logs older than 30 days to prevent unbounded growth:

```bash
find "$HOME/Library/Logs" -name "daily-digest*.log" -mtime +30 -delete
```

### Failure Notification

A `trap` on `ERR` sends a macOS notification so failures don't go unnoticed:

```bash
on_error() {
    osascript -e 'display notification "Daily digest failed. Check logs." with title "Digest Error"'
}
trap on_error ERR
```

### Git Push

Uses `--force-with-lease` (safe force push — will not overwrite commits pushed by another process since last fetch) and only runs if `git diff --cached` shows actual staged changes:

```bash
git add twitter-insights/summaries/ newsletter-insights/summaries/
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    git commit -m "Daily digest — $(date +%Y-%m-%d)"
    git push --force-with-lease
fi
```

---

## Key Learnings

### 1. macOS 26 TCC Blocks launchd Agents from `~/Documents/`

Even user-level LaunchAgents (not root daemons) cannot access `~/Documents/`, `~/Desktop/`, or `~/Downloads/` without Full Disk Access. Granting FDA to `/bin/bash` in System Settings does not reliably solve this because the launchd context has no GUI session lineage.

**The reliable fix:** Use `osascript do shell script` in the plist. This runs in the GUI session context and inherits full user TCC permissions.

### 2. `claude -p` Works Headlessly

The `claude` CLI (Claude Code) works without a TTY, without an API key env var, and without a display. It reads credentials from `~/.claude/` and runs fine when invoked from a launchd/osascript context.

Preflight test to confirm the full pipeline will work before building automation:
```bash
launchctl asuser $(id -u) /bin/bash -c 'claude -p "Output only this exact text: OK"'
```
If this returns `OK`, headless Claude invocation is functioning in the launchd environment.

### 3. Remote Scheduling (Cloud Agents) Cannot Access Local Credentials

The `/schedule` skill and similar remote-trigger mechanisms run in Anthropic's cloud infrastructure. They have no access to:
- Local `.env` files (Twitter cookies)
- Local `token.json` (Gmail OAuth)
- Local `data/scanned.json` (state tracking)

Any automation that depends on local credentials or local state must run on the local machine. Remote triggers are only viable for tasks that can be performed entirely from the git repo contents.

### 4. Silent `cat` Failures Cause Format Corruption That Passes Validation

When `cat` fails on a wrong path, bash sets the variable to an empty string and continues. If that variable is the skill instructions passed to `claude -p`, Claude generates plausible-looking output with no formatting errors — it just has completely wrong structure and content.

This kind of failure **passes a `#` validation check** and produces no obvious error in logs. The only detection method is visually inspecting the output.

**Defense:** Always check that skill content loaded successfully before using it:
```bash
skill=$(cat "$SKILL_PATH")
[[ -z "$skill" ]] && { echo "ERROR: skill load failed"; return 1; }
```

### 5. Restoring State from Git for Re-Runs

When a failed run partially updated `scanned.json` before the digest was generated correctly, restore the pre-run state from git:

```bash
git show <commit-hash>:path/to/scanned.json > /tmp/restore.json
cp /tmp/restore.json path/to/scanned.json
```

This resets the "what has been processed" pointer so the pipeline re-fetches and re-processes the same data on the next run.

### 6. `launchctl list` for Diagnosing Job State

```
PID  Status  Label
-    0       com.nikhil.daily-digest    # not currently running; last exit was 0 (success)
-    126     com.nikhil.daily-digest    # not running; last exit was 126 (TCC block or not executable)
1234 -       com.nikhil.daily-digest    # currently running, PID 1234
```

Exit code `126` specifically means the process was blocked from executing — either TCC denied access or the script file is not executable. Not a script logic error.

### 7. Skill Paths Use Subdirectory Structure

Skills in this project are not flat `.md` files at the root of `.claude/skills/`. They are subdirectories with a `SKILL.md` inside:

```
.claude/skills/
  twitter-insights/
    SKILL.md
  newsletter-insights/
    SKILL.md
```

The wrong path (`twitter-insights.md`) silently returns nothing. Always verify skill file paths before referencing them in automation scripts.

---

## Final State

The pipeline runs daily at 14:00. On a successful run:

1. `fetch_tweets.py` fetches tweets not yet in `scanned.json`, writes JSON to stdout
2. `scan_newsletters.py` fetches Gmail newsletters not yet processed, writes JSON to stdout
3. Each JSON blob is combined with the relevant SKILL.md and sent to `claude -p`
4. Output is validated (starts with `#`) and written to the summaries folder
5. Both files are staged and committed with message `Daily digest — YYYY-MM-DD`
6. Pushed to GitHub with `--force-with-lease`

Logs write to `~/Library/Logs/daily-digest-cron.log`. Failures trigger a macOS notification.
