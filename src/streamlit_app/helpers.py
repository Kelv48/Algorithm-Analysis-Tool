import ast, operator, string
from random import randint, choice, sample
import pathlib, joblib, json, time, copy
import streamlit as st
import pandas as pd

from algorithm_analysis_tool.ast_helpers import resolve_helpers
from algorithm_analysis_tool.ast_visitor import ASTVisitor
from algorithm_analysis_tool.execution_session import ExecutionSession, not_in

root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root/ "src" / "algorithm_analysis_tool" / "algorithms.py"

# Ast Runner

def run_ast_analysis(func_name, *args, input_arr=None, input_generated=False, input_mode=None, job_id=None, **kwargs):
    """
    Execute an algorithm with AST instrumentation using ExecutionSession,
    recording operation counts and maintaining a local history of operations
    for visualization/animation.

    Parameters:
        func_name (str): Name of the algorithm function in algorithms.py
        *args: Positional arguments for the algorithm
        input_arr (list, optional): Pre-generated input array
        input_generated (bool): Whether input_arr is provided
        input_mode (str, optional): Input generation mode for caching
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
    session = ExecutionSession()

    with open(algo_path, "r") as f:
        tree = ast.parse(f.read())

    # Map function names to AST nodes
    function_map = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if func_name not in function_map:
        raise ValueError(f"Function {func_name} not found in algorithms.py")

    # Include helper functions if needed
    needed_functions = resolve_helpers(func_name, function_map)
    selected_nodes = [function_map[name] for name in function_map if name in needed_functions]

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])

    visitor = ASTVisitor(session)
    module_ast = visitor.visit(module_ast)
    ast.fix_missing_locations(module_ast)

    exec_globals = {
        "SESSION": session,            
        "arrays": [input_arr] if input_arr else [],
        "operator": operator,
        "not_in": not_in
    }

    code_obj = compile(module_ast, filename="<ast>", mode="exec")
    exec(code_obj, exec_globals)

    sorting_algos = {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}
    search_algos = {"linear_search", "binary_search"}
    graph_algos = {"dfs", "bfs"}
    activity_algos = {"activity_selection"}

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
        "counters": session.counters,
        "input": final_args,
        "history": session.history,
        "meta": {
            "length": extract_input_length(final_args),
            "algorithm": func_name,
            "input_mode": input_mode
        },
        "job_id" : job_id
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



# Visualization helper functions 

def visualize_algorithm(history, source_code, array_name="arrays", delay=0.5, max_animation_length=20, algorithm_name=""):
    st.subheader(f"Algorithm Step-through Visualization for {algorithm_name}")

    if not history:
        st.info("No history to visualize.")
        return

    mode = "array" if any(snapshot.get(array_name) is not None for snapshot in history) else "graph"

    if mode == "array":
        first_arrays = history[0].get(array_name) or []
        if first_arrays and len(first_arrays[0]) > max_animation_length:
            st.warning(f"Array length is {len(first_arrays[0])}. Animation disabled for arrays larger than 20.")
            return
        array_placeholders = [st.empty() for _ in range(len(first_arrays))]
    else:
        array_placeholders = [st.empty(), st.empty()]  # Graph nodes & edges

    code_placeholder = st.empty()
    counter_placeholder = st.empty()

    step_slider = st.slider("Step", 0, len(history)-1, 0, key=f"step_slider_{algorithm_name}")
    prev_step = history[step_slider-1] if step_slider > 0 else None
    current_step = history[step_slider]

    display_step(
        current_step,
        code_lines=source_code.splitlines(),
        code_placeholder=code_placeholder,
        array_placeholders=array_placeholders,
        counter_placeholder=counter_placeholder,
        array_name=array_name,
        prev_step=prev_step,
        mode=mode
    )

    # Play animation button
    if st.button("Play Animation"):
        import time
        st.info("Running…")
        progress_bar = st.progress(0)
        for i, step in enumerate(history):
            prev_step = history[i-1] if i > 0 else None
            display_step(
                step,
                code_lines=source_code.splitlines(),
                code_placeholder=code_placeholder,
                array_placeholders=array_placeholders,
                counter_placeholder=counter_placeholder,
                array_name=array_name,
                prev_step=prev_step,
                mode=mode
            )
            progress_bar.progress((i+1)/len(history))
            time.sleep(delay)
        st.success("Animation complete!")


def display_step(step, code_lines, code_placeholder, array_placeholders=None, counter_placeholder=None, array_name="arrays", prev_step=None, mode="array"):
    """
    Display a single step in the algorithm visualization.
    Mode can be 'array' or 'graph'.
    """
    current_line_no = step.get("line_no")
    highlighted_code = ""
    for i, line in enumerate(code_lines, start=1):
        if i == current_line_no:
            highlighted_code += f"{line}  # <<< current line\n"
        else:
            highlighted_code += f"{line}\n"
    code_placeholder.code(highlighted_code, language="python")

    if mode == "array" and array_placeholders:
        arrays = step.get(array_name) or []
        prev_arrays = (prev_step.get(array_name) or [[] for _ in arrays]) if prev_step else [[] for _ in arrays]
        highlighted_arrays = []
        for arr, prev_arr in zip(arrays, prev_arrays):
            line = []
            for v, pv in zip(arr, prev_arr):
                if pv is None or v != pv:
                    line.append(f"**{v}**")
                else:
                    line.append(str(v))
            highlighted_arrays.append(", ".join(line))

        for placeholder, arr_line in zip(array_placeholders, highlighted_arrays):
            placeholder.markdown(f"[{arr_line}]")
    elif mode == "graph":
        nodes = step.get("nodes", [])
        visited_edges = step.get("visited_edges", [])
        if array_placeholders:
            array_placeholders[0].markdown(f"**Nodes visited:** {nodes}")
            if len(array_placeholders) > 1:
                array_placeholders[1].markdown(f"**Edges traversed:** {visited_edges}")

    counters = step.get("counters") or {}
    if counters and counter_placeholder:
        df = pd.DataFrame(list(counters.items()), columns=["Operation", "Count"])
        counter_placeholder.dataframe(df.set_index("Operation"))


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
            start = node.lineno - 1
            end = getattr(node, "end_lineno", None)
            if end is None:
                next_fn_lines = [n.lineno - 1 for n in tree.body if isinstance(n, ast.FunctionDef) and n.lineno > node.lineno]
                end = next_fn_lines[0] if next_fn_lines else len(src_lines)
            blocks.append("".join(src_lines[start:end]))

    return "\n".join(blocks)



# Note
# Joblib maintains quick cache for per algo cache
# Json maintains detailed cache for recent history

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

    # --- Prepare input meta ---
    input_meta = {
        "length": extract_input_length(input_array),
        "range_max": n,
    }

    saved_input = input_array

    # Special handling for graphs
    if isinstance(input_array, list) and len(input_array) > 0 and isinstance(input_array[0], dict):
        graph_dict = input_array[0]
        edges = []
        for u, vs in graph_dict.items():
            for v in vs:
                edges.append((u, v))
        saved_input = {
            "nodes": list(graph_dict.keys()),
            "edges": edges
        }
        input_meta["length"] = len(graph_dict)

    run_record = {
        "algorithm": algorithm,
        "timestamp": int(time.time() * 1000),
        "history": history,
        "params": {
            "n": n,
            "arr": arr,
            "mode": mode,
        },
        "input_meta": input_meta,
        "results": result,
        "input": saved_input
    }

    runs.append(run_record) 
    runs.sort(key=lambda r: r["timestamp"], reverse=True)
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



# Input Generators

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
            base_array = [randint(1, n_range) for _ in range(arr_length)]
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

def search_generation(func_name, n_range, arr_length,
                      mode="random", base_array=None, user_func=None):
    """Generate input array and target for searching algorithms."""

    # --- Generate array ---
    if mode == "user" and user_func:
        arr = user_func(n_range, arr_length)

    elif mode == "evolution" and base_array is not None:
        arr = base_array

    else:
        if arr_length > n_range:
            raise ValueError("arr_length cannot exceed n_range when generating unique search array values")
        arr = sample(range(1, n_range + 1), arr_length)

    # --- Binary search requires sorted input ---
    if func_name == "binary_search":
        arr = sorted(arr)

    # --- Pick a target ---
    # 70% chance target exists, 30% chance it doesn't
    if randint(1, 10) <= 7 and arr:
        target = arr[randint(0, len(arr) - 1)]
    else:
        target = randint(1, n_range)

    return [arr, target]


def graph_generation(func_name, num_nodes=6, num_edges=8, graph_type="Random", directed=True, start_node=None):
    """
    Generate configurable graphs for DFS/BFS.

    Returns:
        [graph_dict, start_node]
    """

    labels = list(string.ascii_uppercase[:num_nodes])
    graph = {node: [] for node in labels}

    # ---------- Tree / Connected graph ----------
    if graph_type in {"Connected", "Tree"}:
        for i in range(1, num_nodes):
            parent = choice(labels[:i])
            child = labels[i]
            graph[parent].append(child)
            if not directed:
                graph[child].append(parent)

    # ---------- Extra random edges ----------
    max_edges = num_nodes * (num_nodes - 1)
    if not directed:
        max_edges //= 2

    num_edges = min(num_edges, max_edges)

    existing_edges = set()

    for a in graph:
        for b in graph[a]:
            edge = (a, b) if directed else tuple(sorted([a, b]))
            existing_edges.add(edge)

    while len(existing_edges) < num_edges:
        a, b = sample(labels, 2)
        edge = (a, b) if directed else tuple(sorted([a, b]))

        if edge in existing_edges:
            continue

        graph[a].append(b)
        if not directed:
            graph[b].append(a)

        existing_edges.add(edge)

    if start_node is None:
        start_node = choice(labels)

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