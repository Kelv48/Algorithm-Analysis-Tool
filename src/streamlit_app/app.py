import pathlib
import time
import ast, sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh
from navigation import show_sidebar

import streamlit as st
import pandas as pd
import plotly.express as px
from helpers import run_ast_analysis, save_cache, load_cache, drop_cache, sorting_generation, search_generation, graph_generation, activity_generation, save_recent_run, load_recent_runs


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


tab1, tab2 = st.tabs(["Single Run", "Compare Algos"])


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
            st.session_state.counters = cached["counters"]
            st.session_state.arr_length = cached["meta"]["length"]

    # Input controls
    current_params = None

    # Change input controls based on algo type
    # Different algos will have a differeny UI
    # Allow multiple different generation methods for each algo type, i.e. random generation, manual input, sliders, n to 10, etc
    if group in {"Sorting", "Searching", "Scheduling"}:
        n_label = "Select max integer value" if group != "Scheduling" else "Select max time value"
        arr_label = "Select array length" if group != "Scheduling" else "Select number of activities"
        input_type = st.radio("Choose input method", ["Slider (1–10000)", "Manual input"], key="slider_input")
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

    # Invalidate generated input if params changed
    if st.session_state.generated_params != current_params:
        st.session_state.input_generated = False
        st.session_state.generated_input = None

    sorting_algos = {"bubble_sort", "merge_sort", "insertion_sort", "quicksort"}
    search_algos = {"linear_search", "binary_search"}
    graph_algos = {"dfs", "bfs"}
    activity_algos = {"activity_selection"}
    if st.button("Generate New Input Data", disabled=disabled):
        selected_function = run_args[0]
        match selected_function:
            case name if name in sorting_algos:
                st.text(run_args)
                st.session_state.generated_input = sorting_generation(*run_args)
            case name if name in search_algos:
                st.session_state.generated_input = search_generation(*run_args)
            case name if name in graph_algos:
                st.session_state.generated_input = graph_generation(*run_args)
            case name if name in activity_algos:
                st.session_state.generated_input = activity_generation(*run_args)
            case _:
                raise ValueError(f"Unknown function {selected_function} for input generation")
        st.session_state.generated_params = current_params
        st.session_state.input_generated = True

    if st.session_state.generated_input is not None:
        st.caption("Generated input preview:")
        preview = st.session_state.generated_input
        if isinstance(preview, (list, tuple)) and len(preview) > 10:
            preview = preview[:10]
        st.write(preview)

    if st.button("Run AST Analysis", disabled=st.session_state.is_running):
        drop_cache(cache_key)
        st.session_state.status = "Running analysis..."
        st.session_state.is_running = True

        if st.session_state.input_generated:
            st.success("Using generated input (locked to current parameters)")
            future = st.session_state.executor.submit(
                run_ast_analysis,
                *run_args,
                input_arr=st.session_state.generated_input,
                input_generated=True,
            )
        else:
            st.warning("No generated input — auto-generating on run")
            future = st.session_state.executor.submit(
                run_ast_analysis,
                *run_args,
                input_arr=None,
                input_generated=False,
            )

        st.session_state.future = future
        st.rerun()

    if st.button("Cancel Run", disabled=not st.session_state.is_running):
        st.session_state.status = "Cancelling..."

        if st.session_state.future:
            st.session_state.future.cancel()

        st.session_state.is_running = False
        st.session_state.future = None
        # st.session_state.executor = ThreadPoolExecutor(max_workers=1)

    if st.session_state.is_running:
        with st.spinner("Analyzing AST and executing instrumented code…"):
            st.caption("Parsing → instrumenting → executing")

    if st.session_state.future:
        st_autorefresh(interval=2000, key="poll_ast")

        if st.session_state.future.done():
            result = st.session_state.future.result()
            payload = result
            st.session_state.arr_length = payload["meta"]["length"]
            if payload:
                st.session_state.counters = payload["counters"]
                st.session_state.status = f"Analysis of '{selected_function}' completed ✅"
                save_recent_run(
                    payload["meta"]["algorithm"],
                    n if "n" in locals() else None,
                    arr if "arr" in locals() else None,
                    payload["input"],
                    payload["counters"]
                )
                save_cache(cache_key, result)
            else:
                st.session_state.status = f"Function '{selected_function}' not found"
            st.session_state.future = None
            st.session_state.is_running = False

    if st.session_state.status:
        st.info(st.session_state.status)

    counters = st.session_state.counters

    st.multiselect(
        "Select operations to include:",
        options=list(counters.keys()),
        default=list(counters.keys()),
        key="selected_operations",
    )

    arr_length = st.session_state.get("arr_length")

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

        if payload1 and payload2:
            counters1 = payload1["counters"]
            counters2 = payload2["counters"]

        if counters1 is not None and counters2 is not None:
            df1 = pd.DataFrame({"Operation": list(counters1.keys()), "Count": list(counters1.values()), "Algorithm": algo1_key})
            df2 = pd.DataFrame({"Operation": list(counters2.keys()), "Count": list(counters2.values()), "Algorithm": algo2_key})
            df = pd.concat([df1, df2])

            fig = px.bar(df, x="Operation", y="Count", color="Algorithm", barmode="group", text="Count",
                         title="Operation Count Comparison")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Raw Data Comparison")
            st.dataframe(df.pivot(index="Operation", columns="Algorithm", values="Count").fillna(0))
    st.header("TEMP Placement")

    recent_runs = load_recent_runs()

    for run in recent_runs:
        ts = time.strftime(
            "%H:%M:%S",
            time.localtime(run["timestamp"] / 1000)
        )

        st.write(
            f"**{run['algorithm']}** | "
            f"n={run['params']['n']} | "
            f"len={run['input_meta']['length']} | "
            f"{ts}"
        )

        st.json(run["results"])