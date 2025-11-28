import ast, os
from pathlib import Path
import operator

print("Current Working Directory:", os.getcwd())
from .arithmetic_test_code import Arithmetic_Visiter, count_arith, COUNTERS


def main():
    # CLI entry point to the project
    # To-do: Implement a helper function (e.g., run_cli_analysis(file_path: str) -> dict) that
    # programmatically performs the same analysis as the CLI. The function should accept a path to a Python file,
    # run the analysis (as done below), and return the results (e.g., a dictionary with the arithmetic operation count).
    # This will allow other modules or potential API endpoints to reuse the analysis logic without invoking the CLI.
    # Could also allow toggle options for different types of analysis
    # Using ast transformation we could allow different languages to be analyzed by converting them to python ast first
    import argparse
    parser = argparse.ArgumentParser(description="Analyze a Python algorithm for arithmetic operations.")
    parser.add_argument("file", help="Path to the Python file to analyze.")
    args = parser.parse_args()

    with open(args.file, "r") as f:
        tree = ast.parse(f.read())

    for child in ast.walk(tree):
        for sub in ast.iter_child_nodes(child):
            sub.parent = child  # Keep track of the parent nodes for use by the methods

    visited_tree = Arithmetic_Visiter().visit(tree)
    ast.fix_missing_locations(visited_tree)

    code = compile(visited_tree, filename="<ast>", mode="exec")

    exec_globals = {
        "COUNTERS": COUNTERS,
        "count_arith": count_arith,
        "operator": operator
    }
    arr = [2, 5, 3, 1, 4]

    exec(code, exec_globals)

    exec_globals["bubble_sort"](arr)

    print("Arithmetic operations counted:", COUNTERS["arithmetic"])


if __name__ == "__main__":
    main()