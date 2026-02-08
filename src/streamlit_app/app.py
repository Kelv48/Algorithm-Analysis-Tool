import pathlib
import ast, sys, operator
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
import pandas as pd
import plotly.express as px
from random import randint

root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = ast_visitor_path / "algorithms.py"
sys.path.insert(0, str(ast_visitor_path))

from algorithm_analysis_tool.ast_visitor import (
    ASTVisitor, count_arith, count_assign, count_call,
    count_compare, count_index, COUNTERS, count_loop_iteration
)

# Streamlit page config
st.set_page_config(page_title="Operation Counter", page_icon="📊", layout="wide")
st.title("Algorithm Operation Analysis")

# Session state defaults
st.session_state.setdefault("counters", COUNTERS.copy())
st.session_state.setdefault("status", "")
st.session_state.setdefault("executor", ThreadPoolExecutor(max_workers=1))
st.session_state.setdefault("future", None)

def run_ast_analysis(func_name):
    for key in COUNTERS:
        COUNTERS[key] = 0

    with open(algo_path, "r") as f:
        tree = ast.parse(f.read())

    function_map = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if func_name not in function_map:
        return None

    exec_globals = {
        "COUNTERS": COUNTERS,
        "count_arith": count_arith,
        "count_assign": count_assign,
        "count_call": count_call,
        "count_compare": count_compare,
        "count_index": count_index,
        "count_loop_iteration": count_loop_iteration,
        "operator": operator
    }

    exec(compile(tree, filename="<ast>", mode="exec"), exec_globals)

    visitor = ASTVisitor()
    instrumented_node = visitor.visit(function_map[func_name])
    ast.fix_missing_locations(instrumented_node)
    code_obj = compile(ast.Module(body=[instrumented_node], type_ignores=[]),
                       filename="<ast>", mode="exec")
    exec(code_obj, exec_globals)

    arr = [randint(1, 10) for _ in range(10)]
    exec_globals[func_name](arr)

    return COUNTERS.copy()

with open(algo_path, "r") as f:
    tree = ast.parse(f.read())
functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]

selected_function = st.selectbox("Select function to analyze:", functions)

if st.button("Run AST Analysis"):
    st.session_state.status = "Running analysis..."
    st.session_state.future = st.session_state.executor.submit(run_ast_analysis, selected_function)

if st.session_state.future:
    with st.spinner("Running AST analysis... ⏳"):
        if st.session_state.future.done():
            result = st.session_state.future.result()
            if result:
                st.session_state.counters = result
                st.session_state.status = f"Analysis of '{selected_function}' completed ✅"
            else:
                st.session_state.status = f"Function '{selected_function}' not found"
            st.session_state.future = None  # clear future
        else:
            import time
            time.sleep(2)
            st.rerun()


if st.session_state.status:
    st.info(st.session_state.status)

selected_operations = st.multiselect(
    "Select operations to include:",
    options=list(COUNTERS.keys()),
    default=list(COUNTERS.keys())
)


# Helper: build charts & table
def display_charts(counters_dict):
    df = pd.DataFrame({
        "Operation": [op for op in counters_dict if op in selected_operations],
        "Count": [cnt for op, cnt in counters_dict.items() if op in selected_operations]
    })

    # Bar chart
    fig = px.bar(df, x="Operation", y="Count", text="Count", title="Operation Count Distribution")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # Pie chart
    fig2 = px.pie(df, names="Operation", values="Count", title="Operation Distribution (%)")
    st.plotly_chart(fig2, use_container_width=True)

    # Per-element
    df["Per Element"] = df["Count"] / 10
    st.subheader("Raw Data")
    st.dataframe(df)

# Display charts
display_charts(st.session_state.counters)