import ast
import sys
import copy
import time
import json
from pathlib import Path
from random import randint, choice, sample
import string
from .execution_session import ExecutionSession

DEFAULT_FILE_PATH = "src/algorithm_analysis_tool/algorithms.py"

# ------------------ INPUT GENERATORS ------------------
def generate_sorting(func_name, size):
    return [randint(0, size*10) for _ in range(size)]

def generate_search(func_name, size):
    arr = sorted([randint(0, size*10) for _ in range(size)])
    target = choice(arr)
    return [arr, target]

def generate_graph(func_name, num_nodes=6, num_edges=8, directed=True):
    labels = list(string.ascii_uppercase[:num_nodes])
    graph = {node: [] for node in labels}
    # Tree-like connected graph
    for i in range(1, num_nodes):
        parent = choice(labels[:i])
        graph[parent].append(labels[i])
        if not directed:
            graph[labels[i]].append(parent)
    # Extra edges
    existing_edges = {(parent, child) for parent, children in graph.items() for child in children}
    while len(existing_edges) < num_edges:
        a, b = sample(labels, 2)
        if (a, b) in existing_edges or (not directed and (b, a) in existing_edges):
            continue
        graph[a].append(b)
        if not directed:
            graph[b].append(a)
        existing_edges.add((a,b))
    start = choice(labels)
    return [graph, start]

def generate_activity(func_name, n_range=10, arr_length=5):
    activities = [(randint(1, n_range), randint(1, n_range)) for _ in range(arr_length)]
    return [activities]

def generate_matrix(func_name, n_range=10, rows_A=2, cols_A=2, cols_B=2):
    A = [[randint(1, n_range) for _ in range(cols_A)] for _ in range(rows_A)]
    B = [[randint(1, n_range) for _ in range(cols_B)] for _ in range(cols_A)]
    return [A, B]

def prepare_input(func_name, user_input=None, random_flag=False, size=10):
    # Custom JSON input
    if user_input:
        try:
            parsed = json.loads(user_input)
            return list(parsed) if isinstance(parsed, (list, tuple)) else [parsed]
        except json.JSONDecodeError:
            print("Invalid JSON input, using default/random input instead.")

    # Random input
    if random_flag:
        if "sort" in func_name.lower():
            return [generate_sorting(func_name, size)]
        elif "search" in func_name.lower():
            return generate_search(func_name, size)
        elif func_name in {"dfs", "bfs"}:
            return generate_graph(func_name)
        elif func_name == "activity_selection":
            return generate_activity(func_name)
        elif func_name in {"matrix_multiply", "matrix_add"}:
            return generate_matrix(func_name)
    
    # Fallback: return empty list
    return []

# ------------------ CLI ------------------
def main():
    file_path = DEFAULT_FILE_PATH
    if not Path(file_path).is_file():
        print(f"Default algorithms file '{DEFAULT_FILE_PATH}' not found.")
        file_path = input("Enter path to Python file containing algorithms: ").strip()
        if not Path(file_path).is_file():
            print("Invalid path. Exiting.")
            sys.exit(1)

    with open(file_path, "r") as f:
        source = f.read()

    tree = ast.parse(source)
    function_map = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not function_map:
        print("No functions found. Exiting.")
        sys.exit(1)

    print("\nAvailable functions:")
    for i, name in enumerate(function_map.keys(), 1):
        print(f"{i}. {name}")

    selected = input("\nEnter function numbers (comma-separated) or leave blank for all: ").strip()
    if selected:
        indices = [int(x.strip())-1 for x in selected.split(",")]
        func_names = [list(function_map.keys())[i] for i in indices if 0 <= i < len(function_map)]
    else:
        func_names = list(function_map.keys())

    user_input = input("Custom JSON input (leave blank for default/random): ").strip() or None
    use_random = input("Use random input? (y/N): ").strip().lower() == "y"
    size = input("Random input size (default 10): ").strip()
    size = int(size) if size.isdigit() else 10
    measure_time = input("Measure time? (y/N): ").strip().lower() == "y"
    verbose = input("Show step history? (y/N): ").strip().lower() == "y"
    compare = input("Compare multiple functions? (y/N): ").strip().lower() == "y"

    results = []

    for func_name in func_names:
        print(f"\n=== Running {func_name} ===")
        func_args = prepare_input(func_name, user_input, use_random, size)
        session = ExecutionSession()
        start_time = time.time()
        try:
            result, counters, history = session.run_function(func_name, args=func_args, src=source)
        except TypeError as e:
            print(f"Error running {func_name}: {e}")
            continue
        elapsed_time = time.time() - start_time if measure_time else None

        print("Result:", result)
        if measure_time:
            print(f"Time elapsed: {elapsed_time:.6f}s")
        print("Counters:", counters)
        if verbose:
            print("\nStep history:")
            for step in history:
                print(step)

        results.append({
            "function": func_name,
            "result": result,
            "counters": counters,
            "time": elapsed_time
        })

    if compare and len(results) > 1:
        print("\n=== Comparison Summary ===")
        for r in results:
            time_str = f"{r['time']:.6f}s" if r['time'] is not None else "N/A"
            print(f"{r['function']}: comparisons={r['counters'].get('comparisons',0)}, "
                  f"assignments={r['counters'].get('assignments',0)}, "
                  f"time={time_str}")

if __name__ == "__main__":
    main()