#!/usr/bin/env python3
import os
import re
import sys

from _lib import RED, GREEN, RESET

file_path = 'themes/proseblock/layouts/_partials/head/css.html'

if not os.path.exists(file_path):
    print(f"{RED}Error: File {file_path} not found.{RESET}")
    sys.exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Specifically target the $layerNames slice assignment line
match = re.search(r'\$layerNames\s*:=\s*slice\s+(.*?)(?:-\}\}|\}\})', content)

if not match:
    print(f"{RED}Error: Could not find the '$layerNames := slice ...' declaration in {file_path}.{RESET}")
    sys.exit(1)

# Extract only the double-quoted strings from that specific line
keys_found = re.findall(r'"([^"]+)"', match.group(1))

expected_order =['reset', 'tokens', 'base', 'layout', 'components', 'utilities']

if keys_found != expected_order:
    print(f"{RED}Error: CSS Layers in $layerNames are missing or defined out of order.{RESET}")
    print(f"  Expected: {expected_order}")
    print(f"  Found:    {keys_found}")
    print(f"{RED}Fix: Ensure the $layerNames slice explicitly defines: reset, tokens, base, layout, components, utilities.{RESET}")
    sys.exit(1)

print(f"{GREEN}✅ $layerNames configuration matches the strict architectural cascade: {', '.join(expected_order)}.{RESET}")
sys.exit(0)