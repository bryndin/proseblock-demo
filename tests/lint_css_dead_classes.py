#!/usr/bin/env python3
"""
Linter for detecting dead CSS classes.

Detects:
1. Classes defined in CSS but never used in templates or JS
2. Classes inside themes/proseblock directory that aren't used within that directory
   (indicating potential orphaned component code)
"""

import glob
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Set, Dict, List, Tuple

from _lib import RED, GREEN, YELLOW, BLUE, BOLD, RESET

# Configuration
THEME_DIR = 'themes/proseblock'
CSS_DIR = f'{THEME_DIR}/assets/css'
LAYOUTS_DIR = f'{THEME_DIR}/layouts'
JS_DIR = f'{THEME_DIR}/assets/js'


def extract_classes_from_selector(selector: str) -> Set[str]:
    """
    Extract class names from a CSS selector.
    Handles complex selectors like:
    - .class-name
    - .class-name:hover, .class-name[aria-disabled="true"]
    - .class-a, .class-b
    - .class-a .class-b (descendant)
    - .class-a>.class-b (child)
    - .class-a.is-open (compound)
    """
    classes = set()

    # Normalize selector: remove pseudo-classes, pseudo-elements, and attribute selectors
    # but preserve the class names

    # Remove content inside [...] (attribute selectors) but keep the class part before it
    # e.g., .class[attr] -> .class
    selector = re.sub(r'\[.*?\]', '', selector)

    # Remove pseudo-classes (:hover, :focus, etc.) and pseudo-elements (::before, etc.)
    # Be careful to keep class names that might contain colons in BEM
    # Valid BEM: .c-class__element--modifier
    # We need to remove :hover, :focus, ::before but not break class names

    # Remove :: pseudo-elements first
    selector = re.sub(r'::[\w-]+', '', selector)

    # Remove : pseudo-classes (but be careful with BEM modifiers that use --)
    # We look for : followed by valid CSS identifier characters
    # and remove the pseudo-class part
    selector = re.sub(r':[\w-]+', '', selector)

    # Now extract all class selectors
    # Match . followed by valid CSS identifier characters
    class_pattern = re.compile(r'\.([a-zA-Z_][\w-]*)')

    for match in class_pattern.finditer(selector):
        classes.add(match.group(1))

    return classes


def parse_css_file(filepath: str) -> Dict[str, List[Tuple[int, str]]]:
    """
    Parse a CSS file and extract all class selectors.
    Supports @lint-ignore comments to skip classes used in built output/markdown.
    Returns: {class_name: [(line_num, full_selector), ...]}
    """
    classes_found = defaultdict(list)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to detect @lint-ignore comments
    LINT_IGNORE_PATTERN = re.compile(r'@lint-ignore')

    # Remove CSS comments but preserve newlines to maintain line numbers
    def replace_comment_preserve_newlines(match):
        # Replace comment with same number of newlines to preserve line structure
        newline_count = match.group(0).count('\n')
        return '\n' * newline_count

    content_clean = re.sub(r'/\*.*?\*/', replace_comment_preserve_newlines, content, flags=re.DOTALL)

    # Use a position-based parser to handle nested braces correctly
    pos = 0
    length = len(content_clean)

    while pos < length:
        # Find the next opening brace
        brace_pos = content_clean.find('{', pos)
        if brace_pos == -1:
            break

        # Get the selector (everything between previous closing brace and this opening brace)
        selector = content_clean[pos:brace_pos].strip()

        # Calculate line number
        line_num = content_clean[:brace_pos].count('\n') + 1

        # Check for @lint-ignore in the original content between previous pos and current selector
        # We use the original content to see the actual comments
        original_segment_start = len(content_clean[:pos].replace('\n', ''))
        # Need to map position back to original - approximate by counting newlines
        line_start = content_clean[:pos].count('\n')
        line_end = line_num
        # Get that segment from original content
        original_lines = content.split('\n')[line_start:line_end]
        original_segment = '\n'.join(original_lines)
        has_lint_ignore = bool(LINT_IGNORE_PATTERN.search(original_segment))

        # Find the matching closing brace (handle nesting)
        brace_count = 1
        end_pos = brace_pos + 1

        while end_pos < length and brace_count > 0:
            if content_clean[end_pos] == '{':
                brace_count += 1
            elif content_clean[end_pos] == '}':
                brace_count -= 1
            end_pos += 1

        # Process the selector if it's not an @-rule and not lint-ignored
        if selector and not selector.startswith('@') and not has_lint_ignore:
            # Handle multiple selectors separated by comma
            for sel in selector.split(','):
                sel = sel.strip()
                if not sel:
                    continue

                classes = extract_classes_from_selector(sel)
                for cls in classes:
                    classes_found[cls].append((line_num, sel))

        # Move to after the closing brace
        pos = end_pos

    return dict(classes_found)


