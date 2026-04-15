#!/usr/bin/env python3
"""
Sanitize JSON text fields to prevent prompt injection.
Reads a JSON array from stdin, strips injection patterns from the specified
field (and subject/from fields), writes cleaned JSON to stdout.

Usage:
  echo '$json' | python3 sanitize_json.py <field>

Example:
  echo '$tweets' | python3 sanitize_json.py text
  echo '$newsletters' | python3 sanitize_json.py body
"""
import json
import re
import sys

field = sys.argv[1]
data = json.load(sys.stdin)

for item in data:
    for key in (field, "subject", "from"):
        val = item.get(key)
        if not isinstance(val, str):
            continue
        # Prevent XML tag escapes from data section
        val = re.sub(r'</?(data|tweet_data|newsletter_data)\s*>', '', val, flags=re.IGNORECASE)
        # Strip prompt-injection preamble lines
        val = re.sub(
            r'(?im)^(IGNORE|DISREGARD|OVERRIDE|SYSTEM\s*:|IMPORTANT\s*:).*$',
            '[removed]',
            val
        )
        # Replace triple backticks (code fence injection)
        val = val.replace('```', '[code]')
        item[key] = val

print(json.dumps(data, ensure_ascii=False))
