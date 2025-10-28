#!/usr/bin/env python3
"""
Validate query patterns by manually checking the tree structure
"""
import tree_sitter_yaml as tsyaml
from tree_sitter import Language, Parser

# Load YAML language
YAML_LANGUAGE = Language(tsyaml.language())
parser = Parser(YAML_LANGUAGE)

def check_pattern1(comment_node, debug=False):
    """
    Pattern 1: (comment) . (block_mapping_pair value: (block_node (block_scalar)))
    Check if comment is followed by block_mapping_pair
    """
    parent = comment_node.parent
    if debug:
        print(f"    DEBUG P1: parent type = {parent.type if parent else 'None'}")

    if not parent:
        return None

    try:
        siblings = parent.children
        comment_idx = siblings.index(comment_node)
        if debug:
            print(f"    DEBUG P1: comment index = {comment_idx}/{len(siblings)-1}")

        # Check next sibling
        if comment_idx + 1 < len(siblings):
            next_sib = siblings[comment_idx + 1]
            if debug:
                print(f"    DEBUG P1: next sibling = {next_sib.type} at line {next_sib.start_point[0]}")

            if next_sib.type == 'block_mapping_pair':
                if debug:
                    print(f"    DEBUG P1: next sibling IS block_mapping_pair")
                # Find value node
                for child in next_sib.children:
                    if debug:
                        print(f"    DEBUG P1: block_mapping_pair child = {child.type}")
                    if child.type == 'block_node':
                        for subchild in child.children:
                            if debug:
                                print(f"    DEBUG P1: block_node child = {subchild.type}")
                            if subchild.type == 'block_scalar':
                                return subchild
        else:
            if debug:
                print(f"    DEBUG P1: no next sibling (last in parent)")
    except Exception as e:
        if debug:
            print(f"    DEBUG P1: exception = {e}")

    return None

def check_pattern2(comment_node, debug=False):
    """
    Pattern 2: (block_mapping_pair (comment) (block_node (block_mapping (block_mapping_pair ...))))
    Check if comment is child of block_mapping_pair with nested structure
    """
    parent = comment_node.parent
    if debug:
        print(f"    DEBUG P2: parent type = {parent.type if parent else 'None'}")

    if not parent or parent.type != 'block_mapping_pair':
        return None

    try:
        # Find block_node sibling (doesn't need to be immediate)
        for child in parent.children:
            if child.type == 'block_node':
                if debug:
                    print(f"    DEBUG P2: found block_node")
                # Check for block_mapping inside
                for node in child.children:
                    if node.type == 'block_mapping':
                        if debug:
                            print(f"    DEBUG P2: found block_mapping inside block_node")
                        # Find block_mapping_pair with block_scalar
                        for pair in node.children:
                            if pair.type == 'block_mapping_pair':
                                # Look for value: block_node > block_scalar
                                for pair_child in pair.children:
                                    if pair_child.type == 'block_node':
                                        for scalar_node in pair_child.children:
                                            if scalar_node.type == 'block_scalar':
                                                if debug:
                                                    print(f"    DEBUG P2: found block_scalar at line {scalar_node.start_point[0]}")
                                                return scalar_node
    except Exception as e:
        if debug:
            print(f"    DEBUG P2: exception = {e}")
            import traceback
            traceback.print_exc()

    return None

def find_all_nodes(node, node_type, results=None):
    """Recursively find all nodes of a given type"""
    if results is None:
        results = []

    if node.type == node_type:
        results.append(node)

    for child in node.children:
        find_all_nodes(child, node_type, results)

    return results

def analyze_yaml_file(filepath):
    """Analyze which patterns match"""
    with open(filepath, 'rb') as f:
        source_code = f.read()

    source_lines = source_code.decode('utf-8').split('\n')

    tree = parser.parse(source_code)
    root = tree.root_node

    print(f"\n{'='*60}")
    print(f"Validating: {filepath}")
    print(f"{'='*60}\n")

    # Find all comments
    comments = find_all_nodes(root, 'comment')

    # Filter to only "# sql" comments
    sql_comments = []
    for comment in comments:
        text = comment.text.decode('utf-8').lower()
        if '# sql' in text:
            sql_comments.append(comment)

    print(f"Found {len(sql_comments)} '# sql' comments\n")

    pattern1_matches = []
    pattern2_matches = []

    for i, comment in enumerate(sql_comments, 1):
        line = comment.start_point[0]
        text = comment.text.decode('utf-8')

        print(f"Comment #{i} at line {line}: {text}")

        # Test pattern 1
        match1 = check_pattern1(comment, debug=True)
        if match1:
            print(f"  ✓ PATTERN 1 matches (block_scalar at line {match1.start_point[0]})")
            pattern1_matches.append((comment, match1))
        else:
            print(f"  ✗ Pattern 1 no match")

        # Test pattern 2
        match2 = check_pattern2(comment, debug=True)
        if match2:
            print(f"  ✓ PATTERN 2 matches (block_scalar at line {match2.start_point[0]})")
            pattern2_matches.append((comment, match2))
        else:
            print(f"  ✗ Pattern 2 no match")

        print()

    # Summary
    total_matches = len(set([m[1] for m in pattern1_matches + pattern2_matches]))

    print(f"{'='*60}")
    print(f"SUMMARY:")
    print(f"{'='*60}")
    print(f"Pattern 1 matches: {len(pattern1_matches)}")
    print(f"Pattern 2 matches: {len(pattern2_matches)}")
    print(f"Total unique injection sites: {total_matches}")
    print(f"Expected (# sql comments): {len(sql_comments)}")

    if total_matches == len(sql_comments):
        print(f"\n✓ SUCCESS: All {len(sql_comments)} comments covered by patterns!")
        return True
    else:
        print(f"\n✗ INCOMPLETE: Only {total_matches}/{len(sql_comments)} comments covered")
        return False

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
            import traceback
            traceback.print_exc()
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("✓ ALL VALIDATION PASSED")
    else:
        print("✗ VALIDATION FAILED")
    print(f"{'='*60}\n")

    sys.exit(0 if all_passed else 1)
