#!/usr/bin/env python3
"""
Linter for detecting unused Tier 3 (private) CSS variables.

Detects:
1. Unused variables: --_* variables defined but never referenced via var()
2. Dead code chains: Variables only used in other variable definitions,
   never in actual CSS properties (color, margin, etc.)
"""

import glob
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Set, Dict, List, Tuple, Optional

from _lib import RED, GREEN, YELLOW, BLUE, BOLD, RESET

# Configuration
CSS_DIR = 'themes/proseblock/assets/css'


def remove_css_comments(text: str) -> str:
    """Strip CSS block comments to avoid matching commented-out code."""
    return re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)


def parse_css_file(filepath: str) -> Tuple[Set[Tuple[str, str, int]], Dict[str, List[Tuple[str, int, str]]], Dict[str, List[Tuple[str, int, str]]]]:
    """
    Parse a CSS file to extract:
    - Tier 3 variable definitions: (var_name, filepath, line_num)
    - Variable-to-variable references: var_name -> [(referencing_var, line_num, filepath)]
    - Variable-to-property references: var_name -> [(property, line_num, filepath)]
    """
    defined_vars = set()  # (var_name, filepath, line_num)
    var_to_var_refs = defaultdict(list)  # var_name -> [(referencing_var, line_num, filepath)]
    var_to_prop_refs = defaultdict(list)  # var_name -> [(property, line_num, filepath)]

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match CSS rules: selector { ... }
    # This is a simplified parser - handles most common cases
    rule_pattern = re.compile(
        r'([^{]+)\{([^}]*)\}',
        re.DOTALL
    )

    # Pattern to match var() usages
    var_usage_pattern = re.compile(r'var\(\s*(--[\w-]+)')

    for match in rule_pattern.finditer(content):
        selector = match.group(1).strip()
        declarations = match.group(2)
        # Position right after the opening brace '{'
        decls_start_pos = match.end(1) + 1

        # Parse declarations within this rule
        decls = []

        # Remove comments from declarations to avoid parsing colons in comments
        declarations_clean = remove_css_comments(declarations)

        # Split by semicolon to get individual declarations
        raw_decls = declarations.split(';')
        raw_decls_clean = declarations_clean.split(';')
        current_pos = 0

        for i, (decl, decl_clean) in enumerate(zip(raw_decls, raw_decls_clean)):
            decl = decl.strip()
            decl_clean = decl_clean.strip()
            if not decl:
                current_pos += len(raw_decls[i]) + 1  # +1 for semicolon
                continue

            # Find the colon position in the cleaned declaration (no comments)
            colon_pos = decl_clean.find(':')
            if colon_pos == -1:
                current_pos += len(raw_decls[i]) + 1
                continue

            prop = decl_clean[:colon_pos].strip()
            value = decl_clean[colon_pos + 1:].strip()

            # Calculate line number by finding the actual property position in original declarations
            # Use the raw (unstripped) declaration to find position
            raw_decl = raw_decls[i]
            prop_pos_in_raw = raw_decl.find(prop)
            if prop_pos_in_raw >= 0:
                # Find position in original content
                prop_start_in_content = decls_start_pos + current_pos + prop_pos_in_raw
                decl_line = content[:prop_start_in_content].count('\n') + 1
            else:
                # Fallback: use block start line
                decl_line = content[:decls_start_pos].count('\n') + 1

            current_pos += len(raw_decls[i]) + 1  # +1 for semicolon

            decls.append((prop, value, decl_line))

        # Process declarations
        seen_props = set()
        for prop, value, decl_line in decls:
            # Check if this is a Tier 3 variable definition (only record first occurrence)
            if prop.startswith('--_') and prop not in seen_props:
                seen_props.add(prop)
                defined_vars.add((prop, filepath, decl_line))

            # Find all var() usages in the value
            for var_match in var_usage_pattern.finditer(value):
                ref_var = var_match.group(1)

                # Only track Tier 3 variables
                if not ref_var.startswith('--_'):
                    continue

                # Check if this usage is in a variable definition or a real property
                if prop.startswith('--'):
                    # This is a variable-to-variable reference
                    var_to_var_refs[ref_var].append((prop, decl_line, filepath))
                else:
                    # This is a variable-to-property reference
                    var_to_prop_refs[ref_var].append((prop, decl_line, filepath))

    return defined_vars, var_to_var_refs, var_to_prop_refs


