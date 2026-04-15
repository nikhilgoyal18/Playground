#!/usr/bin/env python3
"""
Validate Newsletter digest output before committing.

Run on a generated digest:
  python3 validate_digest.py summaries/2026-04-15.md
  python3 validate_digest.py --security-only summaries/2026-04-15.md

Exit code 0 = passes all checks
Exit code 1 = one or more checks failed
"""

import re
import sys
from pathlib import Path

MAX_DIGEST_BYTES = 100_000  # 100KB — suspicious if exceeded

# Patterns that should never appear in a generated digest
DANGEROUS_PATTERNS = [
    (r'\brm\s+(-\S+\s+)*[/~]', "shell rm on absolute/home path"),
    (r'\brm\s+-[rRfF]', "shell rm with -r/-f flags"),
    (r'\bcurl\b', "curl invocation"),
    (r'\bwget\b', "wget invocation"),
    (r'\bchmod\b', "chmod invocation"),
    (r'\bchown\b', "chown invocation"),
    (r'\$\(', "command substitution $()"),
    (r'`[^`]{1,200}`', "backtick command substitution"),
    (r'>\s*[/~]', "shell output redirection to absolute/home path"),
    (r'\beval\b', "eval invocation"),
    (r'\bexec\b', "exec invocation"),
    (r'\bsudo\b', "sudo invocation"),
    (r'\bssh\b', "ssh invocation"),
    (r'\bscp\b', "scp invocation"),
    (r'\bnc\b|\bncat\b|\bnetcat\b', "netcat invocation"),
    (r'\bpython\s+-c\b', "python -c inline execution"),
    (r'\bnode\s+-e\b', "node -e inline execution"),
    (r'```\s*(bash|sh|zsh|fish|ksh|csh|shell|python|ruby|perl|node|js|javascript|typescript|ts)\b',
     "executable code fence"),
]


def security_check(filepath: Path) -> tuple[bool, list[str]]:
    errors = []

    size = filepath.stat().st_size
    if size > MAX_DIGEST_BYTES:
        errors.append(f"Output too large ({size} bytes > {MAX_DIGEST_BYTES} limit) — possible injection")

    content = filepath.read_text()

    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, content):
            errors.append(f"Dangerous pattern detected: {description}")

    return len(errors) == 0, errors


def validate_digest(filepath: str) -> tuple[bool, list[str]]:
    fp = Path(filepath)
    if not fp.exists():
        return False, [f"File not found: {fp}"]

    content = fp.read_text()
    errors = []

    # Must start with a markdown heading
    first_line = content.split("\n")[0] if content else ""
    if not first_line.startswith("#"):
        errors.append(f"First line must be a markdown heading, got: '{first_line[:60]}'")

    # Must have at least one sender section (## heading)
    sender_sections = re.findall(r"^## .+", content, re.MULTILINE)
    if not sender_sections:
        errors.append("No sender sections found (expected ## headings for each newsletter)")

    # Each sender section should have at least one subsection (### heading) or bullet list
    sections = re.split(r"^## ", content, flags=re.MULTILINE)[1:]
    for section in sections:
        header = section.split("\n")[0]
        has_subsection = bool(re.search(r"^### ", section, re.MULTILINE))
        has_bullets = bool(re.search(r"^- ", section, re.MULTILINE))
        if not has_subsection and not has_bullets:
            errors.append(f"Section '{header[:50]}' has no content (no ### subsections or bullet points)")

    return len(errors) == 0, errors


def main():
    args = sys.argv[1:]
    security_only = "--security-only" in args
    paths = [a for a in args if not a.startswith("--")]

    if not paths:
        print("Usage: python3 validate_digest.py [--security-only] <filepath>")
        sys.exit(1)

    filepath = paths[0]
    fp = Path(filepath)
    if not fp.exists():
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    if security_only:
        passes, errors = security_check(fp)
        if passes:
            sys.exit(0)
        else:
            print(f"❌ SECURITY FAIL: {filepath}", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

    sec_ok, sec_errors = security_check(fp)
    qual_ok, qual_errors = validate_digest(filepath)

    errors = sec_errors + qual_errors
    if not errors:
        print(f"✅ PASS: {filepath} meets all quality standards")
        sys.exit(0)
    else:
        print(f"❌ FAIL: {filepath} has {len(errors)} issues:\n")
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
