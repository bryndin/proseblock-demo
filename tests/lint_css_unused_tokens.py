#!/usr/bin/env python3
import glob
import os
import re
import sys

from _lib import RED, GREEN, YELLOW, BLUE, BOLD, RESET

# Configuration
TOKENS_FILE = 'themes/proseblock/assets/css/tokens.css'
CSS_DIR = 'themes/proseblock/assets/css'

# Hardcoded allowlist for token scales that we expect to be unused but need for API completeness.
# Since your architecture defines full primitives scales (Tier 1), we safely ignore them here.
IGNORE_LIST =[
    # Tier 1 Primitives
    r'^--color-.*',
    r'^--space-.*',
    r'^--font-.*',
    r'^--size-.*',
    r'^--radius-.*',
    r'^--shadow-.*',
    r'^--duration-.*',
    r'^--ease-.*',
    r'^--weight-.*',
    r'^--tracking-.*',
    r'^--leading-.*',
    r'^--z-.*',
    r'^--motion-shift.*',
    r'^--opacity.*',
    
    # Miscellaneous Constraints / Utilities
    # r'^--text-(2?xs|sm|base|lg|[2-7]xl|tiny|display|hero)$',
    # r'^--max-w-.*',
    # r'^--height-.*',
    # r'^--scale-.*',
    # r'^--border-width$'
]

COMPILED_IGNORES =[re.compile(p) for p in IGNORE_LIST]

def remove_css_comments(text):
    """Strips CSS block comments to avoid matching commented-out variables."""
    return re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

def get_defined_tokens(filepath):
    """Extracts all tokens defined globally in the tokens file with their locations."""
    defined = {}  # token -> (filepath, line_number)
    if not os.path.exists(filepath):
        print(f"{RED}Error: Tokens file not found at {filepath}{RESET}")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Process line by line to track line numbers
    for line_num, line in enumerate(lines, start=1):
        # Remove comments from this line only (simplistic but sufficient)
        clean_line = re.sub(r'/\*.*?\*/', '', line)
        # Match declarations like `--token-name: value;`
        matches = re.findall(r'(--[\w-]+)\s*:', clean_line)
        for token in matches:
            if token not in defined:
                defined[token] = (filepath, line_num)

    return defined

def get_used_tokens(directory):
    """Finds all var(--token-name) usages across all CSS files."""
    used = set()
    css_files = glob.glob(os.path.join(directory, '**/*.css'), recursive=True)
    
    for filepath in css_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = remove_css_comments(f.read())
            # Match var(--token-name)
            matches = re.findall(r'var\(\s*(--[\w-]+)', content)
            used.update(matches)
            
    return used, len(css_files)

# --- Execution ---
print(f"{BLUE}{BOLD}--- Linting Unused CSS Tokens ----------------------------------------------{RESET}")

all_defined_with_locations = get_defined_tokens(TOKENS_FILE)
all_defined = set(all_defined_with_locations.keys())
all_used, file_count = get_used_tokens(CSS_DIR)

# Find the difference: tokens that exist in tokens.css but are never called via var()
unreferenced = all_defined - all_used

# Apply the allowlist filter, keeping location info
warnings = [(t, all_defined_with_locations[t]) for t in unreferenced if not any(regex.match(t) for regex in COMPILED_IGNORES)]

# Sort by file path, then by line number for consistent output
warnings = sorted(warnings, key=lambda x: (x[1][0], x[1][1]))

if not warnings:
    print(f"{GREEN}✅ All semantic tokens are utilized correctly across {file_count} CSS files.{RESET}")
    sys.exit(0)

print(f"\n{YELLOW}⚠️  Unused CSS Tokens Found ({len(warnings)}):{RESET}")
print(f"{YELLOW}These tokens are defined in tokens.css but never referenced via var() in your CSS.{RESET}\n")

for token, (filepath, line_num) in warnings:
    print(f"  {filepath}:{line_num}  {YELLOW}{token}{RESET}")

print(f"\n{BLUE}ℹ️  Note: The linter is currently configured to only warn.{RESET}")
print(f"{BLUE}If you want to be more strict and fail the 'make lint' CI step in the future,{RESET}")
print(f"{BLUE}change the exit code below from sys.exit(0) to sys.exit(1).{RESET}")

# For now, exit with 0 so it doesn't break the build pipeline
sys.exit(0)