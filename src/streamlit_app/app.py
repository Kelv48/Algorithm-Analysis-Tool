import pathlib
import ast, sys, operator
from concurrent.futures import ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh

import streamlit as st
import pandas as pd
import plotly.express as px
from random import randint

root = pathlib.Path.cwd()
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
algo_path = root/ "src" / "algorithm_analysis_tool" / "algorithms.py"
sys.path.insert(0, str(ast_visitor_path))

from algorithm_analysis_tool.ast_visitor import (
    ASTVisitor, count_arith, count_assign, count_call,
    count_compare, count_index, count_loop_iteration
)

# Streamlit page config
st.set_page_config(page_title="Operation Counter", page_icon="📊", layout="wide")
st.title("Algorithm Operation Analysis")
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

# Session state defaults
st.session_state.setdefault("counters", counters)
st.session_state.setdefault("status", "")
st.session_state.setdefault("executor", ThreadPoolExecutor(max_workers=1))
st.session_state.setdefault("future", None)
st.session_state.setdefault("is_running", False)

def run_ast_analysis(func_name, var):
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

    with open(algo_path, "r") as f:
        tree = ast.parse(f.read())

    function_map = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if func_name not in function_map:
        return None

    exec_globals = {
        "COUNTERS": counters,
        "count_arith": count_arith,
        "count_assign": count_assign,
        "count_call": count_call,
        "count_compare": count_compare,
        "count_index": count_index,
        "count_loop_iteration": count_loop_iteration,
        "operator": operator
    }

    exec(compile(tree, filename="<ast>", mode="exec"), exec_globals)

    visitor = ASTVisitor(counters)
    instrumented_node = visitor.visit(function_map[func_name])
    ast.fix_missing_locations(instrumented_node)
    code_obj = compile(ast.Module(body=[instrumented_node], type_ignores=[]),
                       filename="<ast>", mode="exec")
    exec(code_obj, exec_globals)

    n = int(var)
    arr = [randint(1, n) for _ in range(n)]
    exec_globals[func_name](arr)

    return counters

@st.cache_resource
def load_ast(algo_path):
    with open(algo_path, "r") as f:
        return ast.parse(f.read())
    
tree = load_ast(algo_path)
functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]

disabled = st.session_state.get("is_running", False)

selected_function = st.selectbox(
    "Select function to analyze:", functions, disabled=disabled, key="selected_function"
)
var = st.text_input(
    "Pick the range of values to cover", disabled=disabled, key="var_input"
)

if st.button("Run AST Analysis", disabled=st.session_state.future is not None):
    st.session_state.status = "Running analysis..."
    st.session_state.is_running = True
    st.session_state.future = st.session_state.executor.submit(run_ast_analysis, selected_function, var)
    st.rerun()

if st.session_state.get("is_running"):
    with st.spinner("Analyzing AST and executing instrumented code…"):
        st.caption("Parsing → instrumenting → executing")

if st.session_state.future:
    st_autorefresh(interval=2000, key="poll_ast")
    if st.session_state.future.done():
        result = st.session_state.future.result()
        if result:
            st.session_state.counters = result
            st.session_state.status = f"Analysis of '{selected_function}' completed ✅"
        else:
            st.session_state.status = f"Function '{selected_function}' not found"
        st.session_state.future = None
        st.session_state.is_running = False


if st.session_state.status:
    st.info(st.session_state.status)

counters = st.session_state.counters
selected_operations = st.multiselect(
    "Select operations to include:",
    options=list(counters.keys()),
    default=list(counters.keys())
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