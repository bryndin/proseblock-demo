#!/usr/bin/env python3
"""
CSS 3-Tier Architecture Linter
Validates CSS custom properties follow the strict ERD-defined architecture.

Tier Detection Strategy (Solution C - Section-Based):
- tokens.css: Parses /* === TIER X.X: ... */ comments to map line ranges to tiers.
  This is robust against naming changes and requires no prefix conventions.
- Component files: Validates Tier 3 encapsulation with special @provides handling.

Enforces reference rules:
- Tier 2.1 may only reference Tier 1
- Tier 2.2 may only reference Tier 2.1
- Only Tier 2.1 can be redefined in [data-theme="dark"]

Component Validation:
- Variables outside @provides sections: Must use --_ prefix (Tier 3, private)
- Variables inside @provides sections: May be Tier 2.2 (reassigning global semantics)
"""
import glob
import os
import re
import sys

import tinycss2

from _lib import (
    RED, GREEN, YELLOW, RESET,
    get_token_tier, is_tier1_token, is_tier2_token,
)
from _lib.css_parser import (
    get_var_references,
    build_provides_map,
    is_in_section,
)

# Section marker regex: matches "TIER X.X:" or "TIER X:" anywhere in a comment line
TIER_SECTION_RE = re.compile(r'TIER\s+(\d+(?:\.\d+)?):', re.IGNORECASE)


def build_tier_section_map(filepath):
    """
    Pre-scans tokens.css to build a line-range-to-tier mapping based on section comments.
    Returns a list of (start_line, end_line, tier_number) tuples.
    """
    sections = []
    current_tier = None
    section_start = None

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, start=1):
        match = TIER_SECTION_RE.search(line)
        if match:
            # Close previous section
            if current_tier is not None and section_start is not None:
                sections.append((section_start, line_num - 1, current_tier))
            # Start new section
            current_tier = float(match.group(1))
            section_start = line_num

    # Close final section (extends to end of file)
    if current_tier is not None and section_start is not None:
        sections.append((section_start, len(lines) + 1000, current_tier))

    return sections


def get_tier_from_line(line_num, tier_map):
    """Looks up the tier for a given line number using the section map."""
    for start, end, tier in tier_map:
        if start <= line_num <= end:
            return tier
    return None


def get_tier(var_name, line_num=None, tier_map=None):
    """
    Categorizes a CSS variable into its Architectural Tier.
    Uses section-based detection (line_num + tier_map) for tokens.css.
    Falls back to prefix-based for Tier 3 (private component variables).
    """
    # Tier 3 is always detected by prefix (private component variables)
    if var_name.startswith('--_'):
        return 3

    # For tokens.css: use section-based detection
    if tier_map is not None and line_num is not None:
        tier = get_tier_from_line(line_num, tier_map)
        if tier is not None:
            return tier

    return None

def lint_tokens_file(filepath):
    """Validates global primitives and semantic relationships using section-based tier detection."""
    errors = []

    # Build section map from comments (line-range -> tier mapping)
    tier_map = build_tier_section_map(filepath)

    # First pass: build variable name -> tier mapping from :root for dark mode validation
    var_tier_map = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        rules = tinycss2.parse_stylesheet(content, skip_comments=True, skip_whitespace=True)

    for rule in rules:
        if rule.type != 'qualified-rule':
            continue

        selector = tinycss2.serialize(rule.prelude).strip()
        if selector != ':root':
            continue

        decls = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
        for decl in decls:
            if decl.type != 'declaration' or not decl.name.startswith('--'):
                continue
            tier = get_tier(decl.name, line_num=decl.source_line, tier_map=tier_map)
            if tier is not None:
                var_tier_map[decl.name] = tier

    # Second pass: validate all rules
    for rule in rules:
        if rule.type != 'qualified-rule':
            continue

        selector = tinycss2.serialize(rule.prelude).strip()
        decls = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)

        for decl in decls:
            if decl.type != 'declaration' or not decl.name.startswith('--'):
                continue

            line_num = decl.source_line
            refs = get_var_references(decl.value)

            if selector == ':root':
                tier = get_tier(decl.name, line_num=line_num, tier_map=tier_map)

                if tier == 2.1:
                    # Tier 2.1 may reference Tier 1 or Tier 2.1
                    for ref in refs:
                        ref_tier = var_tier_map.get(ref)
                        if ref_tier not in (1, 2.1):
                            errors.append(f"{filepath}:{line_num} | '{decl.name}' (Tier 2.1) illegally references '{ref}' (Tier {ref_tier}). It must only reference Tier 1 primitives or other Tier 2.1 variables.")
                elif tier == 2.2:
                    # Tier 2.2 may reference Tier 2.1 OR Tier 1 primitives
                    # Tier 2.1 is preferred, but direct Tier 1 references are allowed
                    # when no appropriate Tier 2.1 semantic exists
                    for ref in refs:
                        ref_tier = var_tier_map.get(ref)
                        if ref_tier not in (1, 2.1):
                            errors.append(f"{filepath}:{line_num} | '{decl.name}' (Tier 2.2) illegally references '{ref}' (Tier {ref_tier}). It must only reference Tier 2.1 global semantics or Tier 1 primitives.")

            elif selector == '[data-theme="dark"]':
                # Dark mode: look up tier by variable name (from :root definitions)
                tier = var_tier_map.get(decl.name)
                if tier != 2.1:
                    errors.append(f"{filepath}:{line_num} | '{decl.name}' cannot be redefined in Dark Mode. Only Tier 2.1 semantics are allowed here.")

    return errors

