import ast, sys, argparse
import operator

from .helpers import resolve_helpers
from .function_visitor import FunctionDependencyVisitor
from .ast_visitor import (
    ASTVisitor, count_arith, count_assign, count_call,
    count_compare, count_index, count_loop_iteration, reset_counters
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

    print("Available functions:")
    for name in function_map:
        print("-", name)

    choice = input("Which function do you want to run? ")
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

    # Prepare globals for execution
    arr = [2, 5, 3, 1, 4]

    result = exec_globals[choice](arr)
    print("Result:", result)


    # Print analysis counters
    print("\nAnalysis Results:")
    for key, value in counters.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()