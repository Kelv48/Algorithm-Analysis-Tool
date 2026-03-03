import pathlib
import sys
import itertools
import random
from itertools import product
from concurrent.futures import ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh

import streamlit as st
import pandas as pd
import plotly.express as px

from navigation import show_sidebar
from helpers import run_ast_analysis, graph_generation, apply_seed, search_generation, sorting_generation, activity_generation


# Paths
root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))

st.set_page_config(
    initial_sidebar_state="expanded",
    page_title="Multi Execution"
)


# Algorithm Groups
from algorithm_analysis_tool.config import ALGO_GROUPS, ARRAY_GROUPS, GRAPH_GROUPS, MATRIX_GROUPS


# Session
def get_executor():
    return ThreadPoolExecutor(max_workers=10)


st.session_state.setdefault("executor", get_executor())
st.session_state.setdefault("job_counter", itertools.count(1))
st.session_state.setdefault("jobs", {})
st.session_state.setdefault("job_queue", [])
st.session_state.setdefault("shared_array", None)


show_sidebar()

st.title("Multi Execution Dashboard")

tab1, tab2 = st.tabs(["Experimental Modes", "Complexity Analysis"])

with tab1:
    # Job Configuration
    with st.container(border=True):
        st.header("Configure Jobs")

        group = st.selectbox("Algorithm Group", list(ALGO_GROUPS.keys()))
        selected_functions = st.multiselect("Algorithms", ALGO_GROUPS[group])


        # Array-Based Config
        if group in ARRAY_GROUPS:
            st.subheader("Array Configuration")
            col1, col2 = st.columns(2)
            with col1:
                n_values = st.multiselect("Max Integer Values (n)", [50, 100, 200, 500, 1000], default=[100])
                arr_lengths = st.multiselect("Array Lengths", [50, 100, 200, 500], default=[100])
            with col2:
                modes = st.multiselect("Generation Modes", ["random", "guided", "evolution"], default=["random"])
        elif group in MATRIX_GROUPS:
            st.subheader("Matrix Configuration")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                rows_A_values = st.multiselect("Rows of Matrix A", [2, 3, 4, 5], default=[2])
            with col2:
                cols_A_values = st.multiselect("Columns of Matrix A", [2, 3, 4, 5], default=[3])
            with col3:
                cols_B_values = st.multiselect("Columns of Matrix B", [2, 3, 4, 5], default=[2])
            with col4:
                n_values = st.multiselect("Max Integer Value", [10, 50, 100, 200], default=[100])
            modes = st.multiselect("Generation Modes", ["random"], default=["random"])
        # Graph Config
        else:
            st.subheader("Graph Configuration")
            col1, col2 = st.columns(2)
            with col1:
                num_nodes = st.multiselect("Number of Nodes", [4, 6, 8, 10], default=[6])
                num_edges = st.multiselect("Number of Edges", [4, 8, 12, 16], default=[8])
            with col2:
                graph_type = st.selectbox("Graph Type", ["Random", "Connected", "Tree"])
                directed = st.checkbox("Directed Graph", value=True)
            modes = ["graph"]

        with st.expander("Advanced Settings"):
            col1, col2 = st.columns(2)
            with col1:
                random_seed = st.number_input("Random Seed (0 = None)", min_value=0, value=0, help="Set fixed seed for reproducibility")
                max_workers = st.slider("Max Parallel Workers", 1, 20, 10)
            with col2:
                show_raw_payload = st.checkbox("Show Raw AST Payload in Results", value=False)
                auto_clear_finished = st.checkbox("Auto-clear finished jobs on reset", value=True)

            # Apply worker change safely
            if max_workers != st.session_state.executor._max_workers:
                st.session_state.executor.shutdown(wait=False)
                st.session_state.executor = ThreadPoolExecutor(max_workers=max_workers)

            st.session_state.advanced_settings = {
                "random_seed": random_seed,
                "show_raw_payload": show_raw_payload,
                "auto_clear_finished": auto_clear_finished
            }


        # Build Job Queue
        if st.button("Add Jobs to Queue"):
            if not selected_functions:
                st.warning("Select at least one algorithm.")
            else:
                new_jobs = []
                random_seed = st.session_state.advanced_settings.get("random_seed", 0)
                if random_seed:
                    apply_seed(random_seed)
                if group in ARRAY_GROUPS:
                    unique_inputs = []
                    for n, arr_len, mode in product(n_values, arr_lengths, modes):
                        if group == "Sorting":
                            arr = sorting_generation(selected_functions[0], n, arr_len, mode=mode)[0]
                        elif group == "Searching":
                            arr, target = search_generation(selected_functions[0], n, arr_len, mode=mode)
                        elif group == "Scheduling":
                            arr = activity_generation(selected_functions[0], n, arr_len, mode=mode)[0]

                        unique_inputs.append({
                            "n": n,
                            "arr_length": arr_len,
                            "mode": mode,
                            "input_array": arr if group != "Searching" else (arr, target)
                        })

                    for algo in selected_functions:
                        for inp in unique_inputs:
                            job_config = {
                                "type": "array",
                                "algorithm": algo,
                                "n": inp["n"],
                                "arr_length": inp["arr_length"],
                                "mode": inp["mode"],
                                "input_array": inp["input_array"]
                            }
                            if job_config not in st.session_state.job_queue:
                                new_jobs.append(job_config)
                elif group in MATRIX_GROUPS:
                    unique_inputs = []
                    for rows_A, cols_A, cols_B, n, mode in product(rows_A_values, cols_A_values, cols_B_values, n_values, modes):
                        A = [[random.randint(0, n) for _ in range(cols_A)] for _ in range(rows_A)]
                        B = [[random.randint(0, n) for _ in range(cols_B)] for _ in range(cols_A)]  # cols_A = rows_B

                        unique_inputs.append({
                            "rows_A": rows_A,
                            "cols_A": cols_A,
                            "cols_B": cols_B,
                            "n": n,
                            "mode": mode,
                            "matrices": (A, B)
                        })

                    for algo in selected_functions:
                        for inp in unique_inputs:
                            job_config = {
                                "type": "matrix",
                                "algorithm": algo,
                                "rows_A": inp["rows_A"],
                                "cols_A": inp["cols_A"],
                                "cols_B": inp["cols_B"],
                                "n": inp["n"],
                                "mode": inp["mode"],
                                "matrices": inp["matrices"]
                            }
                            if job_config not in st.session_state.job_queue:
                                new_jobs.append(job_config)
                else:
                    # --- Graph generation directly per job ---
                    for algo, nodes, edges in product(selected_functions, num_nodes, num_edges):
                        graph_params = {
                            "num_nodes": nodes,
                            "num_edges": edges,
                            "graph_type": graph_type,
                            "directed": directed
                        }
                        job_config = {
                            "type": "graph",
                            "algorithm": algo,
                            "graph_params": graph_params
                        }
                        if job_config not in st.session_state.job_queue:
                            new_jobs.append(job_config)

                # Add all new jobs to queue
                st.session_state.job_queue.extend(new_jobs)
                st.success(f"Added {len(new_jobs)} jobs to the queue.")

    # Queue Display/Management
    st.header("Job Queue")
    if not st.session_state.job_queue:
        st.info("Queue is empty.")
    else:
        st.metric("Queued Jobs", len(st.session_state.job_queue))
        max_display = st.slider("Max jobs to show in queue", 5, 500, 10)

        display_queue = st.session_state.job_queue[:max_display]
        for idx, job in enumerate(display_queue):
            col1, col2 = st.columns([6, 1])

            with col1:
                if job["type"] == "array":
                    st.write(
                        f"{job['algorithm']} | "
                        f"n={job['n']} | "
                        f"len={job['arr_length']} | "
                        f"mode={job['mode']}"
                    )
                elif job["type"] == "graph":
                    gp = job["graph_params"]
                    st.write(
                        f"{job['algorithm']} | "
                        f"nodes={gp['num_nodes']} | "
                        f"edges={gp['num_edges']} | "
                        f"{gp['graph_type']} | "
                        f"{'Directed' if gp['directed'] else 'Undirected'}"
                    )
                elif job["type"] == "matrix":
                    st.write(
                        f"{job['algorithm']} | {job['rows_A']}x{job['cols_A']} * {job['cols_A']}x{job['cols_B']} | mode={job['mode']}")

            with col2:
                if st.button("Drop", key=f"remove_{idx}"):
                    st.session_state.job_queue.pop(idx)
                    st.rerun()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Submit Queue"):
                for job in st.session_state.job_queue:
                    job_id = next(st.session_state.job_counter)

                    if job["type"] == "array":
                        input_arr = job.get("input_array")
                        future = st.session_state.executor.submit(
                            run_ast_analysis,
                            job["algorithm"],
                            input_arr=input_arr,
                            input_generated=True,
                            input_mode=job["mode"],
                            job_id=job_id,
                            random_seed=st.session_state.advanced_settings.get("random_seed", 0)
                        )
                    elif job["type"] == "matrix":
                        A, B = job["matrices"]
                        future = st.session_state.executor.submit(
                            run_ast_analysis,
                            job["algorithm"],
                            input_arr=(A, B),   # pass matrices as input
                            input_generated=True,
                            input_mode="matrix",
                            job_id=job_id,
                            random_seed=st.session_state.advanced_settings.get("random_seed", 0)
                        )

                    else: 
                        generated_graph = graph_generation(
                            job["algorithm"],
                            **job["graph_params"]
                        )
                        future = st.session_state.executor.submit(
                            run_ast_analysis,
                            job["algorithm"],
                            input_arr=generated_graph,
                            input_generated=True,
                            input_mode="graph",
                            job_id=job_id,
                            random_seed=st.session_state.advanced_settings.get("random_seed", 0)
                        )

                    st.session_state.jobs[job_id] = {
                        "future": future,
                        "status": "running",
                        "result": None,
                        **job
                    }

                submitted = len(st.session_state.job_queue)
                st.session_state.job_queue = []
                st.success(f"Submitted {submitted} jobs.")

        with col2:
            if st.button("Clear Queue"):
                st.session_state.job_queue = []
                st.success("Queue cleared.")

    st.divider()


    # Update Job Statuses
    for job_id, job_data in st.session_state.jobs.items():
        if job_data["status"] == "running":
            future = job_data["future"]

            if future.done():
                try:
                    result = future.result()
                    job_data["status"] = "completed"
                    job_data["result"] = result
                except Exception as e:
                    job_data["status"] = "failed"
                    job_data["result"] = {"error": str(e)}


    def collect_completed_results():
        rows = []

        for job_id, job_data in st.session_state.jobs.items():
            if job_data["status"] == "completed":
                counters = job_data["result"]["counters"]
                total_ops = sum(counters.values())

                row = {
                    "job_id": job_id,
                    "algorithm": job_data["algorithm"],
                    "type": job_data["type"],
                    "total_operations": total_ops
                }

                if job_data["type"] == "array":
                    row["n"] = job_data["n"]
                    row["arr_length"] = job_data["arr_length"]
                    row["mode"] = job_data["mode"]
                elif job_data["type"] == "matrix":
                    row["rows_A"] = job_data["rows_A"]
                    row["cols_A"] = job_data["cols_A"]
                    row["cols_B"] = job_data["cols_B"]
                    row["mode"] = job_data["mode"]
                elif job_data["type"] == "graph":
                    gp = job_data["graph_params"]
                    row["nodes"] = gp["num_nodes"]
                    row["edges"] = gp["num_edges"]

                rows.append(row)

        if rows:
            return pd.DataFrame(rows)

        return pd.DataFrame()


    # Execution Dashboard
    st.header("Execution Dashboard")

    total_jobs = len(st.session_state.jobs)
    running_jobs = sum(1 for j in st.session_state.jobs.values()
                    if j["status"] == "running")
    finished_jobs = total_jobs - running_jobs

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", total_jobs)
    col2.metric("Running", running_jobs)
    col3.metric("Completed", finished_jobs)

    st.divider()

    max_display_jobs = st.slider("Max jobs to show on the dashboard", 5, 500, 10)
    display_jobs = list(sorted(st.session_state.jobs.items()))[:max_display_jobs]
    for job_id, job_data in display_jobs:
        with st.expander(f"Job {job_id} — {job_data['status']}"):

            st.write("Algorithm:", job_data["algorithm"])

            if job_data["type"] == "array":
                st.write("n:", job_data["n"])
                st.write("Array Length:", job_data["arr_length"])
                st.write("Mode:", job_data["mode"])
            elif job_data["type"] == "matrix":
                st.write("Rows A:", job_data["rows_A"])
                st.write("Cols A:", job_data["cols_A"])
                st.write("Cols B:", job_data["cols_B"])
                st.write("Max Value:", job_data["n"])
                st.write("Mode:", job_data["mode"])
            elif job_data["type"] == "graph":
                gp = job_data["graph_params"]
                st.write("Nodes:", gp["num_nodes"])
                st.write("Edges:", gp["num_edges"])
                st.write("Graph Type:", gp["graph_type"])
                st.write("Directed:", gp["directed"])

            if job_data["status"] == "running":
                if st.button(f"Cancel Job {job_id}", key=f"cancel_{job_id}"):
                    if job_data["future"].cancel():
                        job_data["status"] = "cancelled"
                    else:
                        st.warning("Could not cancel (already running).")

            if job_data["status"] == "completed":
                counters = job_data["result"]["counters"]

                df = pd.DataFrame({
                    "Operation": list(counters.keys()),
                    "Count": list(counters.values())
                })

                fig = px.bar(
                    df,
                    x="Operation",
                    y="Count",
                    text="Count",
                    title=f"Operation Distribution (Job {job_id})"
                )
                fig.update_traces(textposition="outside")

                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df.set_index("Operation"))

                if st.session_state.advanced_settings.get("show_raw_payload", False):
                    st.subheader("Raw Payload")
                    st.json(job_data["result"])

            if job_data["status"] == "failed":
                st.error(job_data["result"]["error"])


    if running_jobs > 0:
        st_autorefresh(interval=2000, key="multi_refresh")
    else:
        st.session_state.pop("multi_refresh", None)

    st.divider()
    st.header("Comparative Analysis")

    results = collect_completed_results()
    if results.empty:
        st.info("No completed jobs to compare yet")
    else:
        st.dataframe(results)
        if "n" in results.columns:
            st.subheader("Algorithm Operations Overview")

            col1, col2 = st.columns(2)

            # --- Operations vs Input Size (n) ---
            with col1:
                fig_n = px.scatter(results.sort_values("n"), x="n", y="total_operations", color="algorithm", symbol="algorithm", size_max=15, hover_data=["arr_length", "mode"], title="Operations vs Input Size (n)")
                # Trend lines per algorithm
                for algo in results["algorithm"].unique():
                    df_algo = results[results["algorithm"] == algo].sort_values("n")
                    fig_n.add_scatter(x=df_algo["n"], y=df_algo["total_operations"], mode="lines", name=f"{algo} trend", line=dict(dash="dash"))
                st.plotly_chart(fig_n)

            # --- Operations vs Array Length ---
            if "arr_length" in results.columns:
                with col2:
                    fig_arr = px.scatter(results.sort_values("arr_length"), x="arr_length", y="total_operations", color="algorithm", symbol="algorithm", size_max=15, hover_data=["n", "mode"], title="Operations vs Array Length")
                    # Trend lines per algorithm
                    for algo in results["algorithm"].unique():
                        df_algo = results[results["algorithm"] == algo].sort_values("arr_length")
                        fig_arr.add_scatter( x=df_algo["arr_length"], y=df_algo["total_operations"], mode="lines", name=f"{algo} trend", line=dict(dash="dash"))
                    st.plotly_chart(fig_arr)

            log_scale = st.checkbox("Use Log Scale for Y-Axis", value=False)
            st.subheader("Growth Trends")

            col1, col2 = st.columns(2)

            # --- Trend vs Input Size (n) ---
            with col1:
                log_scale_n = st.checkbox("Log Scale for n Trend", value=False, key="log_n")
                fig_trend_n = px.line(results.sort_values("n"), x="n", y="total_operations", color="algorithm", markers=True, hover_data=["arr_length", "mode"], title="Growth Trend vs Input Size (n)")
                fig_trend_n.update_yaxes(type="log" if log_scale_n else "linear")
                st.plotly_chart(fig_trend_n, use_container_width=True)

            # --- Trend vs Array Length ---
            with col2:
                if "arr_length" in results.columns:
                    log_scale_arr = st.checkbox("Log Scale for Array Length Trend", value=False, key="log_arr")
                    fig_trend_arr = px.line(results.sort_values("arr_length"), x="arr_length", y="total_operations", color="algorithm", markers=True, hover_data=["n", "mode"], title="Growth Trend vs Array Length")
                    fig_trend_arr.update_yaxes(type="log" if log_scale_arr else "linear")
                    st.plotly_chart(fig_trend_arr, use_container_width=True)

            st.subheader("Operations Heatmap")
            df_heat = results.pivot_table(index="algorithm", columns="n", values="total_operations")
            fig_heat = px.imshow(df_heat, text_auto=True, color_continuous_scale='Viridis', title="Operation Heatmap")
            st.plotly_chart(fig_heat, use_container_width=True)

        st.subheader("Aggregated Summary")
        summary_df = results.groupby("algorithm")["total_operations"].mean().reset_index().rename(columns={"total_operations": "avg_operations"})
        st.dataframe(summary_df)

    # System Controls
    st.subheader("System Controls")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Clear Finished Jobs",
                    disabled=(finished_jobs == 0)):
            st.session_state.jobs = {
                job_id: job_data
                for job_id, job_data in st.session_state.jobs.items()
                if job_data["status"] == "running"
            }

            if not st.session_state.jobs:
                st.session_state.job_counter = itertools.count(1)

            st.success("Finished jobs cleared.")

    with col2:
        if st.button("Reset All",
                    disabled=(total_jobs == 0)):
            st.session_state.jobs = {}
            st.session_state.job_queue = []
            st.session_state.job_counter = itertools.count(1)
            st.success("System reset.")



with tab2:
    st.header("Complexity Analysis")

    st.info("This code is not implemented")