#!/usr/bin/env python3
"""
fetch_tweets.py

Fetches new tweets from your Twitter/X home timeline using direct API calls.
Uses cookie-based auth (auth_token + ct0) — no API key required.
Tracks already-seen tweet IDs in data/scanned.json to avoid re-processing.

Usage:
  python3 fetch_tweets.py              # Normal run: fetch and output new tweets
  python3 fetch_tweets.py --auth-check # Verify cookies are valid and exit
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).parent
SCANNED_FILE = BASE_DIR / "data" / "scanned.json"
ENV_FILE = BASE_DIR / ".env"

MAX_TWEETS = 100
LOOKBACK_HOURS = 12

BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
# HomeLatestTimeline = "Following" tab (only accounts you follow, chronological)
# HomeTimeline = "For You" tab (algorithmic, includes recommendations & ads)
HOME_TIMELINE_URL = (
    "https://twitter.com/i/api/graphql/U0cdisy7QFIoTfu3-Okw0A/HomeLatestTimeline"
)
FEATURES = {
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "responsive_web_media_download_video_enabled": False,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}


def load_env():
    load_dotenv(ENV_FILE)
    auth_token = os.getenv("AUTH_TOKEN")
    ct0 = os.getenv("CT0")
    missing = []
    if not auth_token:
        missing.append("AUTH_TOKEN")
    if not ct0:
        missing.append("CT0")
    if missing:
        print(
            f"ERROR: {', '.join(missing)} not set in .env. "
            "Complete the one-time setup described in CLAUDE.md.",
            file=sys.stderr,
        )
        sys.exit(1)
    return auth_token, ct0


def load_scanned() -> dict:
    if SCANNED_FILE.exists():
        return json.loads(SCANNED_FILE.read_text())
    return {"scanned_ids": [], "last_run": None}


def save_scanned(state: dict):
    SCANNED_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    SCANNED_FILE.write_text(json.dumps(state, indent=2))


def make_headers(ct0: str) -> dict:
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json",
        "X-Csrf-Token": ct0,
        "X-Twitter-Auth-Type": "OAuth2Session",
        "X-Twitter-Client-Language": "en",
        "X-Twitter-Active-User": "yes",
        "Referer": "https://twitter.com/home",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }


def extract_tweets_from_response(data: dict) -> list[dict]:
    """Walk the GraphQL response and extract tweet objects."""
    tweets = []
    try:
        instructions = (
            data["data"]["home"]["home_timeline_urt"]["instructions"]
        )
    except (KeyError, TypeError):
        return tweets

    for instruction in instructions:
        if instruction.get("type") != "TimelineAddEntries":
            continue
        for entry in instruction.get("entries", []):
            content = entry.get("content", {})
            item_content = content.get("itemContent", {})
            if item_content.get("itemType") != "TimelineTweet":
                continue
            tweet_results = item_content.get("tweet_results", {}).get("result", {})
            if not tweet_results:
                continue

            # Handle promoted tweets wrapper
            if tweet_results.get("__typename") == "TweetWithVisibilityResults":
                tweet_results = tweet_results.get("tweet", {})

            legacy = tweet_results.get("legacy", {})
            if not legacy:
                continue

            # Skip retweets
            if "retweeted_status_result" in legacy:
                continue

            user_legacy = (
                tweet_results.get("core", {})
                .get("user_results", {})
                .get("result", {})
                .get("legacy", {})
            )

            tweet_id = legacy.get("id_str", "")
            text = legacy.get("full_text", legacy.get("text", ""))
            created_at = legacy.get("created_at", "")

            # Skip tweets older than LOOKBACK_HOURS
            try:
                tweet_dt = parsedate_to_datetime(created_at)
                cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
                if tweet_dt < cutoff:
                    continue
            except Exception:
                pass  # if unparseable, include the tweet

            tweets.append({
                "id": tweet_id,
                "author_username": user_legacy.get("screen_name", ""),
                "author_name": user_legacy.get("name", ""),
                "text": text,
                "created_at": created_at,
                "like_count": legacy.get("favorite_count", 0),
                "retweet_count": legacy.get("retweet_count", 0),
                "reply_count": legacy.get("reply_count", 0),
            })

    return tweets


async def fetch_new_tweets(auth_token: str, ct0: str, scanned_ids: set) -> list[dict]:
    cookies = {"auth_token": auth_token, "ct0": ct0}
    headers = make_headers(ct0)
    variables = {
        "count": MAX_TWEETS,
        "includePromotedContent": False,
        "latestControlAvailable": True,
        "requestContext": "launch",
        "withCommunity": True,
        "seenTweetIds": [],
    }
    payload = {
        "variables": variables,
        "features": FEATURES,
        "queryId": "U0cdisy7QFIoTfu3-Okw0A",
    }

    async with httpx.AsyncClient(cookies=cookies, follow_redirects=True) as client:
        response = await client.post(
            HOME_TIMELINE_URL,
            json=payload,
            headers=headers,
        )

    if response.status_code == 401:
        print("ERROR: Auth failed (401). Your cookies may be expired — re-copy auth_token and ct0 from your browser.", file=sys.stderr)
        sys.exit(1)
    if response.status_code == 403:
        print("ERROR: Forbidden (403). Check that ct0 matches your auth_token session.", file=sys.stderr)
        sys.exit(1)
    if response.status_code != 200:
        print(f"ERROR: Unexpected status {response.status_code}: {response.text[:200]}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    all_tweets = extract_tweets_from_response(data)

    # Filter to only new tweets
    new_tweets = [t for t in all_tweets if t["id"] not in scanned_ids and t["id"]]

    # Sort newest first (Twitter dates: "Mon Jan 01 00:00:00 +0000 2024")
    new_tweets.sort(key=lambda x: x["created_at"], reverse=True)
    return new_tweets


async def main_async(args):
    auth_token, ct0 = load_env()

    if args.auth_check:
        try:
            tweets = await fetch_new_tweets(auth_token, ct0, set())
            print(f"Auth check passed — got {len(tweets)} tweets.", file=sys.stderr)
        except SystemExit:
            raise
        except Exception as e:
            print(f"Auth check FAILED: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    state = load_scanned()
    scanned_ids = set(state["scanned_ids"])

    try:
        tweets = await fetch_new_tweets(auth_token, ct0, scanned_ids)
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR fetching tweets: {e}", file=sys.stderr)
        sys.exit(1)

    # Update state
    new_ids = [t["id"] for t in tweets]
    state["scanned_ids"] = list(scanned_ids | set(new_ids))
    save_scanned(state)

    print(json.dumps(tweets, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Fetch new tweets from home timeline")
    parser.add_argument("--auth-check", action="store_true", help="Verify cookies are valid and exit")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
