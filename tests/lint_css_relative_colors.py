#!/usr/bin/env python3
"""
CSS Relative Color Syntax Linter (ERD Section 2.6)

Validates that alpha-muted colors use CSS Relative Color Syntax with OKLCH:
- Pattern: oklch(from var(--token) l c h / var(--opacity))
- Must use Tier 1 opacity primitives (--opacity-*)
- Warns about non-relative color syntax for alpha transparency

Note: This linter validates syntax patterns. WCAG contrast checking
requires browser rendering and is not performed here.
"""

import glob
import os
import re
import sys

from _lib import RED, GREEN, YELLOW, RESET


# Patterns for detecting alpha/opacity usage
OPACITY_TOKENS = re.compile(r'var\(\s*(--opacity-[\w-]+)\s*\)')

# Pattern for valid OKLCH relative color syntax with alpha
# Matches: oklch(from var(--some-token) l c h / var(--opacity-*))
OKLCH_RELATIVE_PATTERN = re.compile(
    r'oklch\(\s*from\s+var\([^)]+\)\s+l\s+c\s+h\s*/\s*var\(\s*--opacity-[\w-]+\s*\)\s*\)',
    re.IGNORECASE
)

# Pattern for any oklch() usage
OKLCH_ANY_PATTERN = re.compile(r'oklch\([^)]+\)', re.IGNORECASE)

# Pattern for rgba/hsla with CSS variables (old approach to avoid)
LEGACY_ALPHA_PATTERN = re.compile(
    r'(rgba|hsla)\(\s*var\([^)]+\)\s*,\s*var\(\s*--opacity-',
    re.IGNORECASE
)


def extract_line_from_content(content: str, line_num: int) -> str:
    """Extract a specific line from content."""
    lines = content.split('\n')
    if 1 <= line_num <= len(lines):
        return lines[line_num - 1].strip()
    return ""


def lint_css_file(filepath: str) -> list[tuple[int, str, str]]:
    """
    Lint a CSS file for relative color syntax violations.
    Returns list of (line_num, line_content, message) tuples.
    
    According to ERD 2.6: Relative color syntax should be used when muting
    semantic tokens with alpha transparency, not for Tier 1 primitive definitions.
    """
    warnings = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        if line.strip().startswith('/*') or line.strip().startswith('*'):
            continue

        # Check for legacy rgba/hsla with opacity tokens (should use oklch)
        if LEGACY_ALPHA_PATTERN.search(line):
            warnings.append((
                line_num,
                line.strip(),
                "Uses legacy rgba()/hsla() for alpha. Use oklch(from var(--token) l c h / var(--opacity-*)) instead."
            ))
            continue

        # Check for oklch() with var() references that don't use relative syntax
        # This catches patterns like: oklch(var(--token) / alpha) or oklch(27% 0.015 230deg / var(--opacity))
        # where relative syntax (oklch(from var(--token) l c h / alpha)) should be used
        oklch_matches = OKLCH_ANY_PATTERN.findall(line)
        for match in oklch_matches:
            # Only check if it contains both var() and opacity tokens
            # (indicating a semantic token being muted with alpha)
            has_var = 'var(--' in match
            has_opacity = OPACITY_TOKENS.search(match) is not None

            if has_var and has_opacity:
                # This is a semantic token with alpha - should use relative syntax
                if not OKLCH_RELATIVE_PATTERN.search(match):
                    warnings.append((
                        line_num,
                        line.strip(),
                        f"Alpha-muted semantic token should use relative color syntax. "
                        f"Use: oklch(from var(--token) l c h / var(--opacity-*))"
                    ))

    return warnings


def main():
    css_dir = 'themes/proseblock/assets/css'
    css_files = glob.glob(os.path.join(css_dir, '**/*.css'), recursive=True)

    if not css_files:
        print(f"{YELLOW}Warning: No CSS files found in {css_dir}{RESET}")
        sys.exit(0)

    all_warnings = []

    for filepath in css_files:
        file_warnings = lint_css_file(filepath)
        for line_num, line_content, message in file_warnings:
            all_warnings.append((filepath, line_num, line_content, message))

    if all_warnings:
        print(f"\n{YELLOW}⚠️  CSS Relative Color Syntax Warnings Found:{RESET}")
        print(f"{YELLOW}(These are warnings, not errors. Fix for stricter compliance.){RESET}\n")

        for filepath, line_num, line_content, message in all_warnings:
            # Show truncated line content
            display_line = line_content[:80] + "..." if len(line_content) > 80 else line_content
            print(f"  {filepath}:{line_num}")
            print(f"    {YELLOW}{message}{RESET}")
            print(f"    Code: {display_line}\n")

        print(f"{YELLOW}Recommendation: Use oklch(from var(--token) l c h / var(--opacity-*))")
        print(f"for all alpha-muted colors to maintain consistency with light/dark themes.{RESET}")

        # Exit with 0 for warnings (non-blocking)
        sys.exit(0)
    else:
        print(f"{GREEN}✅ All CSS relative color syntax patterns validated ({len(css_files)} files).{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
