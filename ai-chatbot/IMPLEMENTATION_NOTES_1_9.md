# User Feedback Signal (1.9) — Implementation Summary

**Date:** 2026-04-11  
**Commit:** `71770af` — "Implement user feedback signal (1.9) — thumbs up/down on answers"  
**Status:** ✅ Complete and tested

---

## Overview

Added per-answer thumbs up/down buttons that let users rate chatbot responses. Feedback is persisted to SQLite and survives page reloads via sessionStorage.

---

## Changes Made

### 1. `logger.py` — Database Layer

**Lines 48-49:** Added `feedback TEXT` column to schema
```python
conversation_id             TEXT,
feedback                    TEXT
```

**Lines 100-104:** Added idempotent migration for existing DBs
```python
try:
    conn.execute("ALTER TABLE searches ADD COLUMN feedback TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists
```

**Lines 172-199:** Added `update_feedback()` function
- Accepts `search_id` (int) and `feedback` ("up" or "down")
- Returns True if row found and updated, False if not found
- Handles DB exceptions gracefully

### 2. `app.py` — Backend API

**Line 12:** Updated import
```python
from logger import init_db, save_log, update_feedback
```

**Lines 217-244:** Added `POST /feedback` route
- Validates input: `id` must be int, `feedback` must be "up" or "down"
- Returns 400 for bad input, 404 for unknown ID, 200 for success
- Calls `update_feedback()` and returns appropriate JSON response

### 3. `templates/index.html` — Frontend UI

**Lines 319-363:** Added CSS for feedback row and buttons
- `.feedback-row`: flex container for label + 2 buttons
- `.btn-feedback`: button styling with hover/focus states
- `.selected-up` / `.selected-down`: highlight classes (green/red)
- All styles override the global blue button style via `background: none`

**Lines 553-623:** Added feedback row DOM in `addMessage()` function
- Only rendered for assistant messages with valid `metadata.id`
- Buttons: 👍 (thumbs up) and 👎 (thumbs down)
- Features:
  - `aria-label` attributes for accessibility
  - Click handlers POST to `/feedback` endpoint
  - Visual highlights swap on click
  - Re-click support: user can change feedback anytime
  - sessionStorage persistence: feedback state survives page reload
  - Silent error handling: console logs failures but doesn't block UI

---

## Architecture

### Data Flow

```
User clicks 👍 button
    ↓
submitFeedback() called
    ↓
POST /feedback { id: 30, feedback: "up" }
    ↓
Flask route validates input
    ↓
update_feedback(30, "up")
    ↓
UPDATE searches SET feedback = "up" WHERE id = 30
    ↓
Return { "ok": true }
    ↓
Visual highlight applied (selected-up class)
    ↓
sessionStorage updated with feedback value
```

### State Persistence

- **Initial state:** No feedback (buttons unhighlighted)
- **After click:** Feedback sent to DB, button highlighted, sessionStorage updated
- **On page reload:** `restoreChat()` reads sessionStorage, re-renders messages with feedback metadata, buttons restore highlighting
- **On re-click:** Same flow as initial click; new value overwrites old value in both DB and sessionStorage

---

## Testing Results

### Database

✅ Migration ran successfully
- Column 29: `feedback TEXT`
- Existing DBs updated via ALTER TABLE

### API Endpoint

Tested all 5 cases:
- ✅ Happy path (up): 200 `{"ok": true}`
- ✅ Change feedback (down): 200 `{"ok": true}`
- ✅ Bad value (meh): 400 validation error
- ✅ Bad id (string): 400 validation error
- ✅ Not found (999999): 404 error

### Data Persistence

✅ DB update verified
```sql
SELECT id, feedback FROM searches WHERE id = 30;
Result: 30|down
```

### Audit Queries

✅ Aggregation working
```sql
SELECT feedback, COUNT(*) FROM searches WHERE feedback IS NOT NULL GROUP BY feedback;
Result: down|1
```

---

## Design Decisions (Per Panel Review Feedback)

1. **Accessibility:** Added `aria-label` attributes to both buttons so screen readers announce the intent
2. **Visibility:** Feedback row placed BEFORE log footer so buttons are adjacent to answer without scrolling past log toggle
3. **Silent failures:** Network errors logged to console but don't show error message to user (acceptable for personal tool)
4. **No disable:** Buttons never disable after submit, encouraging user exploration and feedback changes
5. **Enum values:** Used "up"/"down" strings (not 1/-1) for SQL query readability

---

## Usage

### UI Flow

1. User opens chatbot at `http://localhost:5001`
2. Asks a question
3. Below the assistant's answer, sees "Helpful?" with 👍 and 👎 buttons
4. Clicks 👍 → button turns green
5. Can click 👎 anytime to switch to red
6. Reloads page → button state is restored

### Monitoring Feedback

```sql
-- Feedback distribution
SELECT feedback, COUNT(*) FROM searches WHERE feedback IS NOT NULL GROUP BY feedback;

-- Recent feedback (last 20)
SELECT id, timestamp, query, feedback FROM searches 
WHERE feedback IS NOT NULL 
ORDER BY id DESC LIMIT 20;

-- Baseline: % positive (target ≥80%)
SELECT ROUND(100.0 * SUM(CASE WHEN feedback = 'up' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_positive
FROM searches WHERE feedback IS NOT NULL;
```

---

## Next Steps

1. **Monitor baseline:** Wait for 50+ feedback samples before setting up alerts
2. **Set up alerting:** If positive % drops below 80%, investigate routing or content issues
3. **Analyze patterns:** Use negative feedback to identify systemic failures
   - E.g., if internal path has <70% positive, consider lowering judge threshold
   - E.g., if web fallback has <60% positive, consider different search strategy
4. **Consider follow-up features:**
   - Optional text feedback ("Why?" reason for down votes)
   - Per-path feedback breakdown (is internal better than web?)
   - Dashboard with feedback trends over time

---

## Files Modified

- `ai-chatbot/logger.py` — DB schema, migration, update function
- `ai-chatbot/app.py` — /feedback route, import
- `ai-chatbot/templates/index.html` — CSS, DOM, JavaScript
- `ai-chatbot/PLAN.md` — Added to shipped features
- `ai-chatbot/eval/METRICS_AND_GUARDRAILS.md` — Marked 1.9 as done, added audit queries

---

## Lines of Code

- `logger.py`: +30 lines (schema column, migration, update function)
- `app.py`: +29 lines (import, route)
- `index.html`: +156 lines (CSS, DOM, JavaScript)
- **Total:** ~215 lines of new code
