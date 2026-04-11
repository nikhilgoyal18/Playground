#!/usr/bin/env python3
"""
Validate Twitter digest quality before submission.
Enforces the quality standards from DIGEST_QUALITY_IMPROVEMENT.md

Run this on any generated digest:
  python3 validate_digest.py summaries/2026-04-11.md

Exit code 0 = digest passes all checks
Exit code 1 = digest fails one or more checks (list shown)
"""

import re
import sys
from pathlib import Path

CHECKS = {
    "min_bullets_per_tweet": 3,
    "min_insights": 3,  # Min bullets with insight keywords
    "required_keywords": {
        "implication": "Implication",
        "context": "Context|Competitive|Market|Suggests|Means",
        "specific_data": "\\$|\\d+%|\\d+[KMB]|company|named",
    },
}


def validate_digest(filepath: str) -> tuple[bool, list[str]]:
    """
    Validate a Twitter digest file.
    Returns (passes, error_list)
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]

    content = filepath.read_text()
    errors = []

    # Parse sections
    sections = re.split(r"^## ", content, flags=re.MULTILINE)[1:]  # Skip header
    if not sections:
        return False, ["No account sections found (expected ## headings)"]

    for section in sections:
        lines = section.split("\n")
        account_header = lines[0]
        match = re.search(r"(\w+) \(@(\w+)\)", account_header)
        if not match:
            continue

        name, handle = match.groups()

        # Find tweet subsections (### headings)
        tweet_blocks = re.split(r"^### ", "\n".join(lines[1:]), flags=re.MULTILINE)[1:]

        if not tweet_blocks:
            continue

        for tweet_idx, tweet_block in enumerate(tweet_blocks):
            tweet_lines = tweet_block.split("\n")
            tweet_title = tweet_lines[0]

            # Extract bullet points (lines starting with "- ")
            bullets = [line.strip() for line in tweet_lines[1:] if line.strip().startswith("-")]

            # Check 1: Minimum bullets per tweet
            if len(bullets) < CHECKS["min_bullets_per_tweet"]:
                errors.append(
                    f"@{handle} tweet '{tweet_title[:40]}...': "
                    f"Only {len(bullets)} bullets (need ≥{CHECKS['min_bullets_per_tweet']})"
                )

            # Check 2: Title not a quote (common paraphrase pattern)
            if re.match(r"^[A-Z][a-z]+ (is|was|are|were|has|have|do|does)", tweet_title):
                # Likely a paraphrase like "Elon says X" or "Company announces Y"
                if not any(word in tweet_title.lower() for word in ["validation", "implies", "suggests", "tradeoff", "problem", "signal"]):
                    errors.append(
                        f"@{handle} tweet '{tweet_title[:40]}...': "
                        f"Title looks like a paraphrase, not insight (e.g. 'X says Y'). "
                        f"Use strategic keywords like 'validates', 'implies', 'tradeoff'."
                    )

            # Check 3: Bullet content has actionable insights
            insight_count = 0
            for bullet in bullets:
                bullet_lower = bullet.lower()
                # Check for insight keywords
                has_insight = any(
                    re.search(pattern, bullet_lower)
                    for pattern in [
                        r"(implication|implies|suggests|means|signal|competitive|context|market)",
                        r"(\$[\d.]+|[\d.]+%|\d+[KMB] )",  # Specific data
                        r"(founder|investor|product|startup|company|strategic)",  # Decision relevance
                    ]
                )
                if has_insight:
                    insight_count += 1
                elif len(bullet) < 30:
                    # Very short bullets are often paraphrases or engagement counts
                    errors.append(
                        f"@{handle} tweet '{tweet_title[:30]}...': "
                        f"Bullet too short and lacks insight: '{bullet[:50]}...'"
                    )

            if insight_count < CHECKS["min_insights"]:
                errors.append(
                    f"@{handle} tweet '{tweet_title[:40]}...': "
                    f"Only {insight_count} insight-rich bullets (need ≥{CHECKS['min_insights']}). "
                    f"Bullets should include: implications, competitive context, specific data, decision relevance."
                )

    # Check 4: Summary Themes section exists
    if "## Summary Themes" not in content and "## Summary" not in content:
        errors.append(
            "No 'Summary Themes' section found at end of digest. "
            "Must synthesize cross-account patterns (e.g., 'AI commoditization mentioned by 3 accounts')."
        )

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_digest.py <filepath>")
        sys.exit(1)

    filepath = sys.argv[1]
    passes, errors = validate_digest(filepath)

    if passes:
        print(f"✅ PASS: {filepath} meets all quality standards")
        sys.exit(0)
    else:
        print(f"❌ FAIL: {filepath} has {len(errors)} quality issues:\n")
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
        print(f"\nReference: See twitter-insights/DIGEST_QUALITY_IMPROVEMENT.md for standards.")
        sys.exit(1)


if __name__ == "__main__":
    main()
