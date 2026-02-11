#!/usr/bin/env python3
"""
Inspect YAML parse tree to understand structure for injection queries
"""
import tree_sitter_yaml as tsyaml
from tree_sitter import Language, Parser, Query

# Load YAML language
YAML_LANGUAGE = Language(tsyaml.language())
parser = Parser(YAML_LANGUAGE)

def print_tree(node, indent=0, max_depth=10):
    """Recursively print the parse tree"""
    if indent > max_depth:
        return

    # Print current node
    print("  " * indent + f"{node.type}", end="")
    if node.is_named:
        # For leaf nodes, show the text content (truncated)
        if node.child_count == 0:
            text = node.text.decode('utf-8')
            if len(text) > 40:
                text = text[:40] + "..."
            # Escape newlines for display
            text = text.replace('\n', '\\n').replace('\r', '\\r')
            print(f' "{text}"', end="")
    print(f" [{node.start_point[0]}:{node.start_point[1]}-{node.end_point[0]}:{node.end_point[1]}]")

    # Print children
    for child in node.children:
        print_tree(child, indent + 1, max_depth)

def find_comments_and_pairs(node, results=None):
    """Find all comment and block_mapping_pair nodes"""
    if results is None:
        results = {'comments': [], 'pairs': [], 'block_scalars': []}

    if node.type == 'comment':
        results['comments'].append(node)
    elif node.type == 'block_mapping_pair':
        results['pairs'].append(node)
    elif node.type == 'block_scalar':
        results['block_scalars'].append(node)

    for child in node.children:
        find_comments_and_pairs(child, results)

    return results

def analyze_yaml_file(filepath):
    """Analyze a YAML file and print relevant structure"""
    with open(filepath, 'rb') as f:
        source_code = f.read()

    tree = parser.parse(source_code)
    root = tree.root_node

    print(f"\n{'='*60}")
    print(f"Analyzing: {filepath}")
    print(f"{'='*60}\n")

    # Print full tree
    print("FULL PARSE TREE:")
    print("-" * 60)
    print_tree(root, max_depth=15)

    # Find and analyze comments and pairs
    print(f"\n{'='*60}")
    print("ANALYSIS OF COMMENTS AND MAPPING PAIRS:")
    print(f"{'='*60}\n")

    results = find_comments_and_pairs(root)

    print(f"Found {len(results['comments'])} comments")
    print(f"Found {len(results['pairs'])} block_mapping_pairs")
    print(f"Found {len(results['block_scalars'])} block_scalars")

    # Analyze each comment and its following sibling
    print("\n" + "-" * 60)
    print("COMMENT -> PAIR RELATIONSHIPS:")
    print("-" * 60)

    source_lines = source_code.decode('utf-8').split('\n')

    for i, comment in enumerate(results['comments']):
        comment_text = comment.text.decode('utf-8')
        line_num = comment.start_point[0]

        print(f"\nComment #{i+1} at line {line_num}: {comment_text}")

        # Get parent
        parent = comment.parent
        if parent:
            print(f"  Parent: {parent.type}")

            # Find this comment's index among siblings
            siblings = parent.children
            try:
                comment_idx = siblings.index(comment)
                print(f"  Comment index in parent: {comment_idx}/{len(siblings)-1}")

                # Check next sibling
                if comment_idx + 1 < len(siblings):
                    next_sibling = siblings[comment_idx + 1]
                    print(f"  Next sibling: {next_sibling.type} at line {next_sibling.start_point[0]}")

                    if next_sibling.type == 'block_mapping_pair':
                        # Analyze the block_mapping_pair structure
                        print(f"    ✓ Next sibling IS a block_mapping_pair!")
                        for child in next_sibling.children:
                            print(f"      - {child.type}", end="")
                            if child.type in ['block_node', 'block_scalar']:
                                for subchild in child.children:
                                    print(f" > {subchild.type}", end="")
                            print()
                else:
                    print(f"  ✗ No next sibling (comment is last in parent)")
            except ValueError:
                print(f"  ✗ Could not find comment in parent's children")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        for filepath in sys.argv[1:]:
            analyze_yaml_file(filepath)
    else:
        # Default test files
        analyze_yaml_file("test_user_example.yaml")
        analyze_yaml_file("test_yaml.yaml")
