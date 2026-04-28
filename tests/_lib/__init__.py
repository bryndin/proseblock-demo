"""
Shared utilities for CSS linting tools.

This package contains helper modules for parsing CSS tokens and component files.
Files in _lib/ are NOT executable linters - they are imported by lint_*.py scripts.
"""

# ANSI Colors for consistent output across all linters
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
BOLD = '\033[1m'
RESET = '\033[0m'

from .css_tokens import (
    get_tier1_tokens,
    get_tier2_tokens,
    get_tier21_tokens,
    get_tier22_tokens,
    get_token_tier,
    is_tier1_token,
    is_tier2_token,
    is_tier3_variable,
)

from .css_parser import (
    get_var_references,
    build_provides_map,
    is_in_section,
    detect_section_from_comments,
    parse_component_declarations,
    API_PATTERN,
    INTERNAL_PATTERN,
    PROVIDES_PATTERN,
)

__all__ = [
    # Colors
    'RED', 'GREEN', 'YELLOW', 'BLUE', 'BOLD', 'RESET',
    # css_tokens exports
    'get_tier1_tokens',
    'get_tier2_tokens',
    'get_tier21_tokens',
    'get_tier22_tokens',
    'get_token_tier',
    'is_tier1_token',
    'is_tier2_token',
    'is_tier3_variable',
    # css_parser exports
    'get_var_references',
    'build_provides_map',
    'is_in_section',
    'detect_section_from_comments',
    'parse_component_declarations',
    'API_PATTERN',
    'INTERNAL_PATTERN',
    'PROVIDES_PATTERN',
]
