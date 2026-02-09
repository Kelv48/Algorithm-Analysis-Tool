import pathlib, ast, operator
from random import randint
import pathlib
import joblib

from algorithm_analysis_tool.ast_visitor import (
    ASTVisitor, count_arith, count_assign, count_call,
    count_compare, count_index, count_loop_iteration, not_in
)
root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root/ "src" / "algorithm_analysis_tool" / "algorithms.py"

def run_ast_analysis(func_name, *args, **kwargs):
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

    # Execute original code to define functions
    exec(compile(tree, filename="<ast>", mode="exec"), exec_globals)

    # Instrument the selected function
    visitor = ASTVisitor(counters)
    instrumented_node = visitor.visit(function_map[func_name])
    ast.fix_missing_locations(instrumented_node)
    code_obj = compile(ast.Module(body=[instrumented_node], type_ignores=[]),
                       filename="<ast>", mode="exec")
    exec(code_obj, exec_globals)

    sorting_algos = {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}
    search_algos = {"linear_search", "binary_search"}
    graph_algos = {"dfs", "bfs"}
    activity_algos = {"activity_selection"}

    if func_name in sorting_algos:
        if len(args) != 2:
            raise ValueError(f"{func_name} expects two arguments: max value and array length")
        n_range, arr_length = args
        arr = [randint(1, n_range) for _ in range(arr_length)]
        final_args = [arr]
    
    elif func_name in search_algos:
        if len(args) != 2:
            raise ValueError(f"{func_name} expects two arguments: max value and array length")
        n_range, arr_length = args
        arr = [randint(1, n_range) for _ in range(arr_length)]
        target = randint(1, n_range)
        final_args = [arr, target]

    elif func_name in graph_algos:
        graph = {
            'A': ['B','C'],
            'B': ['D','E'],
            'C': ['F'],
            'D': [],
            'E': ['F'],
            'F': []
        }
        start_node = 'A'
        final_args = [graph, start_node]

    elif func_name in activity_algos:
        if len(args) != 2:
            raise ValueError(f"{func_name} expects two arguments: max value and number of activities")
        n_range, arr_length = args
        activities = [(randint(1, n_range), randint(1, n_range)) for _ in range(arr_length)]
        final_args = [activities]
    else:
        final_args = list(args)

    exec_globals[func_name](*final_args, **kwargs)

    return counters

CACHE_DIR = pathlib.Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

def save_cache(key, data):
    """Save Streamlit results to disk."""
    path = CACHE_DIR / f"{key}.joblib"
    joblib.dump(data, path)

def load_cache(key):
    """Load Streamlit results from disk if they exist."""
    path = CACHE_DIR / f"{key}.joblib"
    if path.exists():
        return joblib.load(path)
    return None

def drop_cache(key):
    """Remove cached data if it exists."""
    path = CACHE_DIR / f"{key}.joblib"
    if path.exists():
        path.unlink()
