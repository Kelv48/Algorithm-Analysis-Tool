import pathlib
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


# -----------------------------
# Paths & Setup
# -----------------------------
root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root / "src" / "algorithm_analysis_tool" / "algorithms.py"
sys.path.insert(0, str(ast_visitor_path))

st.set_page_config(page_title="Algorithm Dashboard", page_icon="📊", layout="wide")

ALGO_GROUPS = {
    "Sorting": ["bubble_sort", "merge_sort", "insertion_sort", "quicksort"],
    "Searching": ["linear_search", "binary_search"],
    "Graph": ["dfs", "bfs"],
    "Scheduling": ["activity_selection"],
}

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

# -----------------------------
# Executor & Session State
# -----------------------------
def get_executor():
    return ThreadPoolExecutor(max_workers=1)

st.session_state.setdefault("executor", get_executor())
st.session_state.setdefault("counters", counters_template.copy())
st.session_state.setdefault("status", "")
st.session_state.setdefault("future", None)
st.session_state.setdefault("is_running", False)
st.session_state.setdefault("input_generated", False)
st.session_state.setdefault("generated_input", None)
st.session_state.setdefault("generated_params", None)
st.session_state.setdefault("arr_length", None)

# -----------------------------
# Load AST once
# -----------------------------
@st.cache_resource
def load_ast(path):
    with open(path, "r") as f:
        return ast.parse(f.read())

tree = load_ast(algo_path)

show_sidebar()
st.title("Algorithm Analysis Tool: Operation Counter")


with st.sidebar:
    st.title("Controls")
    group = st.selectbox("Algorithm Group", list(ALGO_GROUPS.keys()))
    selected_function = st.selectbox("Algorithm", ALGO_GROUPS[group])

    st.subheader("Input Configuration")
    input_type = st.radio("Input Method", ["Slider (1–1000)", "Manual input"])
    mode_input = st.radio(
        "Input Generation Mode",
        ["Random", "Guided / Edge-case", "Evolutionary", "User-defined"]
    )
    mode_map = {"Random": "random", "Guided / Edge-case": "guided", 
                "Evolutionary": "evolution", "User-defined": "user"}
    mode = mode_map[mode_input]



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

    st.subheader(f"Raw Operation Data {title_suffix}")
    st.dataframe(df.set_index("Operation"))


# -----------------------------
# Main Tabs
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Single Run", "Compare Runs", "History / Visualization"])


# ===========================
# Tab 1: Single Run
# ===========================
with tab1:
    st.header("Run Algorithm & AST Analysis")
    disabled = st.session_state.get("is_running", False)

    # Use sidebar selections
    cache_key = selected_function
    user_has_run = st.session_state.future is not None or st.session_state.is_running

    # Load cached counters if no run yet
    if not user_has_run:
        cached = load_cache(cache_key)
        if cached is not None:
            st.session_state.counters = cached.get("counters", counters_template.copy())
            st.session_state.arr_length = cached.get("meta", {}).get("length")

    # --- Input sliders / number input on main page ---
    current_params = None
    if group in {"Sorting", "Searching", "Scheduling"}:
        n_label = "Select max integer value" if group != "Scheduling" else "Select max time value"
        arr_label = "Select array length" if group != "Scheduling" else "Select number of activities"
        
        col1, col2 = st.columns(2)
        with col1:
            if input_type.startswith("Slider"):
                n = st.slider(n_label, 1, 1000, 100, key="slider_n", disabled=disabled)
            else:
                n = st.number_input(n_label, 1, value=100, key="free_input_n", disabled=disabled)

        with col2:
            if input_type.startswith("Slider"):
                arr = st.slider(arr_label, 1, 1000, 100, key="slider_arr", disabled=disabled)
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

     # Reset generated input if parameters changed
    if st.session_state.generated_params != current_params:
        st.session_state.input_generated = False
        st.session_state.generated_input = None

    sorting_algos = {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}
    search_algos = {"linear_search", "binary_search"}
    graph_algos = {"dfs", "bfs"}
    activity_algos = {"activity_selection"}

    # --- Generate Input Data ---
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

     # --- Operation Selection & Charts ---
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


# -----------------------------
# Tab 2: Compare Cached Runs
# -----------------------------
with tab2:
    st.header("Compare Cached Algorithm Runs")
    CACHE_DIR = pathlib.Path("cache/algorithms")
    cached_files = [f.stem for f in CACHE_DIR.glob("*.joblib")]
    if len(cached_files) < 2:
        st.info("At least two cached runs are required to compare.")
    else:
        algo1_key = st.selectbox("Select first algorithm", cached_files)
        algo2_key = st.selectbox("Select second algorithm", [f for f in cached_files if f != algo1_key])
        payload1, payload2 = load_cache(algo1_key), load_cache(algo2_key)
        if payload1 and payload2:
            df1 = pd.DataFrame({"Operation": list(payload1["counters"].keys()), "Count": list(payload1["counters"].values()), "Algorithm": algo1_key})
            df2 = pd.DataFrame({"Operation": list(payload2["counters"].keys()), "Count": list(payload2["counters"].values()), "Algorithm": algo2_key})
            df = pd.concat([df1, df2])
            fig = px.bar(df, x="Operation", y="Count", color="Algorithm", barmode="group", text="Count", title="Operation Count Comparison")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
            st.subheader("Raw Data")
            st.dataframe(df.pivot(index="Operation", columns="Algorithm", values="Count").fillna(0))

# -----------------------------
# Tab 3: History / Step Visualization
# -----------------------------
with tab3:
    st.header("Recent Runs & Algorithm Visualization")

    # Load last run
    last_run = load_most_recent_run()
    if last_run:
        history = last_run.get("history", [])
        algorithm_name = last_run["algorithm"]

        helper_map = {"merge_sort": ["merge"]}
        source_code = extract_source_for_algorithm(algo_path, algorithm_name, helper_map=helper_map)

        st.subheader(f"Last Run History: {algorithm_name}")

        # Only allow animation if arrays exist in history
        can_visualize = any(snapshot.get("arrays") for snapshot in history)
        if can_visualize and source_code.strip():
            from helpers import visualize_algorithm
            visualize_algorithm(history, source_code)
        else:
            st.warning("Animation cannot run: input arrays were too large, so snapshots were not stored.")
    else:
        st.info("No recent runs to visualize.")

    # -----------------------------
    # Show last 10 runs as cards
    # -----------------------------
    st.subheader("Recent Runs Summary (Top Counters)")

    recent_runs = load_recent_runs()[:10]
    if recent_runs:
        rows = []
        for run in recent_runs:
            counters = run.get("results", {})
            rows.append({
                "Algorithm": run["algorithm"],
                "n": run.get("params", {}).get("n", "-"),
                "Length": run.get("input_meta", {}).get("length", "-"),
                "Mode": run.get("params", {}).get("mode", "-"),
                "Comparisons": counters.get("comparisons", 0),
                "Assignments": counters.get("assignments", 0),
                "Loop Iter": counters.get("loop_iterations", 0)
            })

        df = pd.DataFrame(rows)
        st.dataframe(df.style.background_gradient(cmap="Blues", subset=["Comparisons", "Assignments", "Loop Iter"]))
    else:
        st.info("No Runs to Display")