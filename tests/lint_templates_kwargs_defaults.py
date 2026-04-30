#!/usr/bin/env python3
"""
Test script to verify that dictionary arguments passed to partials have defaults.

Usage:
    python3 tests/lint_templates_kwargs_defaults.py

This script checks that when receiving a dictionary of arguments in partials
(e.g., $kwargs := .), a default empty dictionary is provided to prevent nil errors.

Bad example: {{- $kwargs := . }}
Good example: {{- $kwargs := . | default dict }}
"""

import re
import sys
from pathlib import Path

def preserve_newlines(match):
    """Replaces matched multiline comments with empty lines to keep line numbers accurate."""
    return '\n' * match.group(0).count('\n')

def test_kwargs_defaults():
    layouts_dir = Path(__file__).parent.parent / "themes" / "proseblock" / "layouts"

    if not layouts_dir.exists():
        print(f"Directory not found: {layouts_dir}")
        sys.exit(1)

    # Matches Hugo comments: {{-? /* ... */ -?}}
    comment_pattern = re.compile(r'{{-?\s*/\*.*?\*/\s*-?}}', re.DOTALL)

    # Matches Go template tags: {{ ... }}
    tag_pattern = re.compile(r'{{(.*?)}}', re.DOTALL)

    # Matches string literals (to remove them and avoid false positives)
    string_pattern = re.compile(r'(".*?"|\'.*?\'|`.*?`)', re.DOTALL)

    # Pattern for $kwargs assignment WITHOUT default dict
    # Matches: $kwargs := . (optionally with whitespace and dashes)
    # but NOT followed by | default
    kwargs_no_default_pattern = re.compile(
        r'\$([a-zA-Z_]\w*)\s*(?::=|=)\s*\.(?!\w)(?!\s*\|\s*default)'
    )

    issues = 0

    for filepath in layouts_dir.rglob('*.html'):
        text = filepath.read_text(encoding='utf-8')
        text = comment_pattern.sub(preserve_newlines, text)

        for match in tag_pattern.finditer(text):
            tag_content = match.group(1).strip('- \t\n\r')
            line_num = text[:match.start()].count('\n') + 1

            # Remove string literals to avoid false positives
            cleaned = string_pattern.sub('""', tag_content)

            # Check for $kwargs := . without | default dict
            for km in kwargs_no_default_pattern.finditer(cleaned):
                var_name = km.group(1)
                # Only flag the standard $kwargs variable name
                if var_name == 'kwargs':
                    print(f"❌ {filepath.relative_to(layouts_dir.parent.parent)}:{line_num}")
                    print(f"   Violation: '${var_name} := .' is missing a default value.")
                    print("   Refactor to: '$kwargs := . | default dict'")
                    issues += 1

    if issues == 0:
        print("✅ All clear! No missing default dict violations found.")
        sys.exit(0)
    else:
        print(f"\n🚨 Linting failed: Found {issues} violation(s) of the kwargs defaults rule.")
        sys.exit(1)

if __name__ == "__main__":
    test_kwargs_defaults()
