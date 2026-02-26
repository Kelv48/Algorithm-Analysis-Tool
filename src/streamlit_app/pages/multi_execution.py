import pathlib
import sys
import itertools
from itertools import product
from concurrent.futures import ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh

import streamlit as st
import pandas as pd
import plotly.express as px

from navigation import show_sidebar
from helpers import run_ast_analysis, graph_generation


# Paths
root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))

st.set_page_config(
    initial_sidebar_state="expanded",
    page_title="Multi Execution"
)


# Algorithm Groups
ALGO_GROUPS = {
    "Sorting": ["bubble_sort", "merge_sort", "insertion_sort", "quicksort"],
    "Searching": ["linear_search", "binary_search"],
    "Graph": ["dfs", "bfs"],
    "Scheduling": ["activity_selection"],
}


# Session
def get_executor():
    return ThreadPoolExecutor(max_workers=10)


st.session_state.setdefault("executor", get_executor())
st.session_state.setdefault("job_counter", itertools.count(1))
st.session_state.setdefault("jobs", {})
st.session_state.setdefault("job_queue", [])


show_sidebar()

st.title("Multi Execution Dashboard")

tab1, tab2 = st.tabs(["Experimental Modes", "Complexity Analysis"])

with tab1:
    # Job Configuration
    st.header("Job Configuration")

    group = st.selectbox("Algorithm Group", list(ALGO_GROUPS.keys()))
    selected_functions = st.multiselect("Algorithms", ALGO_GROUPS[group])


    # Array-Based Config
    if group in {"Sorting", "Searching", "Scheduling"}:

        n_values = st.multiselect(
            "Max Integer Values (n)",
            [50, 100, 200, 500, 1000],
            default=[100]
        )

        arr_lengths = st.multiselect(
            "Array Lengths",
            [50, 100, 200, 500],
            default=[100]
        )

        modes = st.multiselect(
            "Generation Modes",
            ["random", "guided", "evolution"],
            default=["random"]
        )


    # Graph Config
    else:
        st.subheader("Graph Configuration")

        num_nodes = st.multiselect(
            "Number of Nodes",
            [4, 6, 8, 10],
            default=[6]
        )

        num_edges = st.multiselect(
            "Number of Edges",
            [4, 8, 12, 16],
            default=[8]
        )

        graph_type = st.selectbox(
            "Graph Type",
            ["Random", "Connected", "Tree"]
        )

        directed = st.checkbox("Directed Graph", value=True)

        modes = ["graph"]


    # Build Job Queue
    if st.button("Add Jobs to Queue"):
        if not selected_functions:
            st.warning("Select at least one algorithm.")
        else:
            if group in {"Sorting", "Searching", "Scheduling"}:

                combinations = list(product(
                    selected_functions,
                    n_values,
                    arr_lengths,
                    modes
                ))

                for algo, n, arr_len, mode in combinations:
                    job_config = {
                        "type": "array",
                        "algorithm": algo,
                        "n": n,
                        "arr_length": arr_len,
                        "mode": mode
                    }

                    if job_config not in st.session_state.job_queue:
                        st.session_state.job_queue.append(job_config)

            else:
                combinations = list(product(
                    selected_functions,
                    num_nodes,
                    num_edges
                ))

                for algo, nodes, edges in combinations:

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
                        st.session_state.job_queue.append(job_config)

            st.success("Jobs added to queue.")

    st.divider()


    # Queue Display/Management
    st.header("Job Queue")

    if not st.session_state.job_queue:
        st.info("Queue is empty.")
    else:
        st.write(f"Queued Jobs: {len(st.session_state.job_queue)}")

        for idx, job in enumerate(st.session_state.job_queue):
            col1, col2 = st.columns([6, 1])

            with col1:
                if job["type"] == "array":
                    st.write(
                        f"{job['algorithm']} | "
                        f"n={job['n']} | "
                        f"len={job['arr_length']} | "
                        f"mode={job['mode']}"
                    )
                else:
                    gp = job["graph_params"]
                    st.write(
                        f"{job['algorithm']} | "
                        f"nodes={gp['num_nodes']} | "
                        f"edges={gp['num_edges']} | "
                        f"{gp['graph_type']} | "
                        f"{'Directed' if gp['directed'] else 'Undirected'}"
                    )

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

                        future = st.session_state.executor.submit(
                            run_ast_analysis,
                            job["algorithm"],
                            job["n"],
                            job["arr_length"],
                            input_generated=False,
                            input_mode=job["mode"],
                            job_id=job_id
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
                            job_id=job_id
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



    # Execution Dashboard
    st.header("Execution Dashboard")

    total_jobs = len(st.session_state.jobs)
    running_jobs = sum(1 for j in st.session_state.jobs.values()
                    if j["status"] == "running")
    finished_jobs = total_jobs - running_jobs

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jobs", total_jobs)
    col2.metric("Running", running_jobs)
    col3.metric("Finished", finished_jobs)

    st.divider()

    for job_id, job_data in sorted(st.session_state.jobs.items()):
        with st.expander(f"Job {job_id} — {job_data['status']}"):

            st.write("Algorithm:", job_data["algorithm"])

            if job_data["type"] == "array":
                st.write("n:", job_data["n"])
                st.write("Array Length:", job_data["arr_length"])
                st.write("Mode:", job_data["mode"])
            else:
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

            if job_data["status"] == "failed":
                st.error(job_data["result"]["error"])


    if running_jobs > 0:
        st_autorefresh(interval=2000, key="multi_refresh")
    else:
        st.session_state.pop("multi_refresh", None)

    st.divider()



    # System Controls
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