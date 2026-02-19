import ast, operator
from random import randint, choice
import pathlib, joblib, json, time, copy
import streamlit as st

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
def run_ast_analysis(func_name, *args, input_arr=None, input_generated=False, input_mode=None, **kwargs):
    """
    Execute an algorithm with AST instrumentation, recording operation counts
    and maintaining a local history of operations for visualization/animation.

    Parameters:
        func_name (str): Name of the algorithm function in algorithms.py
        *args: Positional arguments for the algorithm
        input_arr (list, optional): Pre-generated input array
        input_generated (bool): Whether input_arr is provided
        input_mode (str, optional): The input generation mode for caching
        **kwargs: Other keyword arguments for the algorithm function

    Returns:
        dict: {
            "counters": final counters,
            "input": input array(s),
            "history": list of snapshots of operations,
            "meta": {
                "length": input length,
                "algorithm": func_name,
                "input_mode": input_mode
            }
        }
    """
    # Local counters and history
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
    history = []

    sorting_algos = {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}
    search_algos = {"linear_search", "binary_search"}
    graph_algos = {"dfs", "bfs"}
    activity_algos = {"activity_selection"}

    # Load and parse source code
    with open(algo_path, "r") as f:
        tree = ast.parse(f.read())

    # Map function names to AST nodes
    function_map = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if func_name not in function_map:
        raise ValueError(f"Function {func_name} not found in algorithms.py")

    # Include helper functions if needed
    needed_functions = resolve_helpers(func_name, function_map)
    selected_nodes = [function_map[name] for name in function_map if name in needed_functions]

    # Build module with only required functions
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    visitor = ASTVisitor(counters)
    module_ast = visitor.visit(module_ast)
    ast.fix_missing_locations(module_ast)

    # Prepare execution environment with local history
    exec_globals = {
        "COUNTERS": counters,
        "HISTORY": history,
        "count_arith": count_arith,
        "count_assign": count_assign,
        "count_call": count_call,
        "count_compare": count_compare,
        "count_index": count_index,
        "count_loop_iteration": count_loop_iteration,
        "operator": operator,
        "not_in": not_in,
        "arrays": [],
    }

    # Compile and execute AST
    code_obj = compile(module_ast, filename="<ast>", mode="exec")
    exec(code_obj, exec_globals)

    # Prepare input for the function
    if input_generated:
        final_args = [copy.deepcopy(a) for a in input_arr] if isinstance(input_arr, list) else copy.deepcopy(input_arr)
    else:
        match func_name:
            case name if name in sorting_algos:
                final_args = sorting_generation(func_name, *args, mode=input_mode)
            case name if name in search_algos:
                final_args = search_generation(func_name, *args, mode=input_mode)
            case name if name in graph_algos:
                final_args = graph_generation(func_name, *args)
            case name if name in activity_algos:
                final_args = activity_generation(func_name, *args, mode=input_mode)
            case _:
                raise ValueError(f"Unknown function {func_name} for input generation")
        final_args = [copy.deepcopy(arg) for arg in final_args]

    # Assign arrays for instrumentation and run
    exec_globals["arrays"] = [final_args[0]] if isinstance(final_args, list) else []
    exec_globals[func_name](*final_args, **kwargs)

    return {
        "counters": counters,
        "input": final_args,
        "history": history,
        "meta": {
            "length": extract_input_length(final_args),
            "algorithm": func_name,
            "input_mode": input_mode
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


def visualize_algorithm(history, source_code, array_name="arrays", delay=1, max_animation_length=5):
    """
    Visualize an algorithm step-by-step using the recorded AST history.
    Only allows animation if the array is small enough.
    """
    st.subheader("Algorithm Step-through Visualization")

    if not history:
        st.info("No history to visualize.")
        return

    # Determine number of arrays safely
    first_arrays = history[0].get(array_name) or []
    if first_arrays and len(first_arrays[0]) > max_animation_length:
        st.warning(
            f"Array length is {len(first_arrays[0])}. "
            f"Animations are disabled for arrays larger than {max_animation_length} to prevent memory issues."
        )
        return

    code_lines = source_code.splitlines()
    array_count = len(first_arrays)

    # Persistent placeholders
    code_placeholder = st.empty()
    array_placeholders = [st.empty() for _ in range(array_count)]
    counter_placeholder = st.empty()

    # Slider
    step_slider = st.slider("Step", 0, len(history) - 1, 0, key="step_slider", format="%d")
    prev_step = history[step_slider - 1] if step_slider > 0 else None
    current_step = history[step_slider]

    display_step(current_step, code_lines, code_placeholder, array_placeholders, counter_placeholder, array_name, prev_step)

    if st.button("Play Animation"):
        st.info("Running…")
        progress_bar = st.progress(0)

        total_steps = len(history)
        for i, step in enumerate(history):
            prev_step = history[i - 1] if i > 0 else None
            display_step(step, code_lines, code_placeholder, array_placeholders, counter_placeholder, array_name, prev_step)
            progress_bar.progress((i + 1) / total_steps)
            time.sleep(delay)

        st.success("Animation complete!")

def display_step(step, code_lines, code_placeholder, array_placeholders, counter_placeholder, array_name, prev_step=None):
    """
    Display a single step in the algorithm visualization.
    Highlights array elements that changed compared to the previous step.
    """
    arrays = step.get(array_name) or []
    prev_arrays = (prev_step.get(array_name) or [[] for _ in arrays]) if prev_step else [[] for _ in arrays]

    # Highlight changed elements
    highlighted_arrays = []
    for arr, prev_arr in zip(arrays, prev_arrays):
        line = []
        for v, pv in zip(arr, prev_arr):
            if pv is None or v != pv:
                line.append(f"**{v}**")  # highlight changed values
            else:
                line.append(str(v))
        highlighted_arrays.append(", ".join(line))

    # Display arrays in persistent placeholders
    for placeholder, arr_line in zip(array_placeholders, highlighted_arrays):
        placeholder.markdown(f"[{arr_line}]")

    # Display counters
    counters = step.get("counters") or {}
    if counters:
        import pandas as pd
        df = pd.DataFrame(list(counters.items()), columns=["Operation", "Count"])
        counter_placeholder.dataframe(df.set_index("Operation"))

    # Highlight current line in code using st.code
    current_line_no = step.get("line_no")
    highlighted_code = ""
    for i, line in enumerate(code_lines, start=1):
        if i == current_line_no:
            highlighted_code += f"{line}  # <<< current line\n"
        else:
            highlighted_code += f"{line}\n"

    code_placeholder.code(highlighted_code, language="python")

def extract_source_for_algorithm(algo_path, main_func_name, helper_map=None):
    """
    Extracts source code as a string for a main function + optional helpers.
    
    Parameters:
        algo_path (str or Path): Path to the source file
        main_func_name (str): The main algorithm function to extract
        helper_map (dict): Optional dict mapping main functions to helper function names
    
    Returns:
        str: Source code of the selected function(s)
    """
    with open(algo_path, "r") as f:
        src_lines = f.readlines()
        src_str = "".join(src_lines)

    tree = ast.parse(src_str)
    needed_funcs = set([main_func_name])
    if helper_map and main_func_name in helper_map:
        needed_funcs.update(helper_map[main_func_name])

    blocks = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in needed_funcs:
            # AST provides line numbers (1-indexed)
            start = node.lineno - 1
            end = getattr(node, "end_lineno", None)
            if end is None:
                # Fallback: take until next function or end of file
                next_fn_lines = [n.lineno - 1 for n in tree.body if isinstance(n, ast.FunctionDef) and n.lineno > node.lineno]
                end = next_fn_lines[0] if next_fn_lines else len(src_lines)
            blocks.append("".join(src_lines[start:end]))

    return "\n".join(blocks)



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

def save_cache(algo_key, data, mode="random"):
    data_with_mode = data.copy()
    data_with_mode["input_mode"] = mode  # Add input mode
    path = ALGO_DIR / f"{algo_key}.joblib"
    joblib.dump(data_with_mode, path)

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
    """Read recent runs from JSON file, safely."""
    if RECENT_RUNS_FILE.exists():
        try:
            content = RECENT_RUNS_FILE.read_text().strip()
            if not content:
                return []
            return json.loads(content)
        except json.JSONDecodeError:
            return []
    return []

def _write_recent_runs(runs):
    """Write recent runs to JSON file."""
    with open(RECENT_RUNS_FILE, "w") as f:
        json.dump(runs, f, indent=2)

def save_recent_run(algorithm, n, arr, input_array, result, mode="random", history=[]):
    runs = _read_recent_runs()  # load existing runs

    run_record = {
        "algorithm": algorithm,
        "timestamp": int(time.time() * 1000),
        "history": history,
        "params": {
            "n": n,
            "arr": arr,
            "mode": mode,
        },
        "input_meta": {
            "length": extract_input_length(input_array),
            "range_max": n,
        },
        "results": result,
    }

    runs.append(run_record)  # add new run
    # Sort descending by timestamp
    runs.sort(key=lambda r: r["timestamp"], reverse=True)
    # Keep only last 10 runs
    runs = runs[:10]

    _write_recent_runs(runs)


def load_recent_runs(limit=None):
    """Load recent runs, sorted by timestamp descending."""
    runs = _read_recent_runs()
    runs = sorted(runs, key=lambda r: r["timestamp"], reverse=True)
    if limit:
        return runs[:limit]
    return runs

def load_most_recent_run():
    """Load the single most recent run based on timestamp, or None if none exist."""
    runs = _read_recent_runs()
    if not runs:
        return None
    return max(runs, key=lambda r: r["timestamp"])


def sorting_generation(func_name, n_range, arr_length, mode="random", base_array=None, user_func=None):
    """Generate input array for sorting algorithms."""
    if mode == "random":
        arr = [randint(1, n_range) for _ in range(arr_length)]
    elif mode == "guided":
        # Generate common edge-case arrays
        case = choice(["sorted", "reverse", "all_same", "few_unique"])
        if case == "sorted":
            arr = list(range(1, arr_length + 1))
        elif case == "reverse":
            arr = list(range(arr_length, 0, -1))
        elif case == "all_same":
            val = randint(1, n_range)
            arr = [val] * arr_length
        elif case == "few_unique":
            unique_vals = [randint(1, n_range) for _ in range(max(1, arr_length // 5))]
            arr = [choice(unique_vals) for _ in range(arr_length)]
    elif mode == "evolution":
        if base_array is None:
            raise ValueError("Evolution mode requires a base_array")
        arr = base_array.copy()
        swaps = max(1, arr_length // 5)
        for _ in range(swaps):
            i, j = randint(0, arr_length - 1), randint(0, arr_length - 1)
            arr[i], arr[j] = arr[j], arr[i]
    elif mode == "user":
        if user_func is None:
            raise ValueError("User mode requires user_func")
        arr = user_func(n_range, arr_length)
    else:
        raise ValueError(f"Unknown mode {mode}")
    return [arr]

def search_generation(func_name, n_range, arr_length, mode="random", base_array=None, user_func=None):
    """Generate input array and target for searching algorithms."""
    arr = sorting_generation(n_range, arr_length, mode, base_array, user_func)[0]
    target = randint(1, n_range)
    return [arr, target]

# Expand the graph generation to support different types of graph inputs for different graph algorithms, currently just returns the same graph for testing purposes
def graph_generation(func_name, *args):
    """Return default test graph for DFS/BFS (expandable for more cases)."""
    graph = {
        'A': ['B', 'C'],
        'B': ['D', 'E'],
        'C': ['F'],
        'D': [],
        'E': ['F'],
        'F': []
    }
    start_node = 'A'
    return [graph, start_node]

def activity_generation(func_name, n_range, arr_length, mode="random", base_array=None, user_func=None):
    """Generate activities (start, end pairs) for scheduling algorithms."""
    if mode == "random":
        activities = [(randint(1, n_range), randint(1, n_range)) for _ in range(arr_length)]
    elif mode == "guided":
        case = choice(["all_overlap", "non_overlap", "sequential"])
        if case == "all_overlap":
            start = randint(1, n_range // 2)
            end = start + randint(1, n_range // 2)
            activities = [(start, end) for _ in range(arr_length)]
        elif case == "non_overlap":
            activities = [(i * 2, i * 2 + 1) for i in range(arr_length)]
        elif case == "sequential":
            activities = [(i, i + 1) for i in range(arr_length)]
    elif mode == "evolution":
        if base_array is None:
            raise ValueError("Evolution mode requires a base_array")
        activities = base_array.copy()
        # Mutate: swap start/end of random activities
        for _ in range(max(1, arr_length // 5)):
            i = randint(0, arr_length - 1)
            s, e = activities[i]
            activities[i] = (e, s) if randint(0, 1) else (s, e)
    elif mode == "user":
        if user_func is None:
            raise ValueError("User mode requires user_func")
        activities = user_func(n_range, arr_length)
    else:
        raise ValueError(f"Unknown mode {mode}")
    return [activities]

# Allow input generation for matrix-based algorithms like Floyd-Warshall, Prim's, Kruskal's, etc. to be generated here as well
# Implement Graph generation methods