def find_classes_in_template(filepath: str) -> Set[str]:
    """
    Find all class references in an HTML/template file.
    Looks for class="..." and other common patterns.
    """
    classes_found = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern 1: class="class-name" or class='class-name' or class="class1 class2"
    # Handles both double and single quotes
    class_attr_pattern = re.compile(
        r'class\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    for match in class_attr_pattern.finditer(content):
        class_value = match.group(1)
        # Split on whitespace for multiple classes
        for cls in class_value.split():
            cls = cls.strip()
            if cls:
                classes_found.add(cls)

    # Pattern 2: JavaScript class manipulation
    # classList.add('class-name'), classList.remove('class-name')
    # element.className = 'class-name'
    js_class_pattern = re.compile(
        r'classList\.(?:add|remove|toggle)\s*\(\s*["\']([^"\']+)["\']\s*\)',
        re.IGNORECASE
    )

    for match in js_class_pattern.finditer(content):
        classes_found.add(match.group(1))

    # Pattern 3: Hugo's class function: class "class-name"
    # This is specific to Hugo templates
    hugo_class_pattern = re.compile(
        r'\bclass\s+["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    for match in hugo_class_pattern.finditer(content):
        class_value = match.group(1)
        for cls in class_value.split():
            cls = cls.strip()
            if cls:
                classes_found.add(cls)

    # Pattern 4: Hugo dict values that are BEM classes (modifier, wrapper_class, etc.)
    # Catches: modifier "c-hero--404", wrapper_class "c-card--featured", etc.
    hugo_dict_class_pattern = re.compile(
        r'\b(?:modifier|wrapper_class|wrapper|class|icon_class|btn_class)\s+["\']([a-zA-Z_][\w-]*)["\']',
        re.IGNORECASE
    )

    for match in hugo_dict_class_pattern.finditer(content):
        cls = match.group(1)
        if cls.startswith(('c-', 'l-', 'u-', 'is-', 'has-', 'js-')):
            classes_found.add(cls)

    # Pattern 5: Any quoted BEM-style class in templates (broader heuristic)
    # Matches classes like c-hero__title-prefix, l-site__sidebar, is-open
    # Handles both regular quotes (" or ') and escaped quotes (\" or \')
    bem_string_pattern = re.compile(
        r'(?:\x22|\\\x22|\x27|\\\x27)([a-zA-Z_][\w-]*(?:_[\w-]+|-[\w-]+)+)(?:\x22|\\\x22|\x27|\\\x27)'
    )

    for match in bem_string_pattern.finditer(content):
        potential_class = match.group(1)
        # Check if it looks like a BEM class
        if potential_class.startswith(('c-', 'l-', 'u-', 'is-', 'has-', 'js-')):
            classes_found.add(potential_class)

    return classes_found


def find_classes_in_js(filepath: str) -> Set[str]:
    """
    Find all class references in a JavaScript file.
    Looks for common patterns of class manipulation.
    """
    classes_found = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove comments to avoid false positives
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    # Pattern 1: classList.add('class-name'), classList.remove('class-name'), etc.
    classlist_pattern = re.compile(
        r'classList\.(?:add|remove|toggle|contains)\s*\(\s*["\']([^"\']+)["\']\s*\)'
    )

    for match in classlist_pattern.finditer(content):
        classes_found.add(match.group(1))

    # Pattern 2: element.className = 'class-name'
    # element.className += ' class-name'
    classname_pattern = re.compile(
        r'className\s*(?:=|\+=)\s*["\']([^"\']+)["\']'
    )

    for match in classname_pattern.finditer(content):
        class_value = match.group(1)
        for cls in class_value.split():
            cls = cls.strip()
            if cls:
                classes_found.add(cls)

    # Pattern 3: setAttribute('class', 'class-name')
    setattr_pattern = re.compile(
        r'setAttribute\s*\(\s*["\']class["\']\s*,\s*["\']([^"\']+)["\']\s*\)'
    )

    for match in setattr_pattern.finditer(content):
        class_value = match.group(1)
        for cls in class_value.split():
            cls = cls.strip()
            if cls:
                classes_found.add(cls)

    # Pattern 4: querySelector('.class-name'), querySelectorAll('.class-name')
    # but only extract the class part, not tag selectors
    query_pattern = re.compile(
        r'querySelector(?:All)?\s*\(\s*["\']\.([a-zA-Z_][\w-]*)["\']\s*\)'
    )

    for match in query_pattern.finditer(content):
        classes_found.add(match.group(1))

    # Pattern 5: matches('.class-name'), closest('.class-name')
    matches_pattern = re.compile(
        r'(?:matches|closest)\s*\(\s*["\']\.([a-zA-Z_][\w-]*)["\']\s*\)'
    )

    for match in matches_pattern.finditer(content):
        classes_found.add(match.group(1))

    # Pattern 6: class attributes in HTML strings within JS (template literals, innerHTML, etc.)
    # Matches: class="..." or class='...' inside JS strings
    html_class_pattern = re.compile(
        r'class\s*=\s*["\']([^"\']+)["\']'
    )

    for match in html_class_pattern.finditer(content):
        class_value = match.group(1)
        for cls in class_value.split():
            cls = cls.strip()
            if cls:
                classes_found.add(cls)

    # Pattern 7: String literals containing BEM-style class names (heuristic)
    # Look for common patterns like 'is-open', 'c-component', etc. in any string
    bem_pattern = re.compile(r'["\'`]([a-zA-Z_][\w-]*-[\w-]+)["\'`]')

    for match in bem_pattern.finditer(content):
        potential_class = match.group(1)
        # Check if it looks like a CSS class (BEM-style with prefixes)
        if potential_class.startswith(('is-', 'has-', 'c-', 'l-', 'u-', 'js-')):
            classes_found.add(potential_class)

    return classes_found


def main():
    print(f"{BLUE}{BOLD}--- Linting Dead CSS Classes ---------------------------------------------{RESET}")

    # Collect all CSS files in the theme
    css_files = glob.glob(os.path.join(CSS_DIR, '**/*.css'), recursive=True)

    if not css_files:
        print(f"{YELLOW}⚠️  No CSS files found in {CSS_DIR}{RESET}")
        sys.exit(0)

    # Parse all CSS files to find defined classes
    all_classes = {}  # class_name -> [(filepath, line_num, selector), ...]

    for filepath in css_files:
        file_classes = parse_css_file(filepath)
        for class_name, occurrences in file_classes.items():
            for line_num, selector in occurrences:
                if class_name not in all_classes:
                    all_classes[class_name] = []
                all_classes[class_name].append((filepath, line_num, selector))

    # Collect all class usages from templates and JS
    used_classes_global = set()
    used_classes_in_theme = set()

    # Find template files
    template_files = glob.glob(os.path.join(LAYOUTS_DIR, '**/*.html'), recursive=True)

    # Find JS files
    js_files = glob.glob(os.path.join(JS_DIR, '**/*.js'), recursive=True)

    # Process templates
    for filepath in template_files:
        classes = find_classes_in_template(filepath)
        used_classes_global.update(classes)

        # Check if within theme directory
        if filepath.startswith(THEME_DIR):
            used_classes_in_theme.update(classes)

    # Process JS files
    for filepath in js_files:
        # Skip vendor files
        if 'vendor' in filepath:
            continue
        classes = find_classes_in_js(filepath)
        used_classes_global.update(classes)

        # Check if within theme directory
        if filepath.startswith(THEME_DIR):
            used_classes_in_theme.update(classes)

    # Also check if there are any templates/JS at the root level (demo site)
    root_templates = glob.glob('layouts/**/*.html', recursive=True)
    root_js = glob.glob('assets/**/*.js', recursive=True)

    for filepath in root_templates:
        classes = find_classes_in_template(filepath)
        used_classes_global.update(classes)

    for filepath in root_js:
        classes = find_classes_in_js(filepath)
        used_classes_global.update(classes)

    # Analyze findings
    defined_class_names = set(all_classes.keys())

    # 1. Classes not used anywhere in the repository
    unused_global = defined_class_names - used_classes_global

    # 2. Classes inside themes/proseblock that aren't used within that directory
    # These are classes defined in the theme but potentially only used by the demo site
    # This might indicate component code that should be self-contained
    unused_in_theme = defined_class_names - used_classes_in_theme

    # Filter out classes that ARE used somewhere (just not in theme)
    theme_only_unused = unused_in_theme - unused_global

    # Build output
    issues = []

    # Report globally unused classes
    for class_name in sorted(unused_global):
        occurrences = all_classes[class_name]
        for filepath, line_num, selector in occurrences:
            rel_path = os.path.relpath(filepath)
            issues.append((class_name, rel_path, line_num, selector, 'unused_global'))

    # Report classes not used within theme (but used elsewhere)
    for class_name in sorted(theme_only_unused):
        occurrences = all_classes[class_name]
        for filepath, line_num, selector in occurrences:
            rel_path = os.path.relpath(filepath)
            issues.append((class_name, rel_path, line_num, selector, 'unused_in_theme'))

    if not issues:
        print(f"{GREEN}✅ All {len(defined_class_names)} CSS classes are properly utilized.{RESET}")
        print(f"   (Checked {len(css_files)} CSS files, {len(template_files)} templates, {len(js_files)} JS files)")
        sys.exit(0)

    # Print results
    unused_global_issues = [i for i in issues if i[4] == 'unused_global']
    unused_theme_issues = [i for i in issues if i[4] == 'unused_in_theme']

    if unused_global_issues:
        print(f"\n{YELLOW}⚠️  Globally Unused Classes ({len(unused_global_issues)}):{RESET}")
        print(f"{YELLOW}   These classes are defined in CSS but never referenced in templates or JS.{RESET}\n")

        # Group by class name for cleaner output
        by_class = defaultdict(list)
        for class_name, filepath, line_num, selector, _ in unused_global_issues:
            by_class[class_name].append((filepath, line_num, selector))

        for class_name in sorted(by_class.keys()):
            print(f"   {BOLD}.{class_name}{RESET}")
            for filepath, line_num, selector in by_class[class_name]:
                print(f"     - {filepath}:{line_num} (in `{selector}`)")

    if unused_theme_issues:
        print(f"\n{YELLOW}⚠️  Classes Not Used Within Theme ({len(unused_theme_issues)}):{RESET}")
        print(f"{YELLOW}   These classes are defined in themes/proseblock but only used outside it.{RESET}")
        print(f"{YELLOW}   This may indicate orphaned component code.{RESET}\n")

        by_class = defaultdict(list)
        for class_name, filepath, line_num, selector, _ in unused_theme_issues:
            by_class[class_name].append((filepath, line_num, selector))

        for class_name in sorted(by_class.keys()):
            print(f"   {BOLD}.{class_name}{RESET}")
            for filepath, line_num, selector in by_class[class_name]:
                print(f"     - {filepath}:{line_num} (in `{selector}`)")

    print(f"\n{BLUE}ℹ️  Total: {len(unused_global_issues)} globally unused, {len(unused_theme_issues)} unused in theme.{RESET}")
    print(f"   Checked {len(css_files)} CSS files, {len(template_files)} templates, {len(js_files)} JS files.")

    sys.exit(0)


if __name__ == '__main__':
    main()
