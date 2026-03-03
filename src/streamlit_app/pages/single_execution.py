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
      extract_source_for_algorithm, load_most_recent_run,
      visualize_algorithm, apply_seed, matrix_generation
)


# -----------------------------
# Paths & Setup
# -----------------------------
root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root / "src" / "algorithm_analysis_tool" / "algorithms.py"
sys.path.insert(0, str(ast_visitor_path))

st.set_page_config(page_title="Algorithm Dashboard", page_icon="📊", layout="wide")

from algorithm_analysis_tool.config import ALGO_GROUPS, ARRAY_GROUPS, GRAPH_GROUPS, MATRIX_GROUPS, SORTING_ALGOS, SEARCH_ALGOS, GRAPH_ALGOS, ACTIVITY_ALGOS, MATRIX_ALGOS

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
st.session_state.setdefault("last_payload", None)

# -----------------------------
# Load AST once
# -----------------------------
@st.cache_resource
def load_ast(path):
    with open(path, "r") as f:
        return ast.parse(f.read())

tree = load_ast(algo_path)

show_sidebar()
st.title("Algorithm Analysis Tool: Single Execution")


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
    group = st.selectbox("Algorithm Group", list(ALGO_GROUPS.keys()))
    selected_function = st.selectbox("Algorithm", ALGO_GROUPS[group])
    cache_key = selected_function

    # Configuration Section
    with st.container(border=True):
        st.subheader("Configure Inputs")

        current_params = {"algo": selected_function}

        # Default mode
        mode = "random"
        graph_params = {}
        input_type = None

        # ==========================================================
        # ARRAY-BASED ALGORITHMS
        # ==========================================================
        if group in ARRAY_GROUPS:

            input_type = st.radio(
                "Input Method",
                ["Slider (1–1000)", "Manual input"],
                horizontal=True
            )

            mode_input = st.radio(
                "Input Generation Mode",
                ["Random", "Guided / Edge-case", "Evolutionary", "User-defined"],
                horizontal=True,
                help="Choose an mode to be used to generate the array"
            )

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
                    n = st.slider("Max Integer Value", 1, 1000, 100, disabled=disabled)
                else:
                    n = st.number_input("Max Integer Value", 1, value=100, disabled=disabled)

            with col2:
                if input_type.startswith("Slider"):
                    arr = st.slider("Array Length", 1, 1000, 100, disabled=disabled)
                else:
                    arr = st.number_input("Array Length", 1, value=100, disabled=disabled)

            run_args = (selected_function, n, arr)

            current_params.update({
                "n": n,
                "arr": arr,
                "mode": mode
            })

        # ==========================================================
        # GRAPH-BASED ALGORITHMS
        # ==========================================================
        elif group in GRAPH_GROUPS:

            st.subheader("Graph Configuration")

            col1, col2 = st.columns(2)

            with col1:
                num_nodes = st.slider("Number of nodes", 2, 26, 6)

            with col2:
                max_edges = num_nodes * (num_nodes - 1)
                num_edges = st.slider(
                    "Number of edges",
                    1,
                    max_edges,
                    min(8, max_edges)
                )

            graph_type = st.selectbox(
                "Graph type",
                ["Random", "Connected", "Tree"]
            )

            directed = st.checkbox("Directed graph", value=True)

            labels = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:num_nodes])
            start_node = st.selectbox("Start node", labels)

            graph_params = {
                "num_nodes": num_nodes,
                "num_edges": num_edges,
                "graph_type": graph_type,
                "directed": directed,
                "start_node": start_node,
            }

            run_args = (selected_function,)

            current_params.update(graph_params)
        

        # ==========================================================
        # Matrix-BASED ALGORITHMS
        # ==========================================================
        elif group in MATRIX_GROUPS:
            col1, col2, col3 = st.columns(3)

            with col1:
                rows_A = st.number_input("Rows (A)", 1, value=2, step=1, format="%d")

            with col2:
                cols_A = st.number_input("Columns (A)", 1, value=3, step=1, format="%d")

            with col3:
                cols_B = st.number_input("Columns (B)", 1, value=2, step=1, format="%d")

            n = st.slider("Max Integer Value", 1, 1000, value=100, step=1)

  
            mode_input = st.radio(
                "Input Generation Mode", 
                ["Random", "Guided / Edge-case", "Evolutionary", "User-defined"],
                horizontal=True,
                help="Choose a mode to be used to generate the matrix input"
            )

            mode_map = {
                "Random": "random",
                "Guided / Edge-case": "guided",
                "Evolutionary": "evolution",
                "User-defined": "user"
            }

            mode = mode_map[mode_input]

            current_params.update({
                "rows_A": rows_A,
                "cols_A": cols_A,
                "cols_B": cols_B,
                "n": n,
                "mode": mode
            })

        # Divider + Preview
        st.divider()
        st.caption("Configured Parameters:")
        st.json(current_params)

        with st.expander("Advanced Settings"):

            col1, col2 = st.columns(2)
            with col1:
                use_shared_input = st.checkbox(
                    "Use shared input across algorithms",
                    value=False,
                    help="Reuses the same generated array when comparing multiple algorithms."
                )

                persist_input = st.checkbox(
                    "Persist generated input between runs",
                    value=True,
                    help="Prevents auto-regeneration when parameters change."
                )

                show_raw_ast = st.checkbox(
                    "Show raw AST counters payload",
                    value=False
                )

            with col2:
                random_seed = st.number_input(
                    "Random Seed (0 = None)",
                    min_value=0,
                    value=0,
                    help="Set a fixed seed for reproducibility."
                )

                disable_history = st.checkbox(
                    "Disable history recording",
                    value=False
                )

            # Graph-specific advanced options
            if group in GRAPH_GROUPS:
                st.divider()
                st.subheader("Graph Advanced")

                force_connected = st.checkbox(
                    "Force graph connectivity",
                    value=False
                )

                prevent_self_loops = st.checkbox(
                    "Prevent self-loops",
                    value=True
                )

                show_adj_matrix = st.checkbox(
                    "Display adjacency matrix after generation",
                    value=False
                )

                graph_params.update({
                    "force_connected": force_connected,
                    "prevent_self_loops": prevent_self_loops
                })

            # Store advanced state
            st.session_state.advanced_settings = {
                "use_shared_input": use_shared_input,
                "persist_input": persist_input,
                "show_raw_ast": show_raw_ast,
                "random_seed": random_seed,
                "disable_history": disable_history
            }



        if group in ARRAY_GROUPS:
            n_label = "Select max integer value" if group != ACTIVITY_ALGOS else "Select max time value"
            arr_label = "Select array length" if group != ACTIVITY_ALGOS else "Select number of activities"
            
            run_args = (selected_function, n, arr)
            current_params = {"algo": selected_function, "n": n, "arr": arr}

        elif group in MATRIX_GROUPS:
            run_args = (selected_function, n, rows_A, cols_A, cols_B)

        else:
            run_args = (selected_function,)
            current_params = {"algo": selected_function}

        user_has_run = st.session_state.future is not None or st.session_state.is_running

        # Load cached counters if no run yet
        if not user_has_run:
            cached = load_cache(cache_key)
            if cached is not None:
                st.session_state.counters = cached.get("counters", counters_template.copy())
                st.session_state.arr_length = cached.get("meta", {}).get("length")

    # --- User-defined function input ---
    user_func = None
    if group in ARRAY_GROUPS and mode == "user":
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


    # Execution Section
    with st.container(border=True):
        st.subheader("Execute")

        col1, col2, col3 = st.columns(3)

        with col1:
            # --- Generate Input Data ---
            random_seed = st.session_state.advanced_settings.get("random_seed", 0)
            if random_seed:
                apply_seed(random_seed)
            if st.button("Generate New Input Data", disabled=disabled):
                selected_function = run_args[0]
                base_array = None
                if mode == "evolution" and st.session_state.generated_input:
                    base_array = st.session_state.generated_input[0]

                match selected_function:
                    case name if name in SORTING_ALGOS:
                        st.session_state.generated_input = sorting_generation(
                            *run_args, mode=mode, base_array=base_array, user_func=user_func
                        )
                    case name if name in SEARCH_ALGOS:
                        st.session_state.generated_input = search_generation(
                            *run_args, mode=mode, base_array=base_array, user_func=user_func
                        )
                    case name if name in ACTIVITY_ALGOS:
                        st.session_state.generated_input = activity_generation(
                            *run_args, mode=mode, base_array=base_array, user_func=user_func
                        )
                    case name if name in GRAPH_ALGOS:
                        st.session_state.generated_input = graph_generation(
                            selected_function,
                            **graph_params
                        )
                    case name if name in MATRIX_ALGOS:
                        if None in (n, rows_A, cols_A, cols_B):
                            st.error("Matrix parameters cannot be None")
                        else:
                            st.session_state.generated_input = matrix_generation(
                                *run_args, mode=mode, base_array=base_array, user_func=user_func
                            )

                st.session_state.generated_params = current_params
                st.session_state.input_generated = True

        with col2:         
            # --- Run AST Analysis ---
            if st.button("Run AST Analysis", disabled=st.session_state.is_running):
                drop_cache(cache_key)
                st.session_state.is_running = True

                if st.session_state.generated_input is None:
                    if selected_function in GRAPH_ALGOS:
                        st.session_state.generated_input = graph_generation(
                            selected_function,
                            **graph_params
                        )

                future = st.session_state.executor.submit(
                    run_ast_analysis,
                    *run_args,
                    input_arr=st.session_state.generated_input if st.session_state.input_generated else None,
                    input_generated=st.session_state.input_generated,
                    input_mode = mode,
                    random_seed = st.session_state.advanced_settings.get("random_seed", 0)
                )

                st.session_state.future = future
                st.rerun()

        with col3:
            # --- Cancel Run ---
            if st.button("Cancel Run", disabled=not st.session_state.is_running):
                st.session_state.status = "Cancelling..."
                if st.session_state.future:
                    st.session_state.future.cancel()
                st.session_state.is_running = False
                st.session_state.future = None

    if st.session_state.generated_input is not None:
        st.caption("Generated input")

    # Run Status Section
    if st.session_state.is_running:
        st.warning("🟡 Analysis Running...")
        st_autorefresh(interval=2000, key="poll_ast")

    if st.session_state.future and st.session_state.future.done():
        payload = st.session_state.future.result()
        st.session_state.last_payload = payload

        st.session_state.arr_length = payload.get("meta", {}).get("length")
        st.session_state.counters = payload["counters"]
        if payload:
            saved_input = payload["input"]

            if group in GRAPH_GROUPS and isinstance(st.session_state.generated_input, dict):
                g = st.session_state.generated_input
                nodes = g.get("nodes", [])
                edges = g.get("edges", [])
                saved_input = {"nodes": nodes, "edges": edges}
            if not st.session_state.advanced_settings.get("disable_history", False):
                save_recent_run(
                    payload["meta"]["algorithm"],
                    n if "n" in locals() else None,
                    arr if "arr" in locals() else None,
                    saved_input,
                    payload["counters"],
                    mode=mode, 
                    history=payload.get("history", [])
                )
                save_cache(cache_key, payload, mode=mode)
        else:
            st.session_state.status = f"Function '{selected_function}' not found"
        st.session_state.future = None
        st.session_state.is_running = False
        st.success("🟢 Analysis Complete")#
    
    if (
    st.session_state.get("last_payload") is not None and st.session_state.advanced_settings.get("show_raw_ast", False)):
        st.subheader("Raw AST Payload")
        st.json(st.session_state.last_payload)

    if st.session_state.status:
        st.info(st.session_state.status)

    # --- Step Through History ---
    with st.container(border=True):
        st.subheader("Step-Through Execution")
    
        last_run = load_most_recent_run()

        if last_run:
            history = last_run.get("history", [])
            algorithm_name = last_run["algorithm"]

            helper_map = {"merge_sort": ["merge"]}
            source_code = extract_source_for_algorithm(
                algo_path,
                algorithm_name,
                helper_map=helper_map
            )

            can_visualize = any(snapshot.get("arrays") for snapshot in history)

            if not can_visualize:
                for snapshot in history:
                    if snapshot.get("nodes") is not None or snapshot.get("visited_edges") is not None:
                        can_visualize = True
                        break

            with st.expander("View Algorithm Execution Animation"):
                if can_visualize and source_code.strip():
                    visualize_algorithm(history, source_code, algorithm_name=algorithm_name)
                else:
                    st.info("Animation unavailable: input too large or graph too big.")
        else:
            st.info("Run an algorithm to enable step-through visualization.")

    # --- Operation Selection & Charts ---
    counters = st.session_state.counters
    arr_length = st.session_state.get("arr_length")
    if not isinstance(arr_length, (int, float)):
        arr_length = None

    if counters:
        with st.container(border=True):
            st.subheader("Execution Summary")

            col1, col2, col3 = st.columns(3)
            col1.metric("Input Size", arr_length)
            col2.metric("Total Operations", sum(counters.values()))
            col3.metric("Comparisons", counters.get("comparisons", 0))

    if counters:
        with st.container(border=True):
            st.subheader("Operation Breakdown")
            st.multiselect(
                "Select operations to include:",
                options=list(counters.keys()),
                default=list(counters.keys()),
                key="selected_operations",
            )

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
    # -----------------------------
    # Recent Runs Summary (Top Counters)
    # -----------------------------
    st.header("Recent Runs Summary (Top Counters)")

    recent_runs = load_recent_runs(limit=10)
    if recent_runs:
        rows = []
        edge_tables = []

        for run in recent_runs:
            counters = run.get("results", {})
            input_meta = run.get("input_meta", {})
            input_data = run.get("input", {})

            nodes_str = ""
            edges_list = []
            is_graph = False

            if isinstance(input_data, dict) and "nodes" in input_data and "edges" in input_data:
                nodes = input_data.get("nodes", [])
                edges_list = input_data.get("edges", [])
                nodes_str = ", ".join(nodes)
                is_graph = True
            elif isinstance(input_data, list):
                if len(input_data) == 2 and isinstance(input_data[0], dict):
                    graph_dict = input_data[0]
                    nodes = list(graph_dict.keys())
                    nodes_str = ", ".join(nodes)
                    for f, tos in graph_dict.items():
                        for t in tos:
                            edges_list.append([f, t])
                    is_graph = True
                else:
                    nodes_str = ""

            rows.append({
                "Algorithm": run.get("algorithm", "-"),
                "Mode": run.get("params", {}).get("mode", "-"),
                "Length": input_meta.get("length", "-"),
                "Comparisons": counters.get("comparisons", 0),
                "Assignments": counters.get("assignments", 0),
                "Loop Iter": counters.get("loop_iterations", 0),
                "Nodes": nodes_str if is_graph else ""
            })

            if is_graph and edges_list and len(nodes) <= 6 and len(edges_list) <= 8:
                edge_tables.append((run.get("algorithm", "-"), pd.DataFrame(edges_list, columns=["From", "To"]), True))
            else:
                edge_tables.append((run.get("algorithm", "-"), None, is_graph))

        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.background_gradient(cmap="Blues", subset=["Comparisons", "Assignments", "Loop Iter"]),
            use_container_width=True
        )

        for algo_name, edges_df, is_graph_flag in edge_tables:
            if edges_df is not None and not edges_df.empty:
                st.markdown(f"**Edges for {algo_name}:**")
                st.table(edges_df)
            elif edges_df is None and is_graph_flag:
                st.info(f"Edges for {algo_name} not displayed (graph too large)")

    else:
        st.info("No recent runs to display.")