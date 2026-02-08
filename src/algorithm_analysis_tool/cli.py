import ast, sys, argparse
import operator

from .ast_visitor import (
    ASTVisitor, count_arith, count_assign, count_call,
    count_compare, count_index, count_loop_iteration, reset_counters
)

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


def main():
    counters = reset_counters(counters)
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

    exec(compile(tree, filename="<ast>", mode="exec"), exec_globals)

    visitor = ASTVisitor(counters)
    instrumented_node = visitor.visit(function_map[choice])
    ast.fix_missing_locations(instrumented_node)

    module_ast = ast.Module(body=[instrumented_node], type_ignores=[])
    code_obj = compile(module_ast, filename="<ast>", mode="exec")

    # Prepare globals for execution

    # Execute function definition
    exec(code_obj, exec_globals)

    # Example input array for algorithms that need it
    from random import randint
    arr = []

    for i in range(10000):
        i = randint(1, 500)
        arr.append(i)
    # arr = [2, 5, 3, 1, 4]

    # Call the selected function dynamically
    exec_globals[choice](arr)
    # print("Result:", result)

    # Print analysis counters
    print("\nAnalysis Results:")
    for key, value in counters.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()