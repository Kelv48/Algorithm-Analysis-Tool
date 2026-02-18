import pathlib, ast, operator
from random import randint
import pathlib
import joblib
import time
import json

from algorithm_analysis_tool.ast_helpers import resolve_helpers
from algorithm_analysis_tool.ast_visitor import (
    ASTVisitor, count_arith, count_assign, count_call,
    count_compare, count_index, count_loop_iteration, not_in
)
root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root/ "src" / "algorithm_analysis_tool" / "algorithms.py"

# This may need to be modified to accept a broader range of inputs for different algo types
# Also may need to also return the history of the counters at each step for visualization purposes, not just the final counters
# And the order in which lines were executed
def run_ast_analysis(func_name, *args, input_arr=None, input_generated=False, **kwargs):
    
    sorting_algos = {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}
    search_algos = {"linear_search", "binary_search"}
    graph_algos = {"dfs", "bfs"}
    activity_algos = {"activity_selection"}

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

    # Parse the algorithm file
    with open(algo_path, "r") as f:
        tree = ast.parse(f.read())

    function_map = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if func_name not in function_map:
        raise ValueError(f"Function {func_name} not found in algorithms.py")

    # Prepare globals with counters and instrumentation
    exec_globals = {
        "COUNTERS": counters,
        "count_arith": count_arith,
        "count_assign": count_assign,
        "count_call": count_call,
        "count_compare": count_compare,
        "count_index": count_index,
        "count_loop_iteration": count_loop_iteration,
        "operator": operator,
        "not_in": not_in
    }

    needed_functions = resolve_helpers(func_name, function_map)
    
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

    if input_generated:
        final_args = input_arr
    else:
        match func_name:
            case name if name in sorting_algos:
                final_args = sorting_generation(func_name, *args)
            case name if name in search_algos:
                final_args = search_generation(func_name, *args)
            case name if name in graph_algos:
                final_args = graph_generation(func_name, *args)
            case name if name in activity_algos:
                final_args = activity_generation(func_name, *args)
            case _:
                raise ValueError(f"Unknown function {func_name} for input generation")

    exec_globals[func_name](*final_args, **kwargs)

    return {
        "counters": counters,
        "input": final_args,
        "meta": {
            "length": extract_input_length(final_args),
            "algorithm": func_name,
        }
    }




def extract_input_length(input_args):
    """
    Extract meaningful input size from generated argument list.
    """

    if not input_args:
        return None

    primary = input_args[0]

    # Array-based algorithms
    if isinstance(primary, (list, tuple)):
        return len(primary)

    # Graph algorithms (dict adjacency list)
    if isinstance(primary, dict):
        return len(primary.keys())

    return None

# Note
# Joblib maintains quick cache for per algo cache
# Json maintains detailed cache for resent history

# Cache Configs 

CACHE_DIR = pathlib.Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

ALGO_DIR = CACHE_DIR / "algorithms"
ALGO_DIR.mkdir(exist_ok=True)

RECENT_RUNS_FILE = CACHE_DIR / "recent_runs.json"
MAX_RECENT_RUNS = 10

# Per Algo Cache

def save_cache(algo_key, data):
    path = ALGO_DIR / f"{algo_key}.joblib"
    joblib.dump(data, path)

def load_cache(algo_key):
    path = ALGO_DIR / f"{algo_key}.joblib"
    if path.exists():
        return joblib.load(path)
    return None

def drop_cache(algo_key):
    path = ALGO_DIR / f"{algo_key}.joblib"
    if path.exists():
        path.unlink()

# Recent Run History

def _read_recent_runs():
    if RECENT_RUNS_FILE.exists():
        with open(RECENT_RUNS_FILE, "r") as f:
            return json.load(f)
    return []

def _write_recent_runs(runs):
    with open(RECENT_RUNS_FILE, "w") as f:
        json.dump(runs, f, indent=2)

def save_recent_run(algorithm, n, arr, input_array, result):
    runs = _read_recent_runs()

    run_record = {
        "algorithm": algorithm,
        "timestamp": int(time.time() * 1000),
        "params": {
            "n": n,
            "arr": arr,
        },
        "input_meta": {
            "length": extract_input_length(input_array),
            "range_max": n,
        },
        "results": result,
    }

    # Insert newest run first
    runs.insert(0, run_record)

    # Keep only last N runs overall
    runs = runs[:MAX_RECENT_RUNS]

    _write_recent_runs(runs)


def load_recent_runs():
    return _read_recent_runs()


def sorting_generation(func_name, *args):
    if len(args) != 2:
        raise ValueError(f"{func_name} expects two arguments: max value and array length")
    n_range, arr_length = args
    arr = [randint(1, n_range) for _ in range(arr_length)]
    return [arr]

def search_generation(func_name, *args):
    if len(args) != 2:
        raise ValueError(f"{func_name} expects two arguments: max value and array length")
    n_range, arr_length = args
    arr = [randint(1, n_range) for _ in range(arr_length)]
    target = randint(1, n_range)
    return [arr, target]

# Expand the graph generation to support different types of graph inputs for different graph algorithms, currently just returns the same graph for testing purposes
def graph_generation(func_name, *args):
    graph = {
        'A': ['B','C'],
        'B': ['D','E'],
        'C': ['F'],
        'D': [],
        'E': ['F'],
        'F': []
        }
    start_node = 'A'
    return [graph, start_node]

def activity_generation(func_name, *args):
    if len(args) != 2:
        raise ValueError(f"{func_name} expects two arguments: max value and number of activities")
    n_range, arr_length = args
    activities = [(randint(1, n_range), randint(1, n_range)) for _ in range(arr_length)]
    return [activities]

# Allow input generation for matrix-based algorithms like Floyd-Warshall, Prim's, Kruskal's, etc. to be generated here as well