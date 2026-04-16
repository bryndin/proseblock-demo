import re
import sys
from pathlib import Path

def preserve_newlines(match):
    """Replaces matched multiline comments with empty lines to keep line numbers perfectly accurate."""
    return '\n' * match.group(0).count('\n')

def test_kwargs_pattern():
    # Resolves to: ../themes/theme-x/layouts
    # Adjust "theme-x" to match your actual theme folder name
    layouts_dir = Path(__file__).parent.parent / "themes" / "theme-x" / "layouts"

    if not layouts_dir.exists():
        print(f"Directory not found: {layouts_dir}")
        sys.exit(1)

    comment_pattern = re.compile(r'{{-?\s*/\*.*?\*/\s*-?}}', re.DOTALL)
    tag_pattern = re.compile(r'{{(.*?)}}', re.DOTALL)
    string_pattern = re.compile(r'(".*?"|\'.*?\'|`.*?`)', re.DOTALL)

    # VIOLATION 1: Direct property extraction from context (e.g., $page := .page)
    # Matches a variable assignment followed directly by a dot and a word
    direct_prop_pattern = re.compile(r'(\$[\w]+)\s*(?::=|=)\s*\.([a-zA-Z_]\w*)')

    # VIOLATION 2: Non-standard generic dictionary names (e.g., $args := .)
    # Matches assignments of the bare dot. If named in the bad_names list, it flags it.
    bad_dict_names = {'args', 'opts', 'options', 'dict', 'params', 'props', 'payload'}
    bad_name_pattern = re.compile(r'\$([a-zA-Z0-9_]+)\s*(?::=|=)\s*\.(?!\w)')

    issues = 0

    for filepath in layouts_dir.rglob('*.html'):
        text = filepath.read_text(encoding='utf-8')
        text = comment_pattern.sub(preserve_newlines, text)

        for match in tag_pattern.finditer(text):
            tag_content = match.group(1).strip('- \t\n\r')
            cleaned = string_pattern.sub('""', tag_content)

            # Check 1: Direct Property Extraction
            for prop_match in direct_prop_pattern.finditer(cleaned):
                var_name, prop_name = prop_match.groups()
                line_num = text[:match.start()].count('\n') + 1

                print(f"❌ {filepath.relative_to(layouts_dir.parent.parent)}:{line_num}")
                print(f"   Violation: Direct property extraction '{prop_match.group(0).strip()}'.")
                print(f"   Refactor to: '$kwargs := .' followed by '{var_name} := $kwargs.{prop_name}'")
                issues += 1

            # Check 2: Bad Dictionary Variables
            for name_match in bad_name_pattern.finditer(cleaned):
                var_name = name_match.group(1)
                if var_name.lower() in bad_dict_names:
                    line_num = text[:match.start()].count('\n') + 1

                    print(f"❌ {filepath.relative_to(layouts_dir.parent.parent)}:{line_num}")
                    print(f"   Violation: Non-standard dict context name '${var_name} := .'")
                    print(f"   Refactor to: '$kwargs := .' when receiving a dictionary of arguments.")
                    issues += 1

    if issues == 0:
        print("✅ All clear! No $kwargs pattern violations found.")
        sys.exit(0)
    else:
        print(f"\n🚨 Linting failed: Found {issues} violation(s) of the $kwargs pattern.")
        sys.exit(1)

if __name__ == "__main__":
    test_kwargs_pattern()