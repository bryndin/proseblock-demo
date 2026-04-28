"""
Shared CSS parsing utilities for lint tools.

Provides common functionality for parsing CSS component files including:
- Variable reference extraction from var() functions
- Section detection (@api, @internal, @provides)
- Component file parsing with tinycss2
"""

import re
from pathlib import Path
from typing import List, Set, Tuple

import tinycss2


# Section marker patterns
API_PATTERN = re.compile(r'@api:', re.IGNORECASE)
INTERNAL_PATTERN = re.compile(r'@internal:', re.IGNORECASE)
PROVIDES_PATTERN = re.compile(r'@provides', re.IGNORECASE)
SECTION_END_PATTERN = re.compile(r'@\s*(api|internal|provides)', re.IGNORECASE)


def get_var_references(tokens) -> Set[str]:
    """
    Recursively extracts all CSS variables referenced inside var() functions.

    Args:
        tokens: tinycss2 token list (from declaration.value or rule.content)

    Returns:
        Set of variable names (e.g., {'--color-primary', '--space-4'})
    """
    refs = set()
    for token in tokens:
        if token.type == 'function' and token.name == 'var':
            for arg in token.arguments:
                if arg.type == 'ident' and arg.value.startswith('--'):
                    refs.add(arg.value)
                    break  # First ident is the reference, rest are fallbacks
            # Check for nested var() inside fallbacks
            refs.update(get_var_references(token.arguments))
    return refs


def build_provides_map(filepath: str | Path) -> List[Tuple[int, int]]:
    """
    Pre-scans component CSS files to detect @provides section ranges.

    A @provides section starts at a comment containing @provides and ends
    at the next comment starting with @api, @internal, @provides, or the
    end of the rule block.

    Args:
        filepath: Path to CSS component file

    Returns:
        List of (start_line, end_line) tuples marking @provides sections
    """
    sections = []
    in_provides = False
    provides_start = None

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, start=1):
        # Check if this line contains a section marker
        if SECTION_END_PATTERN.search(line):
            if in_provides and provides_start is not None:
                # End the current @provides section
                sections.append((provides_start, line_num - 1))
                in_provides = False
                provides_start = None

            # Check if starting a new @provides section
            if PROVIDES_PATTERN.search(line):
                in_provides = True
                provides_start = line_num

    # If @provides continues to end of file
    if in_provides and provides_start is not None:
        sections.append((provides_start, len(lines) + 1000))

    return sections


def is_in_section(line_num: int, section_map: List[Tuple[int, int]]) -> bool:
    """Check if a given line number falls within any section range."""
    for start, end in section_map:
        if start <= line_num <= end:
            return True
    return False


def detect_section_from_comments(decls, start_idx: int) -> str | None:
    """
    Detect if we're in @api, @provides, or @internal section based on preceding comments.

    Args:
        decls: List of declarations from tinycss2.parse_declaration_list
        start_idx: Index of current declaration to check

    Returns:
        'api' for @api, 'provides' for @provides, 'internal' for @internal, or None
    """
    for i in range(start_idx - 1, -1, -1):
        decl = decls[i]
        if decl.type == 'comment':
            text = decl.value
            if API_PATTERN.search(text):
                return 'api'
            if PROVIDES_PATTERN.search(text):
                return 'provides'
            if INTERNAL_PATTERN.search(text):
                return 'internal'
    return None


def parse_component_declarations(filepath: str | Path):
    """
    Parse a component CSS file and yield relevant declarations.

    Yields tuples of (selector, declaration, line_num) for declarations
    that define CSS custom properties (--*).

    Args:
        filepath: Path to CSS component file

    Yields:
        (selector: str, declaration: Declaration, line_num: int)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rules = tinycss2.parse_stylesheet(content, skip_comments=False, skip_whitespace=True)

    for rule in rules:
        if rule.type != 'qualified-rule':
            continue

        selector = tinycss2.serialize(rule.prelude).strip()

        decls = list(tinycss2.parse_declaration_list(
            rule.content, skip_comments=False, skip_whitespace=True
        ))

        for decl in decls:
            if decl.type != 'declaration':
                continue
            if not decl.name.startswith('--'):
                continue

            yield selector, decl, decl.source_line
