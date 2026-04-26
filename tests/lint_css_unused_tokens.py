#!/usr/bin/env python3
import glob
import os
import re
import sys

# ANSI Colors
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
BOLD = '\033[1m'
RESET = '\033[0m'

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
    
    # Miscellaneous Constraints / Utilities
    r'^--text-(2?xs|sm|base|lg|[2-7]xl|tiny|display|hero)$',
    r'^--max-w-.*',
    r'^--height-.*',
    r'^--scale-.*',
    r'^--border-width$'
]

COMPILED_IGNORES =[re.compile(p) for p in IGNORE_LIST]

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

all_defined = get_defined_tokens(TOKENS_FILE)
all_used, file_count = get_used_tokens(CSS_DIR)

# Find the difference: tokens that exist in tokens.css but are never called via var()
unreferenced = all_defined - all_used

# Apply the allowlist filter
warnings_to_print = [t for t in unreferenced if not any(regex.match(t) for regex in COMPILED_IGNORES)]

# Sort the filtered list for consistent, readable output
warnings_to_print = sorted(list(warnings_to_print))

if not warnings_to_print:
    print(f"{GREEN}✅ All semantic tokens are utilized correctly across {file_count} CSS files.{RESET}")
    sys.exit(0)

print(f"\n{YELLOW}⚠️  Unused CSS Tokens Found ({len(warnings_to_print)}):{RESET}")
print(f"{YELLOW}These tokens are defined in tokens.css but never referenced via var() in your CSS.{RESET}\n")

for token in warnings_to_print:
    print(f"  - {token}")

print(f"\n{BLUE}ℹ️  Note: The linter is currently configured to only warn.{RESET}")
print(f"{BLUE}If you want to be more strict and fail the 'make lint' CI step in the future,{RESET}")
print(f"{BLUE}change the exit code below from sys.exit(0) to sys.exit(1).{RESET}")

# For now, exit with 0 so it doesn't break the build pipeline
sys.exit(0)