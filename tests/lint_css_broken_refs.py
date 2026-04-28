#!/usr/bin/env python3
"""
Lint CSS for broken token references.

Detects when CSS files reference var(--token-name) where the token is not defined in tokens.css.
This is a BLOCKING rule - exits with code 1 if broken references are found.
"""
import glob
import os
import re
import sys

# ANSI Colors for consistent output
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
BOLD = '\033[1m'
RESET = '\033[0m'

# Configuration
TOKENS_FILE = 'themes/proseblock/assets/css/tokens.css'
CSS_DIR = 'themes/proseblock/assets/css'


def remove_css_comments(text):
    """Strips CSS block comments to avoid matching commented-out variables."""
    return re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)


def get_defined_tokens(filepath):
    """Extracts all tokens defined globally in the tokens file."""
    defined = set()
    if not os.path.exists(filepath):
        print(f"{RED}Error: Tokens file not found at {filepath}{RESET}")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = remove_css_comments(f.read())

    # Match declarations like `--token-name: value;`
    matches = re.findall(r'(--[\w-]+)\s*:', content)
    defined.update(matches)

    return defined


def get_local_definitions(lines):
    """Extract --_* variable definitions that are local to this file."""
    local_defs = set()
    # Pattern to match local var definitions like `--_name: value;`
    def_pattern = re.compile(r'(--_[\w-]+)\s*:')

    for line in lines:
        clean_line = remove_css_comments(line)
        for match in def_pattern.finditer(clean_line):
            local_defs.add(match.group(1))

    return local_defs


def get_var_references_with_lines(filepath):
    """
    Extract all var() references from a CSS file with their line numbers.
    Also returns locally-defined --_* variables.

    Returns:
        Tuple of (references_list, local_definitions_set)
        where references_list is list of (token_name, line_number) tuples
    """
    references = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Get locally-defined --_* variables
    local_defs = get_local_definitions(lines)

    # Pattern to match var(--token-name) - captures the token name
    var_pattern = re.compile(r'var\(\s*(--[\w-]+)')

    for line_num, line in enumerate(lines, start=1):
        # Skip comment-only lines
        stripped = line.strip()
        if stripped.startswith('/*') and stripped.endswith('*/'):
            continue
        if stripped.startswith('//'):
            continue

        # Remove inline comments for matching
        clean_line = remove_css_comments(line)

        # Find all var() references in this line
        for match in var_pattern.finditer(clean_line):
            token_name = match.group(1)
            references.append((token_name, line_num))

    return references, local_defs


def main():
    print(f"{BLUE}{BOLD}--- Linting CSS Broken Token References -------------------------------------{RESET}")

    # Get all defined tokens
    defined_tokens = get_defined_tokens(TOKENS_FILE)
    print(f"  Found {len(defined_tokens)} defined tokens in {TOKENS_FILE}")

    # Scan all CSS files for broken references
    css_files = glob.glob(os.path.join(CSS_DIR, '**/*.css'), recursive=True)

    broken_refs = []  # List of (filepath, line_num, token_name)

    for filepath in css_files:
        # Skip the tokens file itself (it references other tokens legitimately)
        if os.path.basename(filepath) == 'tokens.css':
            continue

        refs, local_defs = get_var_references_with_lines(filepath)

        for token_name, line_num in refs:
            # Check if token is either globally defined or locally defined in this file
            if token_name not in defined_tokens and token_name not in local_defs:
                # Get relative path for cleaner output
                rel_path = os.path.relpath(filepath, os.path.dirname(CSS_DIR))
                broken_refs.append((rel_path, line_num, token_name))

    if not broken_refs:
        print(f"{GREEN}✅ No broken token references found across {len(css_files)} CSS files.{RESET}")
        sys.exit(0)

    # Sort by filepath then line number for consistent output
    broken_refs.sort(key=lambda x: (x[0], x[1]))

    print(f"\n{RED}❌ Broken Token References Found ({len(broken_refs)}):{RESET}")
    print(f"{YELLOW}These var() references point to tokens that don't exist in {TOKENS_FILE}:{RESET}\n")

    for filepath, line_num, token_name in broken_refs:
        print(f"  {filepath}:{line_num}: {RED}{token_name}{RESET}")

    print(f"\n{RED}This is a blocking error. Fix the broken references above.{RESET}")
    sys.exit(1)


if __name__ == '__main__':
    main()
