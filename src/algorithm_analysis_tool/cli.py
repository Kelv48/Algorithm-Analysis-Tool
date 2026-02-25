import ast, sys, argparse
import operator

from .ast_helpers import resolve_helpers
from .ast_visitor import (
    ASTVisitor, count_arith, count_assign, count_call,
    count_compare, count_index, count_loop_iteration
)

def main():
    counters = {
    "assignments": 0,
    "indexing": 0,
    "function_calls": 0,
    "returns": 0,
    "comparisons": 0,
    "arithmetic": 0,
    "loop_nodes": 0,
    "loop_iterations": 0
    }
    parser = argparse.ArgumentParser(description="Analyze a Python algorithm for arithmetic operations.")
    parser.add_argument("file", help="Path to the Python file to analyze.")
    args = parser.parse_args()
    
    # Read the file
    with open(args.file, "r") as f:
        source = f.read()

    tree = ast.parse(source)

    # Map function names -> AST nodes
    function_map = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}

    if not function_map:
        print("No functions found in the file.")
        sys.exit(1)

    # List functions with numbers
    print("Available functions:")
    for i, name in enumerate(function_map, 1):
        print(f"{i}. {name}")

    # User picks a number
    choice_index = input("Select a function by number: ")
    try:
        choice_index = int(choice_index)
        if not 1 <= choice_index <= len(function_map):
            raise ValueError
    except ValueError:
        print("Invalid selection")
        sys.exit(1)

    # Map number → function name
    function_names = list(function_map.keys())
    choice = function_names[choice_index - 1]

    # Resolve helpers
    needed_functions = resolve_helpers(choice, function_map)

    if choice not in function_map:
        print("Invalid choice")
        sys.exit(1)

    exec_globals = {
        "COUNTERS": counters,
        "count_arith": count_arith,
        "count_assign": count_assign,
        "count_call": count_call,
        "count_compare": count_compare,
        "count_index": count_index,
        "count_loop_iteration": count_loop_iteration,
        "operator": operator
    }

    selected_nodes = [
        function_map[name]
        for name in function_map
        if name in needed_functions
    ]

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])

    visitor = ASTVisitor(counters)
    module_ast = visitor.visit(module_ast)
    ast.fix_missing_locations(module_ast)

    code_obj = compile(module_ast, filename="<ast>", mode="exec")
    exec(code_obj, exec_globals)

    if choice in {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}:
        arr = [2, 5, 3, 1, 4]
        result = exec_globals[choice](arr)

    elif choice in {"linear_search", "binary_search"}:
        arr = [1, 3, 5, 7, 9, 11, 13]
        target = 7
        result = exec_globals[choice](arr, target)

    elif choice in {"dfs", "bfs"}:
        graph = {
            'A': ['B', 'C'],
            'B': ['D', 'E'],
            'C': ['F'],
            'D': [],
            'E': ['F'],
            'F': []
        }
        start = 'A'
        result = exec_globals[choice](graph, start)

    elif choice in {"fib", "fib_dp"}:
        n = 10
        result = exec_globals[choice](n)

    elif choice == "activity_selection":
        activities = [
            (1, 4),
            (3, 5),
            (0, 6),
            (5, 7),
            (8, 9),
            (5, 9),
        ]
        result = exec_globals[choice](activities)

    elif choice == "greatest_common_divisor":
        result = exec_globals[choice](48, 18)

    else:
        raise ValueError(f"No test input defined for {choice}")

    print("Result:", result)


    # Print analysis counters
    print("\nAnalysis Results:")
    for key, value in counters.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()