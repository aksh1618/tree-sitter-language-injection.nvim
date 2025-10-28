#!/usr/bin/env python3
"""
Test tree-sitter queries against YAML files
"""
import tree_sitter_yaml as tsyaml
from tree_sitter import Language, Parser, Query

# Load YAML language
YAML_LANGUAGE = Language(tsyaml.language())
parser = Parser(YAML_LANGUAGE)

# Our queries (simplified for testing - using 'sql' as example)
QUERY_PATTERN_1 = """
;; comment injection - pattern 1: comment sibling of block_mapping_pair
(
 (comment) @_comment
 .
 (block_mapping_pair
   value: (block_node
            (block_scalar) @injection.content))
 (#match? @_comment "^#+( )*(sql|SQL)( )*"))
"""

QUERY_PATTERN_2 = """
;; comment injection - pattern 2: comment child of block_mapping_pair
(block_mapping_pair
 (comment) @_comment
 .
 (block_node
   (block_scalar) @injection.content)
 (#match? @_comment "^#+( )*(sql|SQL)( )*"))
"""

def test_query(query_string, source_code, query_name):
    """Test a query against source code"""
    try:
        query = Query(YAML_LANGUAGE, query_string)
        tree = parser.parse(source_code)

        # Use matches() method which returns list of (pattern_index, captures_dict)
        query_matches = query.matches(tree.root_node)

        print(f"\n{query_name}:")
        print("-" * 60)

        if not query_matches:
            print("  No matches found")
            return []

        matches = []
        for pattern_idx, captures_dict in query_matches:
            for capture_name, nodes in captures_dict.items():
                for node in nodes:
                    line = node.start_point[0]
                    text = node.text.decode('utf-8')
                    # Truncate and escape text for display
                    text = text.replace('\n', '\\n').replace('\r', '\\r')
                    if len(text) > 50:
                        text = text[:50] + "..."

                    print(f"  [{capture_name}] Line {line}: {text}")
                    matches.append((capture_name, line, node))

        return matches
    except Exception as e:
        print(f"\n{query_name}: ERROR - {e}")
        import traceback
        traceback.print_exc()
        return []

def analyze_yaml_file(filepath):
    """Test queries against a YAML file"""
    with open(filepath, 'rb') as f:
        source_code = f.read()

    source_lines = source_code.decode('utf-8').split('\n')

    print(f"\n{'='*60}")
    print(f"Testing: {filepath}")
    print(f"{'='*60}")

    # Show the source with line numbers
    print("\nSOURCE CODE:")
    print("-" * 60)
    for i, line in enumerate(source_lines[:20], 1):  # Show first 20 lines
        print(f"{i:3}: {line}")

    # Test both query patterns
    matches1 = test_query(QUERY_PATTERN_1, source_code, "PATTERN 1 (sibling of block_mapping_pair)")
    matches2 = test_query(QUERY_PATTERN_2, source_code, "PATTERN 2 (child of block_mapping_pair)")

    # Combine and summarize
    all_injection_matches = [m for m in matches1 + matches2 if m[0] == 'injection.content']

    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"{'='*60}")
    print(f"Total injection sites found: {len(all_injection_matches)}")
    for _, line, _ in all_injection_matches:
        print(f"  - Line {line}")

    # Count expected injections (lines with "# sql")
    expected_lines = [i for i, line in enumerate(source_lines) if '# sql' in line.lower()]
    print(f"\nExpected injection comments (# sql): {len(expected_lines)}")
    for line_num in expected_lines:
        print(f"  - Line {line_num}")

    if len(all_injection_matches) == len(expected_lines):
        print(f"\n✓ SUCCESS: All {len(expected_lines)} expected injections matched!")
    else:
        print(f"\n✗ MISMATCH: Found {len(all_injection_matches)} injections, expected {len(expected_lines)}")

    return len(all_injection_matches) == len(expected_lines)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = ["test_user_example.yaml"]

    all_passed = True
    for filepath in files:
        try:
            passed = analyze_yaml_file(filepath)
            all_passed = all_passed and passed
        except Exception as e:
            print(f"\nERROR processing {filepath}: {e}")
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print(f"{'='*60}\n")

    sys.exit(0 if all_passed else 1)
