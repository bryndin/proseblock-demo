#!/usr/bin/env python3
"""
Test script for the Explicit Parameter Declaration (API Contract) best practice.

Usage:
    python3 tests/test_explicit_params.py

This script checks that all references to site.Params and page.Params are declared
as local variables at the top of each template file, not hidden inside business logic.
Violations occur when these global/page identifiers are accessed directly in 
conditional blocks, assignments within logic, or any non-declaration context.
"""

import re
import sys
from pathlib import Path

def preserve_newlines(match):
    """Replaces matched multiline comments with empty lines to keep line numbers accurate."""
    return '\n' * match.group(0).count('\n')

def test_explicit_params():
    layouts_dir = Path(__file__).parent.parent / "themes" / "theme-x" / "layouts"
    
    if not layouts_dir.exists():
        print(f"Directory not found: {layouts_dir}")
        sys.exit(1)

    # Matches Hugo comments: {{-? /* ... */ -?}}
    comment_pattern = re.compile(r'{{-?\s*/\*.*?\*/\s*-?}}', re.DOTALL)
    
    # Matches Go template tags: {{ ... }}
    tag_pattern = re.compile(r'{{(.*?)}}', re.DOTALL)
    
    # Matches string literals (to remove them)
    string_pattern = re.compile(r'(".*?"|\'.*?\'|`.*?`)', re.DOTALL)
    
    # Variable declaration patterns (allowed at top of file):
    # $var := expr or $var = expr (including with pipelines like | default)
    var_declaration_pattern = re.compile(
        r'^\s*(?:\$[a-zA-Z_]\w*)\s*(?::=|=)\s*(.*)'
    )
    
    # Patterns for violations:
    # site.Params.X anywhere except the RHS of a declaration
    site_params_pattern = re.compile(r'site\.Params\.[a-zA-Z_]\w*')
    
    # page.Params.X or $page.Params.X anywhere except the RHS of a declaration
    page_params_pattern = re.compile(r'(?:\$)?page\.Params\.[a-zA-Z_]\w*')
    
    # Direct .Params.X access (implicit page context)
    dot_params_pattern = re.compile(r'\.Params\.[a-zA-Z_]\w*')
    
    issues = 0
    
    for filepath in layouts_dir.rglob('*.html'):
        text = filepath.read_text(encoding='utf-8')
        text = comment_pattern.sub(preserve_newlines, text)
        
        # Track if we're still in the "declaration zone" at the top
        # The declaration zone ends when we see a non-declaration tag
        in_declaration_zone = True
        
        for match in tag_pattern.finditer(text):
            tag_content = match.group(1).strip('- \t\n\r')
            line_num = text[:match.start()].count('\n') + 1
            
            # Skip empty tags
            if not tag_content:
                continue
            
            # Remove string literals to avoid false positives
            cleaned = string_pattern.sub('""', tag_content)
            
            # Check if this is a variable declaration
            # Declarations look like: $var := ... or $var = ...
            is_declaration = bool(var_declaration_pattern.match(cleaned))
            
            # Once we hit a non-declaration, we've left the declaration zone
            if in_declaration_zone and not is_declaration:
                in_declaration_zone = False
            
            # Check for violations based on zone
            if not in_declaration_zone or not is_declaration:
                # Outside declaration zone OR not a declaration: any params access is a violation
                
                # Check site.Params
                for sm in site_params_pattern.finditer(cleaned):
                    # Exception: if it's in a declaration (RHS), it's allowed
                    if is_declaration and sm.group(0) in cleaned.split('=')[-1].split(':=')[-1]:
                        continue
                    
                    print(f"❌ {filepath.relative_to(layouts_dir.parent.parent)}:{line_num}")
                    print(f"   Violation: '{sm.group(0)}' accessed outside declaration zone.")
                    print(f"   Extract into: '$var := {sm.group(0)} | default <value>' at top of file")
                    issues += 1
                
                # Check $page.Params or page.Params
                for pm in page_params_pattern.finditer(cleaned):
                    # Exception: if it's in a declaration (RHS), it's allowed
                    if is_declaration and pm.group(0) in cleaned.split('=')[-1].split(':=')[-1]:
                        continue
                    
                    print(f"❌ {filepath.relative_to(layouts_dir.parent.parent)}:{line_num}")
                    print(f"   Violation: '{pm.group(0)}' accessed outside declaration zone.")
                    print(f"   Extract into: '$var := {pm.group(0)} | default <value>' at top of file")
                    issues += 1
                
                # Check bare .Params.X
                for dm in dot_params_pattern.finditer(cleaned):
                    # Skip if part of $page.Params (already handled) or page.Params
                    match_text = dm.group(0)
                    if 'page' + match_text in cleaned or '$page' + match_text in cleaned:
                        continue
                    # Skip if in declaration RHS
                    if is_declaration and match_text in cleaned.split('=')[-1].split(':=')[-1]:
                        continue
                    
                    print(f"❌ {filepath.relative_to(layouts_dir.parent.parent)}:{line_num}")
                    print(f"   Violation: '{match_text}' accessed outside declaration zone.")
                    print(f"   Extract into: '$var := {match_text}' at top of file")
                    issues += 1
            
            # Additional check: even in declaration zone, ensure we're ASSIGNING to a var
            # (not just referencing params in an expression without capturing)
            if in_declaration_zone and not is_declaration:
                # In declaration zone but not a declaration - accessing params here is wrong
                for sm in site_params_pattern.finditer(cleaned):
                    print(f"❌ {filepath.relative_to(layouts_dir.parent.parent)}:{line_num}")
                    print(f"   Violation: '{sm.group(0)}' used in non-declaration context.")
                    print(f"   Must be captured: '$var := {sm.group(0)} | default <value>'")
                    issues += 1
    
    if issues == 0:
        print("✅ All clear! No explicit parameter declaration violations found.")
        sys.exit(0)
    else:
        print(f"\n🚨 Linting failed: Found {issues} violation(s) of the Explicit Parameter Declaration rule.")
        sys.exit(1)

if __name__ == "__main__":
    test_explicit_params()