def find_reachable_vars(var_to_var_refs: Dict[str, List], var_to_prop_refs: Dict[str, List],
                        all_defined: Set[str]) -> Set[str]:
    """
    Find all variables that are transitively reachable from properties.
    Uses BFS to trace backwards from variables used in properties.
    """
    # Start with variables directly used in properties
    reachable = set(var_to_prop_refs.keys())

    # Build reverse graph: var -> variables that reference it
    # Actually we need: var -> variables it references (dependencies)
    # Then trace backwards: start from vars used in props, find what refs them

    # Build forward graph: var -> vars it depends on
    forward_graph = defaultdict(set)
    for var_name, refs in var_to_var_refs.items():
        for ref_var, _, _ in refs:
            forward_graph[var_name].add(ref_var)

    # Build reverse graph: var -> vars that depend on it
    reverse_graph = defaultdict(set)
    for var_name, deps in forward_graph.items():
        for dep in deps:
            reverse_graph[dep].add(var_name)

    # BFS: find all variables that eventually lead to a property
    visited = set(reachable)
    queue = list(reachable)

    while queue:
        current = queue.pop(0)

        # Find all variables that reference 'current'
        for var_name in all_defined:
            if var_name in forward_graph and current in forward_graph[var_name]:
                if var_name not in visited:
                    visited.add(var_name)
                    queue.append(var_name)

    return visited