def lint_components(filepath):
    """
    Validates component CSS variable encapsulation.

    Rules:
    - Variables in @provides sections: Can only be Tier 2.2 (reassigning global
      component semantics for child components). Tier 1 and Tier 2.1 cannot
      be reassigned in components.
    - Variables elsewhere: Must be Tier 3 (start with '--_') - private to this component.
    """
    errors = []

    # Pre-scan for @provides sections
    provides_map = build_provides_map(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        rules = tinycss2.parse_stylesheet(f.read(), skip_comments=True, skip_whitespace=True)

    def walk_rules(rule_list):
        for rule in rule_list:
            if rule.type == 'qualified-rule':
                decls = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
                for decl in decls:
                    if decl.type == 'declaration' and decl.name.startswith('--'):
                        line_num = decl.source_line
                        var_name = decl.name
                        is_private = var_name.startswith('--_')
                        in_provides = is_in_section(line_num, provides_map)

                        if in_provides:
                            # @provides section: only Tier 2.2 variables allowed
                            tier = get_token_tier(var_name)
                            if tier == 1:
                                errors.append(f"{filepath}:{line_num} | Cannot reassign '{var_name}' (Tier 1 Primitive) in component. Only Tier 2.2 variables can be overridden in @provides.")
                            elif tier == 2.1:
                                errors.append(f"{filepath}:{line_num} | Cannot reassign '{var_name}' (Tier 2.1 Global Semantic) in component. Only Tier 2.2 variables can be overridden in @provides.")
                            elif tier == 3:
                                errors.append(f"{filepath}:{line_num} | Private variable '{var_name}' (Tier 3) should not be in @provides. Move to @api or @internal section.")
                        else:
                            # Outside @provides: must be private (Tier 3)
                            if not is_private:
                                errors.append(f"{filepath}:{line_num} | Component variable '{var_name}' must be private (Tier 3) and start with '--_'. Use @provides section for Tier 2.2 overrides.")
            elif rule.type == 'at-rule' and rule.content:
                # Handle nested rules (e.g., inside @media)
                sub_rules = tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True)
                walk_rules(sub_rules)

    walk_rules(rules)
    return errors

# --- Execution ---
all_errors =[]

# 1. Lint Tokens
tokens_file = 'themes/proseblock/assets/css/tokens.css'
if os.path.exists(tokens_file):
    all_errors.extend(lint_tokens_file(tokens_file))
else:
    print(f"{YELLOW}Warning: {tokens_file} not found. Skipping tokens linting.{RESET}")

# 2. Lint Components
component_files = glob.glob('themes/proseblock/assets/css/components/**/*.css', recursive=True)
for comp_file in component_files:
    all_errors.extend(lint_components(comp_file))

# Output Results
if all_errors:
    print(f"\n{RED}🚨 CSS Architecture Violations Found:{RESET}")
    for err in all_errors:
        print(f"  ❌ {err}")
    sys.exit(1)
else:
    print(f"{GREEN}✅ 3-Tier CSS Architecture validated perfectly across {len(component_files) + 1} files.{RESET}")
    sys.exit(0)