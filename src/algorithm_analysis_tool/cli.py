import ast, os, sys, argparse
import operator

from .ast_visitor import AST_Visitor, count_arith, count_assign, count_call, count_compare, count_index, COUNTERS

def main():
    # CLI entry point to the project
    # To-do: Implement a helper function (e.g., run_cli_analysis(file_path: str) -> dict) that
    # programmatically performs the same analysis as the CLI. The function should accept a path to a Python file,
    # run the analysis (as done below), and return the results (e.g., a dictionary with the arithmetic operation count).
    # This will allow other modules or potential API endpoints to reuse the analysis logic without invoking the CLI.
    # Could also allow toggle options for different types of analysis
    # Using ast transformation we could allow different languages to be analyzed by converting them to python ast first
    parser = argparse.ArgumentParser(description="Analyze a Python algorithm for arithmetic operations.")
    parser.add_argument("file", help="Path to the Python file to analyze.")
    args = parser.parse_args()
    
    filename = sys.argv[1]
    name = os.path.basename(filename)

    with open(args.file, "r") as f:
        tree = ast.parse(f.read())

    for child in ast.walk(tree):
        for sub in ast.iter_child_nodes(child):
            sub.parent = child  # Keep track of the parent nodes for use by the methods

    visited_tree = AST_Visitor().visit(tree)
    ast.fix_missing_locations(visited_tree)

    code = compile(visited_tree, filename="<ast>", mode="exec")

    exec_globals = {
        "COUNTERS": COUNTERS,
        "count_arith": count_arith,
        "count_assign": count_assign,
        "count_call": count_call,
        "count_compare": count_compare,
        "count_index": count_index,
        "operator": operator
    }
    arr = [2, 5, 3, 1, 4]

    exec(code, exec_globals)
    function_name = f"{name}"
    function_name = function_name.split(".")[0]
    exec_globals[function_name](arr)

    print("Analysis Results:")
    for key, value in COUNTERS.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()