def main():
    print(f"{BLUE}{BOLD}--- Linting Unused Tier 3 CSS Variables -----------------------------------{RESET}")

    # Collect all CSS files
    css_files = glob.glob(os.path.join(CSS_DIR, '**/*.css'), recursive=True)

    if not css_files:
        print(f"{YELLOW}⚠️  No CSS files found in {CSS_DIR}{RESET}")
        sys.exit(0)

    # Collect data from all files
    all_defined = set()  # (var_name, filepath, line_num)
    all_var_to_var = defaultdict(list)
    all_var_to_prop = defaultdict(list)

    # Per-file tracking for local unused detection
    # file_defined[filepath] = set of var_names defined in that file
    file_defined = defaultdict(set)
    # file_used[filepath] = set of var_names used (via var()) in that file
    file_used = defaultdict(set)

    for filepath in css_files:
        defined, var_to_var, var_to_prop = parse_css_file(filepath)
        all_defined.update(defined)
        for var, refs in var_to_var.items():
            all_var_to_var[var].extend(refs)
        for var, refs in var_to_prop.items():
            all_var_to_prop[var].extend(refs)

        # Track per-file usage
        for var_name, fpath, _ in defined:
            if fpath == filepath:
                file_defined[filepath].add(var_name)
        for var_name, refs in var_to_var.items():
            for _, _, ref_path in refs:
                if ref_path == filepath:
                    file_used[filepath].add(var_name)
        for var_name, refs in var_to_prop.items():
            for _, _, ref_path in refs:
                if ref_path == filepath:
                    file_used[filepath].add(var_name)

    if not all_defined:
        print(f"{GREEN}✅ No Tier 3 variables found in {len(css_files)} CSS files.{RESET}")
        sys.exit(0)

    # Find unused variables (defined but never referenced globally)
    defined_names = {v[0] for v in all_defined}
    referenced_names = set(all_var_to_var.keys()) | set(all_var_to_prop.keys())
    unused_names = defined_names - referenced_names

    # Find dead code chains
    reachable_from_props = find_reachable_vars(all_var_to_var, all_var_to_prop, defined_names)
    dead_chain_names = defined_names - reachable_from_props - unused_names

    # Filter out unused from dead_chain (they're reported separately)
    dead_chain_names = dead_chain_names - unused_names

    # Find locally unused: defined in a file but not used in that same file
    # This catches variables that are meant to be local but aren't used locally
    locally_unused = set()  # (var_name, filepath, line_num)
    for filepath in css_files:
        defined_in_file = file_defined[filepath]
        used_in_file = file_used[filepath]
        locally_unused_names = defined_in_file - used_in_file

        # Only flag if used somewhere else (otherwise it's caught by unused_names)
        for var_name, fpath, line_num in all_defined:
            if fpath == filepath and var_name in locally_unused_names and var_name not in unused_names:
                locally_unused.add((var_name, filepath, line_num))

    # Build output
    all_issues = []

    for var_name, filepath, line_num in all_defined:
        if var_name in unused_names:
            all_issues.append((var_name, filepath, line_num, 'unused'))
        elif var_name in dead_chain_names:
            all_issues.append((var_name, filepath, line_num, 'dead_chain'))

    # Add locally unused issues
    for var_name, filepath, line_num in locally_unused:
        all_issues.append((var_name, filepath, line_num, 'locally_unused'))

    if not all_issues:
        print(f"{GREEN}✅ All {len(all_defined)} Tier 3 variables are properly utilized.{RESET}")
        print(f"   (Checked {len(css_files)} CSS files)")
        sys.exit(0)

    # Print results
    unused = [i for i in all_issues if i[3] == 'unused']
    dead = [i for i in all_issues if i[3] == 'dead_chain']
    local = [i for i in all_issues if i[3] == 'locally_unused']

    if unused:
        print(f"\n{YELLOW}⚠️  Unused Variables ({len(unused)}):{RESET}")
        print(f"{YELLOW}   These variables are defined but never referenced via var().{RESET}\n")
        for var_name, filepath, line_num, _ in sorted(unused):
            rel_path = os.path.relpath(filepath)
            print(f"   - {BOLD}{var_name}{RESET} in {rel_path}:{line_num}")

    if local:
        print(f"\n{YELLOW}⚠️  Locally Unused Variables ({len(local)}):{RESET}")
        print(f"{YELLOW}   These variables are defined in a file but not used in that same file.{RESET}")
        print(f"{YELLOW}   They are used elsewhere, but may indicate a component architecture issue.{RESET}\n")
        for var_name, filepath, line_num, _ in sorted(local):
            rel_path = os.path.relpath(filepath)
            print(f"   - {BOLD}{var_name}{RESET} in {rel_path}:{line_num}")

    if dead:
        print(f"\n{YELLOW}⚠️  Dead Code Chains ({len(dead)}):{RESET}")
        print(f"{YELLOW}   These variables are only used in other variable definitions.{RESET}")
        print(f"{YELLOW}   They never affect actual CSS rendering (dead code).{RESET}\n")
        for var_name, filepath, line_num, _ in sorted(dead):
            rel_path = os.path.relpath(filepath)
            print(f"   - {BOLD}{var_name}{RESET} in {rel_path}:{line_num}")
            # Show what references this variable
            refs = all_var_to_var.get(var_name, [])
            if refs:
                for ref_var, ref_line, ref_path in refs[:3]:  # Show first 3
                    ref_rel = os.path.relpath(ref_path)
                    print(f"     referenced by: {ref_var} ({ref_rel}:{ref_line})")

    print(f"\n{BLUE}ℹ️  Total: {len(unused)} unused, {len(local)} locally unused, {len(dead)} dead chain variables out of {len(all_defined)} Tier 3 definitions.{RESET}")
    print(f"   Checked {len(css_files)} CSS files.")

    sys.exit(0)


if __name__ == '__main__':
    main()
