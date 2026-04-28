"""
Shared CSS token parser for lint tools.

Parses tokens.css to extract actual Tier 1, Tier 2.1, and Tier 2.2 tokens
for validation against the canonical source of truth.
"""

from pathlib import Path
from typing import Set

import tinycss2


def parse_tokens_css() -> tuple[Set[str], Set[str], Set[str]]:
    """
    Parse tokens.css and return sets of Tier 1, Tier 2.1, and Tier 2.2 token names.

    Returns:
        (tier1_tokens, tier21_tokens, tier22_tokens)
    """
    tokens_path = Path(__file__).parent.parent.parent / "themes" / "proseblock" / "assets" / "css" / "tokens.css"

    with open(tokens_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tier1_tokens: Set[str] = set()
    tier21_tokens: Set[str] = set()
    tier22_tokens: Set[str] = set()

    # Parse with line numbers to track section boundaries
    rules = tinycss2.parse_stylesheet(content, skip_comments=False, skip_whitespace=False)

    for rule in rules:
        if rule.type != 'qualified-rule':
            continue

        # Only parse :root for token definitions (data-theme only overrides)
        selector = tinycss2.serialize(rule.prelude).strip()
        if selector != ':root':
            continue

        # Parse content with comments to detect section markers
        items = tinycss2.parse_declaration_list(
            rule.content, skip_comments=False, skip_whitespace=False
        )

        current_tier: str | None = None

        for item in items:
            if item.type == 'comment':
                text = item.value.lower()
                if 'tier 1' in text or 'tier1' in text:
                    current_tier = 'tier1'
                elif 'tier 2.1' in text or 'tier2.1' in text:
                    current_tier = 'tier21'
                elif 'tier 2.2' in text or 'tier2.2' in text:
                    current_tier = 'tier22'
                continue

            if item.type != 'declaration':
                continue

            var_name = item.name
            if not var_name.startswith('--'):
                continue

            # Assign to appropriate tier set based on current section
            if current_tier == 'tier1':
                tier1_tokens.add(var_name)
            elif current_tier == 'tier21':
                tier21_tokens.add(var_name)
            elif current_tier == 'tier22':
                tier22_tokens.add(var_name)

    return tier1_tokens, tier21_tokens, tier22_tokens


# Cache the parsed tokens
_TIER1_TOKENS: Set[str] | None = None
_TIER21_TOKENS: Set[str] | None = None
_TIER22_TOKENS: Set[str] | None = None


def _ensure_loaded():
    """Lazy-load and cache token sets."""
    global _TIER1_TOKENS, _TIER21_TOKENS, _TIER22_TOKENS
    if _TIER1_TOKENS is None:
        _TIER1_TOKENS, _TIER21_TOKENS, _TIER22_TOKENS = parse_tokens_css()


def get_tier1_tokens() -> Set[str]:
    """Return set of Tier 1 primitive token names."""
    _ensure_loaded()
    return _TIER1_TOKENS.copy()


def get_tier21_tokens() -> Set[str]:
    """Return set of Tier 2.1 global semantic token names."""
    _ensure_loaded()
    return _TIER21_TOKENS.copy()


def get_tier22_tokens() -> Set[str]:
    """Return set of Tier 2.2 component semantic token names."""
    _ensure_loaded()
    return _TIER22_TOKENS.copy()


def get_tier2_tokens() -> Set[str]:
    """Return combined set of Tier 2.1 and Tier 2.2 token names."""
    _ensure_loaded()
    return _TIER21_TOKENS | _TIER22_TOKENS


def get_token_tier(var_name: str) -> int | None:
    """
    Determine which tier a variable belongs to.

    Returns:
        1 for Tier 1 primitives
        2 for Tier 2 (2.1 or 2.2) semantics
        3 for Tier 3 private component variables (--_*)
        None for unknown/non-token variables
    """
    if not var_name.startswith('--'):
        return None

    if var_name.startswith('--_'):
        return 3

    _ensure_loaded()

    if var_name in _TIER1_TOKENS:
        return 1

    if var_name in _TIER21_TOKENS or var_name in _TIER22_TOKENS:
        return 2

    # Unknown custom property - could be undefined or dynamic
    return None


def is_tier1_token(var_name: str) -> bool:
    """Check if variable is a defined Tier 1 primitive."""
    return get_token_tier(var_name) == 1


def is_tier2_token(var_name: str) -> bool:
    """Check if variable is a defined Tier 2 semantic token."""
    return get_token_tier(var_name) == 2


def is_tier3_variable(var_name: str) -> bool:
    """Check if variable is a Tier 3 private component variable."""
    return var_name.startswith('--_')
