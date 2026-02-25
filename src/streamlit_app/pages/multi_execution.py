import pathlib
import sys
import itertools
from concurrent.futures import ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh

import streamlit as st
import pandas as pd
import plotly.express as px

from navigation import show_sidebar
from helpers import (
    run_ast_analysis,
    sorting_generation,
    search_generation,
    graph_generation,
    activity_generation,
)

root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root / "src" / "algorithm_analysis_tool" / "algorithms.py"
sys.path.insert(0, str(ast_visitor_path))

st.set_page_config(initial_sidebar_state="expanded", page_title="Multi Execution")

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

show_sidebar()

def get_executor():
    return ThreadPoolExecutor(max_workers=4)

st.session_state.setdefault("executor", get_executor())
st.session_state.setdefault("job_counter", itertools.count(1))
st.session_state.setdefault("jobs", {})

st.title("Multi Execution Page")

# Sidebar Controls
with st.sidebar:
    st.header("Configuration")
    group = st.selectbox("Algorithm Group", list(ALGO_GROUPS.keys()))
    selected_function = st.selectbox("Algorithm", ALGO_GROUPS[group])

    mode = "random"
    if group in {"Sorting", "Searching", "Scheduling"}:
        n = st.slider("Max Integer Value", 1, 1000, 100)
        arr = st.slider("Array Length", 1, 1000, 100)

        mode = st.selectbox(
            "Input Mode",
            ["random", "guided", "evolution"]
        )

        run_args = (selected_function, n, arr)
    else:
        graph_params = {}
        st.divider()
        st.subheader("Graph Configuration")

        num_nodes = st.slider("Number of nodes", 2, 26, 6)

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
        current_params = {"algo": selected_function}


# Job Submission

col1, col2 = st.columns(2)

with col1:
    if st.button("Submit Job"):
        job_id = next(st.session_state.job_counter)

        if group == "Graph":
            generated_input = graph_generation(selected_function, **graph_params)
        else:
            generated_input = None

        future = st.session_state.executor.submit(
            run_ast_analysis,
            *run_args,
            input_arr=generated_input,
            input_generated=bool(generated_input),
            input_mode=mode,
            job_id=job_id
        )

        st.session_state.jobs[job_id] = {
            "future": future,
            "status": "running",
            "algorithm": selected_function,
            "mode": mode,
            "result": None
        }

        st.success(f"Submitted Job {job_id}")


with col2:
    if st.button("Submit 5 Jobs"):
        for _ in range(5):
            job_id = next(st.session_state.job_counter)

            future = st.session_state.executor.submit(
                run_ast_analysis,
                *run_args,
                input_generated=False,
                input_mode=mode,
                job_id=job_id
            )

            st.session_state.jobs[job_id] = {
                "future": future,
                "status": "running",
                "algorithm": selected_function,
                "mode": mode,
                "result": None
            }

        st.success("Submitted 5 jobs")

st.divider()



# Update Job Status
running = 0
completed = 0
failed = 0

for job_id, job_data in st.session_state.jobs.items():
    future = job_data["future"]

    if job_data["status"] == "running":
        if future.done():
            try:
                payload = future.result()
                job_data["status"] = "completed"
                job_data["result"] = payload
            except Exception as e:
                job_data["status"] = "failed"
                job_data["result"] = str(e)

    if job_data["status"] == "running":
        running += 1
    elif job_data["status"] == "completed":
        completed += 1
    elif job_data["status"] == "failed":
        failed += 1

st.subheader("System Status")
st.write(f"Running: {running}")
st.write(f"Completed: {completed}")
st.write(f"Failed: {failed}")
st.write(f"Total Jobs: {len(st.session_state.jobs)}")

st.divider()


# Display Jobs
for job_id, job_data in sorted(st.session_state.jobs.items()):
    with st.expander(f"Job {job_id} — {job_data['status']}"):
        st.write("Algorithm:", job_data["algorithm"])
        st.write("Mode:", job_data["mode"])
        st.write("Status:", job_data["status"])

        if job_data["status"] == "running":
            if st.button(f"Cancel Job {job_id}", key=f"cancel_{job_id}"):
                if job_data["future"].cancel():
                    job_data["status"] = "cancelled"

        if job_data["status"] == "completed":
            counters = job_data["result"]["counters"]
            arr_length = job_data["result"]["meta"]["length"]

            df = pd.DataFrame({
                "Operation": list(counters.keys()),
                "Count": list(counters.values())
            })

            fig = px.bar(df, x="Operation", y="Count", text="Count",
                         title=f"Operation Distribution (Job {job_id})")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df.set_index("Operation"))


if running > 0:
    st_autorefresh(interval=2000, key="multi_refresh")