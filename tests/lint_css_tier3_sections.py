#!/usr/bin/env python3
"""
Lint test for Tier 3 Private Component Variables section validation.

Validates that component CSS follows the strict @api/@internal split:
- @api: --_* variables must ONLY reference Tier 2.2 Component Semantics
- @internal: --_* variables must ONLY reference Tier 1 Primitives or direct values
"""

import re
import sys
from pathlib import Path

import tinycss2

from _lib import (
    RED, GREEN, RESET,
    get_token_tier, is_tier2_token, get_var_references, detect_section_from_comments
)


def extract_component_name(selector: str) -> str | None:
    """Extract component name from selector like '.c-header' -> 'header'."""
    # Match BEM-style component prefixes: .c-header, .c-article-card, etc.
    match = re.search(r'\.c-([a-z]+(?:-[a-z]+)*)', selector)
    if match:
        return match.group(1)
    return None


def get_referenced_tier(var_ref: str) -> int | None:
    """Determine which tier a variable reference belongs to."""
    return get_token_tier(var_ref)


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
                    f"'@api: var1, var2', '@provides: var1, var2', or '@internal: var1, var2' section"
                )
                continue

            if section == 'provides':
                # @provides: Tier 3 private variables should NOT be here
                # @provides is for reassigning Tier 2.2 variables to child components
                errors.append(
                    f"{filepath}:{decl.source_line} | '{decl.name}' is a Tier 3 private variable "
                    f"and should not be in @provides section. "
                    f"@provides is for reassigning Tier 2.2 variables to child components."
                )
                continue

            refs = get_var_references(decl.value)

            if section == 'api':
                # @api: must ONLY reference Tier 2 variables (2.1 or 2.2)
                # No direct values, no Tier 1, no Tier 3
                if not refs:
                    errors.append(
                        f"{filepath}:{decl.source_line} | '{decl.name}' in @api section "
                        f"must reference a Tier 2 variable, not a direct value"
                    )
                else:
                    for ref in refs:
                        ref_tier = get_referenced_tier(ref)
                        if ref_tier == 1:
                            errors.append(
                                f"{filepath}:{decl.source_line} | '{decl.name}' in @api section "
                                f"illegally references Tier 1 primitive '{ref}'. "
                                f"Must only reference Tier 2 variables"
                            )
                        elif ref_tier == 3:
                            errors.append(
                                f"{filepath}:{decl.source_line} | '{decl.name}' in @api section "
                                f"illegally references another Tier 3 variable '{ref}'. "
                                f"Must only reference Tier 2 variables"
                            )

            elif section == 'internal':
                # @internal: must ONLY use direct values or Tier 1 primitives
                # No Tier 2 references allowed (neither 2.1 nor 2.2)
                for ref in refs:
                    ref_tier = get_referenced_tier(ref)
                    if ref_tier == 2:
                        errors.append(
                            f"{filepath}:{decl.source_line} | '{decl.name}' in @internal section "
                            f"illegally references Tier 2 variable '{ref}'. "
                            f"Must only use direct values or Tier 1 primitives"
                        )
                    elif ref_tier == 3:
                        errors.append(
                            f"{filepath}:{decl.source_line} | '{decl.name}' in @internal section "
                            f"illegally references another Tier 3 variable '{ref}'. "
                            f"Must only use direct values or Tier 1 primitives"
                        )

            # Note: @provides section validation happens above (catches --_* variables)
            # Actual @provides content (Tier 2.2 reassignments) is validated by lint_css_tiers.py

    return errors


def main():
    all_errors = []
    # Resolves to: ../themes/proseblock/assets/css/components
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
        print(f"\n{RED}🚨 Tier 3 CSS Section Violations Found:{RESET}")
        for err in all_errors:
            print(f"  ❌ {err}")
        print(f"\n{RED}Fix: Ensure @api: section only references Tier 2.2 variables,")
        print(f"      @provides: section reassigns Tier 2.2 for child components,")
        print(f"      and @internal: section only uses direct values or Tier 1 primitives.{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}✅ Tier 3 CSS section validation passed for {len(component_files)} component file(s).{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
