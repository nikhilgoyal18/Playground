#!/usr/bin/env python3
"""
scan_newsletters.py

Fetches new newsletters from Gmail and outputs them as JSON with full body text.
Tracks already-scanned email IDs in data/scanned.json to avoid re-processing.

Usage:
  python3 scan_newsletters.py         # Normal run: fetch and output new newsletters
  python3 scan_newsletters.py --auth  # One-time OAuth setup
"""

import argparse
import base64
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
SCANNED_FILE = BASE_DIR / "data" / "scanned.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_QUERY = "from:@substack.com OR subject:newsletter"
MAX_RESULTS = 50  # Full bodies are larger; 50 is the right batch size
BODY_CHAR_LIMIT = 3000  # Per email — enough for deep content, fits in context


def get_gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(
                    "ERROR: credentials.json not found. "
                    "Complete the one-time setup described in CLAUDE.md.",
                    file=sys.stderr,
                )
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def load_scanned() -> dict:
    if SCANNED_FILE.exists():
        return json.loads(SCANNED_FILE.read_text())
    return {"scanned_ids": [], "last_run": None}


def save_scanned(state: dict):
    SCANNED_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    SCANNED_FILE.write_text(json.dumps(state, indent=2))


def extract_body_text(payload: dict) -> str:
    """Walk the MIME payload tree, prefer text/plain over text/html, decode and clean."""
    mime = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if parts:
        # First pass: prefer text/plain
        for part in parts:
            if part.get("mimeType") == "text/plain":
                text = extract_body_text(part)
                if text:
                    return text
        # Second pass: accept text/html
        for part in parts:
            if part.get("mimeType") == "text/html":
                text = extract_body_text(part)
                if text:
                    return text
        # Fallback: recurse into any part (handles nested multipart)
        for part in parts:
            text = extract_body_text(part)
            if text:
                return text

    if mime in ("text/plain", "text/html"):
        data = payload.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            if mime == "text/html":
                decoded = re.sub(r"<[^>]+>", " ", decoded)    # strip HTML tags
                decoded = re.sub(r"\s+", " ", decoded).strip()  # collapse whitespace
            return decoded

    return ""


def get_message_detail(service, msg_id: str) -> dict:
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    # Parse date header into ISO format if possible
    date_raw = headers.get("Date", "")
    try:
        from email.utils import parsedate_to_datetime
        date_iso = parsedate_to_datetime(date_raw).isoformat()
    except Exception:
        date_iso = date_raw

    body = extract_body_text(payload)[:BODY_CHAR_LIMIT]

    return {
        "id": msg_id,
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "date": date_iso,
        "body": body,
    }


def fetch_new_newsletters(service, scanned_ids: set) -> list[dict]:
    results = service.users().messages().list(
        userId="me",
        q=GMAIL_QUERY,
        maxResults=MAX_RESULTS,
    ).execute()

    messages = results.get("messages", [])
    new_ids = [m["id"] for m in messages if m["id"] not in scanned_ids]

    if not new_ids:
        return []

    newsletters = []
    for msg_id in new_ids:
        try:
            detail = get_message_detail(service, msg_id)
            newsletters.append(detail)
        except Exception as e:
            print(f"Warning: could not fetch message {msg_id}: {e}", file=sys.stderr)

    # Sort by date descending (newest first)
    newsletters.sort(key=lambda x: x["date"], reverse=True)
    return newsletters


def main():
    parser = argparse.ArgumentParser(description="Fetch new newsletters from Gmail")
    parser.add_argument("--auth", action="store_true", help="Run OAuth setup flow and exit")
    args = parser.parse_args()

    service = get_gmail_service()

    if args.auth:
        print("Authentication successful. token.json saved.", file=sys.stderr)
        sys.exit(0)

    state = load_scanned()
    scanned_ids = set(state["scanned_ids"])

    newsletters = fetch_new_newsletters(service, scanned_ids)

    # Update scanned state
    new_ids = [n["id"] for n in newsletters]
    state["scanned_ids"] = list(scanned_ids | set(new_ids))
    save_scanned(state)

    # Output results as JSON to stdout (Claude reads this)
    print(json.dumps(newsletters, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
