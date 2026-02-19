import pathlib
import time
import ast, sys
from concurrent.futures import ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh
from navigation import show_sidebar

import streamlit as st
import pandas as pd
import plotly.express as px
from helpers import (
    run_ast_analysis, save_cache, load_cache, drop_cache, 
    sorting_generation, search_generation, graph_generation,
      activity_generation, save_recent_run, load_recent_runs, 
      extract_source_for_algorithm, load_most_recent_run
)


root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root / "src" / "algorithm_analysis_tool" / "algorithms.py"
sys.path.insert(0, str(ast_visitor_path))


def display_charts(counters_dict, arr_length=None, title_suffix=""):
    df = pd.DataFrame({
        "Operation": list(counters_dict.keys()),
        "Count": list(counters_dict.values())
    })

    # Filter by selected operations
    selected_ops = st.session_state.get("selected_operations")
    if selected_ops:
        df = df[df["Operation"].isin(selected_ops)]

    # Total counts bar chart
    fig = px.bar(df, x="Operation", y="Count", text="Count",
                 title=f"Operation Count Distribution {title_suffix}")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # Operation distribution (pie chart)
    fig2 = px.pie(df, names="Operation", values="Count",
                  title=f"Operation Distribution (%) {title_suffix}")
    st.plotly_chart(fig2, use_container_width=True)

    # Normalized metrics per element
    if arr_length:
        if arr_length and pd.api.types.is_numeric_dtype(df["Count"]):
            df["Per Element"] = df["Count"] / arr_length
        fig3 = px.bar(df, x="Operation", y="Per Element", text="Per Element",
                      title=f"Normalized Operations per Element (n={arr_length}) {title_suffix}")
        fig3.update_traces(textposition="outside")
        st.plotly_chart(fig3, use_container_width=True)

    # Comparisons vs assignments
    if all(op in df["Operation"].values for op in ["comparisons", "assignments"]):
        comp_assign_df = df[df["Operation"].isin(["comparisons", "assignments"])]
        fig4 = px.bar(comp_assign_df, x="Operation", y="Count", text="Count",
                      title=f"Comparisons vs Assignments {title_suffix}")
        fig4.update_traces(textposition="outside", marker_color=["#636EFA", "#EF553B"])
        st.plotly_chart(fig4, use_container_width=True)

    # Loop iterations metric
    if "loop_iterations" in df["Operation"].values:
        loop_iter = df[df["Operation"] == "loop_iterations"]["Count"].values[0]
        st.metric("Total loop iterations", f"{loop_iter:,}")

    # Raw data table
    st.subheader(f"Raw Operation Data {title_suffix}")
    st.dataframe(df.set_index("Operation"))


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

