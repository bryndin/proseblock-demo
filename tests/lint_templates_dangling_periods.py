#!/usr/bin/env python3
"""
Test script for the Zero-Dot Policy.

Usage:
    python3 tests/test_dangling_periods.py

This script checks all Hugo templates in the `layouts` directory for "dangling periods" (.),
which are forbidden by the Zero-Dot Policy. It allows explicit context captures like
`$variable := .` or `$page := .page` but flags any other use of a bare dot.
"""

# Note: Here's the regexp for the manual grepping.
# \{\{[^\}]*?(?<=\s|\(|\[)(?:\.(?!page\b|\d)\w+|(?<!:=)(?<!=)(?<!:=\s)(?<!=\s)\.(?!\w))


import re
import sys
from pathlib import Path

def preserve_newlines(match):
    """
    Replaces matched multiline comments with empty lines.
    This hides the comment from the linter but keeps line numbers exactly accurate!
    """
    return '\n' * match.group(0).count('\n')

def test_zero_dot_policy():
    # Resolves to: ../themes/proseblock/layouts
    # Adjust "proseblock" to match your actual theme folder name
    layouts_dir = Path(__file__).parent.parent / "themes" / "proseblock" / "layouts"

    if not layouts_dir.exists():
        print(f"Directory not found: {layouts_dir}")
        sys.exit(1)

    # 1. Matches Hugo comments: {{/* ... */}} or {{- /* ... */ -}}
    # (Using simple {{ and }} without backslashes to avoid Python SyntaxWarnings)
    comment_pattern = re.compile(r'{{-?\s*/\*.*?\*/\s*-?}}', re.DOTALL)

    # 2. Matches Go template tags: {{ ... }} or {{- ... -}} across multiple lines
    tag_pattern = re.compile(r'{{(.*?)}}', re.DOTALL)

    # 3. Matches string literals (to remove them and prevent false positives)
    string_pattern = re.compile(r'(".*?"|\'.*?\'|`.*?`)', re.DOTALL)

    # 4: Allowed: ONLY bare dot assignments ($var := .)
    allowed_assignment_pattern = re.compile(r'\$[\w]+\s*(?::=|=)\s*\.(?!\w)')

    # 5. Matches a forbidden dot:
    # - Preceded by start of string, space, or brackets
    # - A literal dot
    # - Not followed by a digit (allowing floats like .14)
    dot_pattern = re.compile(r'(^|\s|\(|\[)\.(?!\d)\w*')

    issues = 0

    for filepath in layouts_dir.rglob('*.html'):
        text = filepath.read_text(encoding='utf-8')

        # Strip comments first, but replace them with newlines to keep line tracking accurate
        text = comment_pattern.sub(preserve_newlines, text)

        for match in tag_pattern.finditer(text):
            # Extract inner content and strip Hugo's formatting dashes/spaces
            tag_content = match.group(1).strip('- \t\n\r')

            # Strip string literals so dots inside "file.html" aren't checked
            cleaned = string_pattern.sub('""', tag_content)

            # Strip explicitly allowed captures ($var := . or $page := .page)
            cleaned = allowed_assignment_pattern.sub('', cleaned)

            # Search the remaining logic for forbidden dangling dots
            dot_match = dot_pattern.search(cleaned)
            if dot_match:
                # Calculate the exact line number of the match
                line_num = text[:match.start()].count('\n') + 1

                print(f"❌ {filepath.relative_to(layouts_dir.parent.parent.parent.parent)}:{line_num}")
                # We show the offending tag, collapsing multiline matches to 1 line for readability
                offending_code = match.group(0).replace('\n', ' ').strip()
                print(f"   Forbidden dot found: {offending_code}")
                issues += 1

    if issues == 0:
        print("✅ All clear! No dangling periods found.")
        sys.exit(0)
    else:
        print(f"\n🚨 Linting failed: Found {issues} violation(s) of the Zero-Dot Policy.")
        sys.exit(1)

if __name__ == "__main__":
    test_zero_dot_policy()