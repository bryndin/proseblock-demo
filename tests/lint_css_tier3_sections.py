#!/usr/bin/env python3
"""
Lint test for Tier 3 Private Component Variables section validation.

Validates that component CSS follows the strict Arguments/Configuration split:
- Arguments: --_* variables must ONLY reference Tier 2.2 Component Semantics
- Configuration: --_* variables must ONLY reference Tier 1 Primitives or direct values
"""

import re
import sys
from pathlib import Path

import tinycss2

RED = '\033[31m'
GREEN = '\033[32m'
RESET = '\033[0m'

# Tier 1 Primitives prefixes (from ERD 1.4)
TIER1_PREFIXES = (
    '--color-', '--space-', '--font-', '--size-', '--radius-',
    '--shadow-', '--time-', '--weight-', '--tracking-', '--leading-', '--z-'
)

# Section delimiter patterns (supports both old and new formats)
# Old: /* *** Arguments (The Public API) */, /* *** Configuration (Internal Styling) */
# New: /* @api: var1, var2 */, /* @internal: var1, var2 */
ARGUMENTS_PATTERN = re.compile(r'(?:\*\*\*\s*Arguments|@api:)', re.IGNORECASE)
CONFIG_PATTERN = re.compile(r'(?:\*\*\*\s*Configuration|@internal:)', re.IGNORECASE)


def extract_component_name(selector: str) -> str | None:
    """Extract component name from selector like '.c-header' -> 'header'."""
    # Match BEM-style component prefixes: .c-header, .c-article-card, etc.
    match = re.search(r'\.c-([a-z]+(?:-[a-z]+)*)', selector)
    if match:
        return match.group(1)
    return None


def get_referenced_tier(var_ref: str) -> int | None:
    """Determine which tier a variable reference belongs to."""
    if var_ref.startswith('--_'):
        return 3
    if var_ref.startswith(TIER1_PREFIXES):
        return 1
    return 2  # Tier 2 (could be 2.1 or 2.2)


def is_tier22_for_component(var_ref: str, component_name: str) -> bool:
    """Check if var_ref is a Tier 2.2 variable for the given component."""
    expected_prefix = f'--{component_name}-'
    return var_ref.startswith(expected_prefix)


def get_var_references(tokens):
    """Recursively extracts all CSS variables referenced inside var() functions."""
    refs = []
    for token in tokens:
        if token.type == 'function' and token.name == 'var':
            for arg in token.arguments:
                if arg.type == 'ident' and arg.value.startswith('--'):
                    refs.append(arg.value)
                    break  # First ident is the main reference, rest are fallbacks
            # Check for nested var() inside fallbacks
            refs.extend(get_var_references(token.arguments))
    return refs


def detect_section_from_comments(decls, start_idx: int) -> str | None:
    """
    Detect if we're in Arguments or Configuration section based on preceding comments.
    Returns 'arguments', 'configuration', or None.
    """
    # Look backward through declarations to find the most recent section comment
    for i in range(start_idx - 1, -1, -1):
        decl = decls[i]
        if decl.type == 'comment':
            text = decl.value
            if ARGUMENTS_PATTERN.search(text):
                return 'arguments'
            if CONFIG_PATTERN.search(text):
                return 'configuration'
    return None


def lint_component_file(filepath: str) -> list[str]:
    """Lint a component CSS file for Tier 3 section violations."""
    errors = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rules = tinycss2.parse_stylesheet(content, skip_comments=False, skip_whitespace=True)

    for rule in rules:
        if rule.type != 'qualified-rule':
            continue

        selector = tinycss2.serialize(rule.prelude).strip()
        component_name = extract_component_name(selector)

        if not component_name:
            continue  # Not a component selector

        decls = list(tinycss2.parse_declaration_list(
            rule.content, skip_comments=False, skip_whitespace=True
        ))

        for i, decl in enumerate(decls):
            if decl.type != 'declaration' or not decl.name.startswith('--_'):
                continue

            section = detect_section_from_comments(decls, i)

            if section is None:
                # Variable not in a marked section - this is an error
                errors.append(
                    f"{filepath}:{decl.source_line} | '{decl.name}' must be in either "
                    f"'@api: var1, var2' or '@internal: var1, var2' section"
                )
                continue

            refs = get_var_references(decl.value)

            if section == 'arguments':
                # Arguments: must ONLY reference this component's Tier 2.2 variables
                # No direct values, no Tier 1, no Tier 2.1, no other Tier 2.2
                if not refs:
                    errors.append(
                        f"{filepath}:{decl.source_line} | '{decl.name}' in Arguments section "
                        f"must reference var(--{component_name}-*), not a direct value"
                    )
                else:
                    for ref in refs:
                        ref_tier = get_referenced_tier(ref)
                        if ref_tier == 1:
                            errors.append(
                                f"{filepath}:{decl.source_line} | '{decl.name}' in Arguments section "
                                f"illegally references Tier 1 primitive '{ref}'. "
                                f"Must only reference --{component_name}-* (Tier 2.2)"
                            )
                        elif ref_tier == 2:
                            if not is_tier22_for_component(ref, component_name):
                                errors.append(
                                    f"{filepath}:{decl.source_line} | '{decl.name}' in Arguments section "
                                    f"illegally references '{ref}'. "
                                    f"Must only reference this component's Tier 2.2 variables (--{component_name}-*)"
                                )
                        elif ref_tier == 3:
                            errors.append(
                                f"{filepath}:{decl.source_line} | '{decl.name}' in Arguments section "
                                f"illegally references another Tier 3 variable '{ref}'. "
                                f"Must only reference --{component_name}-* (Tier 2.2)"
                            )

            elif section == 'configuration':
                # Configuration: must ONLY use direct values or Tier 1 primitives
                # No Tier 2 references allowed (neither 2.1 nor 2.2)
                for ref in refs:
                    ref_tier = get_referenced_tier(ref)
                    if ref_tier == 2:
                        errors.append(
                            f"{filepath}:{decl.source_line} | '{decl.name}' in Configuration section "
                            f"illegally references Tier 2 variable '{ref}'. "
                            f"Must only use direct values or Tier 1 primitives ({', '.join(TIER1_PREFIXES)})"
                        )
                    elif ref_tier == 3:
                        errors.append(
                            f"{filepath}:{decl.source_line} | '{decl.name}' in Configuration section "
                            f"illegally references another Tier 3 variable '{ref}'. "
                            f"Must only use direct values or Tier 1 primitives"
                        )

    return errors


def main():
    all_errors = []
    # Resolves to: ../themes/theme-x/assets/css/components
    components_dir = Path(__file__).parent.parent / "themes" / "theme-x" / "assets" / "css" / "components"

    if not components_dir.exists():
        print(f"{RED}Error: Directory not found: {components_dir}{RESET}")
        sys.exit(1)

    component_files = list(components_dir.rglob("*.css"))

    if not component_files:
        print(f"{GREEN}✅ No component files to lint.{RESET}")
        sys.exit(0)

    for comp_file in component_files:
        all_errors.extend(lint_component_file(str(comp_file)))

    if all_errors:
        print(f"\n{RED}🚨 Tier 3 CSS Section Violations Found:{RESET}")
        for err in all_errors:
            print(f"  ❌ {err}")
        print(f"\n{RED}Fix: Ensure @api: section only references --{{component}}-* (Tier 2.2),")
        print(f"      and @internal: section only uses direct values or Tier 1 primitives.{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}✅ Tier 3 CSS section validation passed for {len(component_files)} component file(s).{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
