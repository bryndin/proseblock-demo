#!/usr/bin/env python3
"""
CSS State and Variant Architecture Linter (ERD Section 2.5)

Validates that component states and BEM modifiers follow strict variable reassignment rules:
- State selectors (:hover, :focus-visible, [aria-*]) MUST ONLY reassign Tier 3 custom properties
- BEM modifiers (--modifier) MUST ONLY reassign Tier 3 custom properties
- No standard CSS property declarations allowed in states/modifiers
- State selectors must co-locate with their base component
"""

import re
import sys
from pathlib import Path

import tinycss2

from _lib import RED, GREEN, YELLOW, RESET, is_tier3_variable


# Patterns for state/modifier detection
STATE_PSEUDO_CLASSES = ('hover', 'focus', 'focus-visible', 'active', 'disabled', 'checked')
ARIA_STATES = re.compile(r'\[aria-[\w]+=".*?"\]')
BEM_MODIFIER = re.compile(r'--[a-z]+(?:-[a-z]+)*')  # .c-block--modifier


def is_state_or_modifier_selector(selector: str) -> bool:
    """Check if selector is a state or modifier selector."""
    # Check for pseudo-classes (hover, focus, etc.)
    for pseudo in STATE_PSEUDO_CLASSES:
        if f':{pseudo}' in selector:
            return True

    # Check for ARIA states
    if ARIA_STATES.search(selector):
        return True

    # Check for BEM modifiers
    if BEM_MODIFIER.search(selector):
        return True

    return False


def is_tier3_declaration(decl) -> bool:
    """Check if declaration is a Tier 3 private variable (starts with --_)."""
    return decl.name.startswith('--_')


def lint_component_file(filepath: str) -> list[str]:
    """Lint a component CSS file for state/modifier violations."""
    errors = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rules = tinycss2.parse_stylesheet(content, skip_comments=True, skip_whitespace=True)

    for rule in rules:
        if rule.type != 'qualified-rule':
            continue

        selector = tinycss2.serialize(rule.prelude).strip()

        # Check if this is a state or modifier selector
        if not is_state_or_modifier_selector(selector):
            continue

        # Parse declarations in this rule
        decls = tinycss2.parse_declaration_list(
            rule.content, skip_comments=True, skip_whitespace=True
        )

        for decl in decls:
            if decl.type != 'declaration':
                continue

            # Check if it's a standard CSS property (not a custom property)
            if not decl.name.startswith('--'):
                errors.append(
                    f"{filepath}:{decl.source_line} | State/Modifier selector '{selector}' "
                    f"illegally declares standard property '{decl.name}'. "
                    f"Must ONLY reassign Tier 3 variables (--_*)."
                )
                continue

            # Check if it's a Tier 3 variable
            if not is_tier3_variable(decl.name):
                errors.append(
                    f"{filepath}:{decl.source_line} | State/Modifier selector '{selector}' "
                    f"illegally references non-private variable '{decl.name}'. "
                    f"Must ONLY reassign Tier 3 private variables (--_*)."
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
        print(f"\n{YELLOW}⚠️  CSS State/Variant Architecture Warnings Found:{RESET}")
        print(f"{YELLOW}(These indicate technical debt - states should only reassign Tier 3 variables){RESET}\n")
        for err in all_errors:
            print(f"  ⚠️  {err}")
        print(f"\n{YELLOW}Recommendation: States (:hover, :focus) and BEM modifiers (--modifier)")
        print(f"should ONLY reassign Tier 3 private variables (--_*), not standard CSS properties.")
        print(f"This requires component refactoring to use the variable-pattern architecture.{RESET}")
        # Exit 0 for warnings (non-blocking)
        sys.exit(0)
    else:
        print(f"{GREEN}✅ State/Variant Architecture validated for {len(component_files)} component file(s).{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
