#!/usr/bin/env python3
import glob
import os
import sys

import tinycss2

RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'

# Define our strict prefixes for the Tiers
TIER1_PREFIXES = ('--color-', '--space-', '--font-', '--size-', '--radius-', '--shadow-', '--time-', '--weight-', '--tracking-', '--leading-', '--z-')
TIER2_1_PREFIXES = ('--bg-', '--text-', '--border-', '--link-', '--icon-')

def get_tier(var_name):
    """Categorizes a CSS variable into its Architectural Tier based on prefix."""
    if var_name.startswith('--_'):
        return 3
    if var_name.startswith(TIER1_PREFIXES):
        return 1
    if var_name.startswith(TIER2_1_PREFIXES):
        return 2.1
    return 2.2

def get_var_references(tokens):
    """Recursively extracts all CSS variables referenced inside var() functions."""
    refs = set()
    for token in tokens:
        if token.type == 'function' and token.name == 'var':
            for arg in token.arguments:
                if arg.type == 'ident' and arg.value.startswith('--'):
                    refs.add(arg.value)
                    break # The first ident in var() is the reference, others are fallbacks
            # Check for nested var() inside fallbacks
            refs.update(get_var_references(token.arguments))
    return refs

def lint_tokens_file(filepath):
    """Validates global primitives and semantic relationships."""
    errors = []
    with open(filepath, 'r', encoding='utf-8') as f:
        rules = tinycss2.parse_stylesheet(f.read(), skip_comments=True, skip_whitespace=True)

    for rule in rules:
        if rule.type != 'qualified-rule':
            continue
            
        selector = tinycss2.serialize(rule.prelude).strip()
        decls = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
        
        for decl in decls:
            if decl.type != 'declaration' or not decl.name.startswith('--'):
                continue
                
            tier = get_tier(decl.name)
            refs = get_var_references(decl.value)

            if selector == ':root':
                if tier == 2.1:
                    # Tier 2.1 MUST ONLY reference Tier 1
                    for ref in refs:
                        if get_tier(ref) != 1:
                            errors.append(f"{filepath}:{decl.source_line} | '{decl.name}' (Tier 2.1) illegally references '{ref}'. It must only reference Tier 1 primitives.")
                elif tier == 2.2:
                    # Tier 2.2 MUST ONLY reference Tier 2.1
                    for ref in refs:
                        if get_tier(ref) != 2.1:
                            errors.append(f"{filepath}:{decl.source_line} | '{decl.name}' (Tier 2.2) illegally references '{ref}'. It must only reference Tier 2.1 global semantics.")
                            
            elif selector == '[data-theme="dark"]':
                if tier != 2.1:
                    errors.append(f"{filepath}:{decl.source_line} | '{decl.name}' cannot be redefined in Dark Mode. Only Tier 2.1 semantics (--bg-, --text-, etc.) are allowed here.")

    return errors

def lint_components(filepath):
    """Validates that components perfectly encapsulate variables (Tier 3)."""
    errors =[]
    with open(filepath, 'r', encoding='utf-8') as f:
        rules = tinycss2.parse_stylesheet(f.read(), skip_comments=True, skip_whitespace=True)

    def walk_rules(rule_list):
        for rule in rule_list:
            if rule.type == 'qualified-rule':
                decls = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
                for decl in decls:
                    if decl.type == 'declaration' and decl.name.startswith('--'):
                        if not decl.name.startswith('--_'):
                            errors.append(f"{filepath}:{decl.source_line} | Component variable '{decl.name}' must be private (Tier 3) and start with '--_'.")
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