st.set_page_config(page_title="Operation Counter", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

counters_template = {
    "assignments": 0,
    "indexing": 0,
    "function_calls": 0,
    "returns": 0,
    "comparisons": 0,
    "arithmetic": 0,
    "loop_nodes": 0,
    "loop_iterations": 0
}

ALGO_GROUPS = {
    "Sorting": ["bubble_sort", "merge_sort", "insertion_sort", "quicksort"],
    "Searching": ["linear_search", "binary_search"],
    "Graph": ["dfs", "bfs"],
    "Scheduling": ["activity_selection"],
}

def get_executor():
    return ThreadPoolExecutor(max_workers=1)

# Session state defaults
st.session_state.setdefault("executor", get_executor())
st.session_state.setdefault("counters", counters_template.copy())
st.session_state.setdefault("status", "")
st.session_state.setdefault("future", None)
st.session_state.setdefault("is_running", False)
st.session_state.setdefault("input_generated", False)
st.session_state.setdefault("generated_input", None)
st.session_state.setdefault("generated_params", None)


@st.cache_resource
def load_ast(path):
    with open(path, "r") as f:
        return ast.parse(f.read())


tree = load_ast(algo_path)

show_sidebar()
st.title("Algorithm Analysis Tool: Operation Counter")


tab1, tab2, tab3 = st.tabs(["Single Run", "Compare Algos", "History"])


# ===========================
# Tab 1: Single Run
# ===========================
with tab1:
    disabled = st.session_state.get("is_running", False)

    group = st.selectbox("Algorithm Group", list(ALGO_GROUPS.keys()), disabled=disabled)
    selected_function = st.selectbox(
        "Algorithm", ALGO_GROUPS[group], disabled=disabled, key="selected_function"
    )

    user_has_run = st.session_state.future is not None or st.session_state.is_running
    cache_key = selected_function

    if not user_has_run:
        cached = load_cache(cache_key)
        if cached is not None:
            st.session_state.counters = cached.get("counters", counters_template.copy())
            st.session_state.arr_length = cached.get("meta", {}).get("length")

    # --- Input controls ---
    current_params = None

    if group in {"Sorting", "Searching", "Scheduling"}:
        n_label = "Select max integer value" if group != "Scheduling" else "Select max time value"
        arr_label = "Select array length" if group != "Scheduling" else "Select number of activities"

        # Slider / manual input
        input_type = st.radio("Choose input method", ["Slider (1–10000)", "Manual input"], key="slider_input")

        # Input generation mode
        mode_input = st.radio(
            "Choose input generation method",
            ["Random", "Guided / Edge-case", "Evolutionary", "User-defined"],
            key="input_gen_mode"
        )

        # Map to internal mode
        mode_map = {
            "Random": "random",
            "Guided / Edge-case": "guided",
            "Evolutionary": "evolution",
            "User-defined": "user"
        }
        mode = mode_map[mode_input]

        col1, col2 = st.columns(2)

        with col1:
            if input_type.startswith("Slider"):
                n = st.slider(n_label, 1, 10000, 100, key="slider_n", disabled=disabled)
            else:
                n = st.number_input(n_label, 1, value=100, key="free_input_n", disabled=disabled)

        with col2:
            if input_type.startswith("Slider"):
                arr = st.slider(arr_label, 1, 10000, 100, key="slider_arr", disabled=disabled)
            else:
                arr = st.number_input(arr_label, 1, value=100, key="free_input_arr", disabled=disabled)

        run_args = (selected_function, n, arr)
        current_params = {"algo": selected_function, "n": n, "arr": arr}

    else:
        st.info("Using default test graph for DFS/BFS")
        run_args = (selected_function,)
        current_params = {"algo": selected_function}

    # --- User-defined function input ---
    user_func = None
    if mode == "user":
        code_input = st.text_area(
            "Define your input function as `def gen(n_range, arr_length): ...`",
            key="user_func_code"
        )
        if code_input:
            local_vars = {}
            try:
                exec(code_input, {}, local_vars)
                user_func = local_vars.get("gen")
                if not callable(user_func):
                    st.error("Your function must define `gen(n_range, arr_length)`")
                    user_func = None
            except Exception as e:
                st.error(f"Error in user function: {e}")
                user_func = None

    # Invalidate previous input if params changed
    if st.session_state.generated_params != current_params:
        st.session_state.input_generated = False
        st.session_state.generated_input = None

    sorting_algos = {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}
    search_algos = {"linear_search", "binary_search"}
    graph_algos = {"dfs", "bfs"}
    activity_algos = {"activity_selection"}

    if st.button("Generate New Input Data", disabled=disabled):
        selected_function = run_args[0]
        base_array = None
        if mode == "evolution" and st.session_state.generated_input:
            base_array = st.session_state.generated_input[0]

        match selected_function:
            case name if name in sorting_algos:
                st.session_state.generated_input = sorting_generation(
                    *run_args, mode=mode, base_array=base_array, user_func=user_func
                )
            case name if name in search_algos:
                st.session_state.generated_input = search_generation(
                    *run_args, mode=mode, base_array=base_array, user_func=user_func
                )
            case name if name in activity_algos:
                st.session_state.generated_input = activity_generation(
                    *run_args, mode=mode, base_array=base_array, user_func=user_func
                )
            case name if name in graph_algos:
                st.session_state.generated_input = graph_generation(*run_args)

        st.session_state.generated_params = current_params
        st.session_state.input_generated = True

    if st.session_state.generated_input is not None:
        st.caption("Generated input")

    # --- Run AST Analysis ---
    if st.button("Run AST Analysis", disabled=st.session_state.is_running):
        drop_cache(cache_key)
        st.session_state.status = "Running analysis..."
        st.session_state.is_running = True

        future = st.session_state.executor.submit(
            run_ast_analysis,
            *run_args,
            input_arr=st.session_state.generated_input if st.session_state.input_generated else None,
            input_generated=st.session_state.input_generated,
            input_mode = mode
        )

        st.session_state.future = future
        st.rerun()

    if st.button("Cancel Run", disabled=not st.session_state.is_running):
        st.session_state.status = "Cancelling..."
        if st.session_state.future:
            st.session_state.future.cancel()
        st.session_state.is_running = False
        st.session_state.future = None

    if st.session_state.is_running:
        with st.spinner("Analyzing AST and executing instrumented code…"):
            st.caption("Parsing → instrumenting → executing")

    if st.session_state.future:
        st_autorefresh(interval=2000, key="poll_ast")
        if st.session_state.future.done():
            payload = st.session_state.future.result()
            st.session_state.arr_length = payload.get("meta", {}).get("length")
            if payload:
                st.session_state.counters = payload["counters"]
                st.session_state.status = f"Analysis of '{selected_function}' completed ✅"
                save_recent_run(
                    payload["meta"]["algorithm"],
                    n if "n" in locals() else None,
                    arr if "arr" in locals() else None,
                    payload["input"],
                    payload["counters"],
                    mode=mode, 
                    history=payload.get("history", [])
                )
                save_cache(cache_key, payload, mode=mode)
            else:
                st.session_state.status = f"Function '{selected_function}' not found"
            st.session_state.future = None
            st.session_state.is_running = False

    if st.session_state.status:
        st.info(st.session_state.status)

    # Operation selection
    counters = st.session_state.counters
    st.multiselect(
        "Select operations to include:",
        options=list(counters.keys()),
        default=list(counters.keys()),
        key="selected_operations",
    )

    arr_length = st.session_state.get("arr_length")
    if not isinstance(arr_length, (int, float)):
        arr_length = None

    display_charts(counters, arr_length)


# ===========================
# Tab 2: Compare Cached Runs
# ===========================
with tab2:
    st.subheader("Compare Two Cached Algorithm Runs")
    CACHE_DIR = pathlib.Path("cache/algorithms")
    cached_files = [f.stem for f in CACHE_DIR.glob("*.joblib")]

    if len(cached_files) < 2:
        st.info("At least two cached runs are required to compare.")
    else:
        algo1_key = st.selectbox("Select first algorithm", cached_files, index=0)
        algo2_options = [f for f in cached_files if f != algo1_key]
        algo2_key = st.selectbox("Select second algorithm", algo2_options, index=0)

        payload1 = load_cache(algo1_key)
        payload2 = load_cache(algo2_key)

        counters1 = counters2 = None
        mode1 = mode2 = "unknown"
        if payload1 and payload2:
            counters1 = payload1.get("counters")
            counters2 = payload2.get("counters")
            mode1 = payload1.get("meta", {}).get("input_mode", "unknown")
            mode2 = payload2.get("meta", {}).get("input_mode", "unknown")

        if counters1 is not None and counters2 is not None:
            df1 = pd.DataFrame({
                "Operation": list(counters1.keys()),
                "Count": list(counters1.values()),
                "Algorithm": f"{algo1_key} ({mode1})"  # show mode
            })
            df2 = pd.DataFrame({
                "Operation": list(counters2.keys()),
                "Count": list(counters2.values()),
                "Algorithm": f"{algo2_key} ({mode2})"  # show mode
            })
            df = pd.concat([df1, df2])

            fig = px.bar(
                df, x="Operation", y="Count", color="Algorithm", barmode="group", text="Count",
                title="Operation Count Comparison"
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Raw Data Comparison")
            st.dataframe(df.pivot(index="Operation", columns="Algorithm", values="Count").fillna(0))

    st.header("Recent Runs")
    recent_runs = load_recent_runs()
    for run in recent_runs:
        ts = time.strftime("%H:%M:%S", time.localtime(run["timestamp"] / 1000))
        mode = run.get("params", {}).get("mode", "unknown")  # get input generation mode
        st.write(
            f"**{run['algorithm']}** | "
            f"n={run['params']['n']} | "
            f"len={run['input_meta']['length']} | "
            f"mode={mode} | "
            f"{ts}"
        )
        st.json(run["results"])

with tab3:
    last_run = load_most_recent_run() 
    if last_run:
        history = last_run.get("history", [])
        algorithm_name = last_run["algorithm"]

        # Optional: define helpers if needed
        helper_map = {
            "merge_sort": ["merge"]
        }

        source_code = extract_source_for_algorithm(
            "src/algorithm_analysis_tool/algorithms.py",
            algorithm_name,
            helper_map=helper_map
        )

        st.subheader(f"History: {algorithm_name}")

        # Check if arrays were stored in history
        can_visualize = any(snapshot.get("arrays") is not None for snapshot in history)

        if can_visualize and source_code.strip():
            visualize_algorithm(history, source_code)
        else:
            st.warning(
                "Animation cannot be run: input arrays were too large, so snapshots were not stored."
            )
    else:
        st.info("No recent runs to visualize.")