#!/usr/bin/env python3
"""
CSS @provides Block Validation Linter (ERD Section 2.4)

Validates that parent components correctly override child component tokens:
- @provides section MUST ONLY contain Tier 2.2 custom property reassignments
- No standard CSS properties allowed in @provides
- No Tier 3 private variables in @provides
- Parent root MUST NOT redefine Tier 2.2 tokens globally
- Descendant selector MUST be used (.parent .child or .parent > .child)
- No fallbacks allowed (var(--a, var(--b)))
"""

import re
import sys
from pathlib import Path

import tinycss2

from _lib import RED, GREEN, YELLOW, RESET, get_token_tier, is_tier3_variable
from _lib.css_parser import get_var_references, build_provides_map, is_in_section


def is_descendant_selector(selector: str) -> bool:
    """
    Check if selector uses descendant combinator (space) or child combinator (>).
    This ensures proper targeting without global mutation.
    """
    # Match patterns like: .parent .child or .parent > .child
    # Must have at least one combinator (space or >)
    if ' > ' in selector or (' ' in selector and not selector.startswith('@')):
        return True
    return False


def has_var_fallback(tokens) -> bool:
    """Check if var() function has fallback values."""
    for token in tokens:
        if token.type == 'function' and token.name == 'var':
            # var() arguments: first is the variable, rest are fallbacks
            args = list(token.arguments)
            if len(args) > 1:
                return True
            # Check nested var() in arguments
            if has_var_fallback(token.arguments):
                return True
    return False


def lint_component_file(filepath: str) -> list[str]:
    """Lint a component CSS file for @provides violations."""
    errors = []

    # Pre-scan for @provides sections
    provides_map = build_provides_map(filepath)

    if not provides_map:
        return errors  # No @provides sections to validate

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rules = tinycss2.parse_stylesheet(content, skip_comments=True, skip_whitespace=True)

    for rule in rules:
        if rule.type != 'qualified-rule':
            continue

        selector = tinycss2.serialize(rule.prelude).strip()

        # Skip if not a component selector
        if not selector.startswith('.'):
            continue

        # Check if this selector is within @provides section
        # We check by looking at the declarations
        decls = tinycss2.parse_declaration_list(
            rule.content, skip_comments=False, skip_whitespace=True
        )

        # Find which declarations are in @provides section
        provides_decls = []
        for decl in decls:
            if decl.type == 'declaration' and is_in_section(decl.source_line, provides_map):
                provides_decls.append(decl)

        if not provides_decls:
            continue

        # Check Rule 1: Descendant selector requirement
        # @provides should be in a descendant selector block, not on parent root
        if not is_descendant_selector(selector):
            # This might be the parent root - check if it's redefining Tier 2.2
            for decl in provides_decls:
                if decl.name.startswith('--') and not decl.name.startswith('--_'):
                    tier = get_token_tier(decl.name)
                    if tier == 2:
                        errors.append(
                            f"{filepath}:{decl.source_line} | Parent root '{selector}' redefines "
                            f"Tier 2 token '{decl.name}'. Use descendant selector (e.g., '{selector} .child') "
                            f"to prevent global leakage."
                        )

        # Check Rule 2: @provides MUST ONLY contain Tier 2.2 custom property reassignments
        for decl in provides_decls:
            # No standard CSS properties
            if not decl.name.startswith('--'):
                errors.append(
                    f"{filepath}:{decl.source_line} | @provides section illegally declares "
                    f"standard property '{decl.name}'. @provides MUST ONLY contain "
                    f"Tier 2.2 custom property reassignments."
                )
                continue

            # No Tier 3 private variables
            if is_tier3_variable(decl.name):
                errors.append(
                    f"{filepath}:{decl.source_line} | @provides section illegally redefines "
                    f"Tier 3 private variable '{decl.name}'. @provides is for child "
                    f"Tier 2.2 overrides only."
                )
                continue

            # Check token tier
            tier = get_token_tier(decl.name)
            if tier == 1:
                errors.append(
                    f"{filepath}:{decl.source_line} | @provides section illegally redefines "
                    f"Tier 1 primitive '{decl.name}'. Only Tier 2.2 variables can be "
                    f"overridden for child components."
                )
            elif tier == 2.1:
                errors.append(
                    f"{filepath}:{decl.source_line} | @provides section illegally redefines "
                    f"Tier 2.1 global semantic '{decl.name}'. Only Tier 2.2 variables "
                    f"can be overridden for child components."
                )

            # Check Rule 3: No fallbacks allowed
            if has_var_fallback(decl.value):
                errors.append(
                    f"{filepath}:{decl.source_line} | @provides section uses fallback in "
                    f"'{decl.name}'. Fallbacks (var(--a, var(--b))) are forbidden to "
                    f"prevent hidden visual bugs."
                )

    return errors


def main():
    all_errors = []
    components_dir = Path(__file__).parent.parent / "themes" / "proseblock" / "assets" / "css" / "components"

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
        print(f"\n{YELLOW}⚠️  CSS @provides Block Warnings Found:{RESET}")
        print(f"{YELLOW}(These indicate technical debt - @provides should use descendant selectors){RESET}\n")
        for err in all_errors:
            print(f"  ⚠️  {err}")
        print(f"\n{YELLOW}Recommendation: @provides sections should use descendant selectors")
        print(f"(e.g., '.parent .child') instead of parent root redefinition to prevent global leakage.")
        print(f"This requires component refactoring to follow strict encapsulation.{RESET}")
        # Exit 0 for warnings (non-blocking)
        sys.exit(0)
    else:
        print(f"{GREEN}✅ @provides block validation passed for {len(component_files)} component file(s).{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
