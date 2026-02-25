import streamlit as st
import pandas as pd
import pathlib
from helpers import load_recent_runs, load_most_recent_run, load_cache
from navigation import show_sidebar

st.set_page_config(
    page_title="Algorithm Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Algorithm Analysis Dashboard")

# -----------------------------
# Section 1: Last Run Summary
# -----------------------------
show_sidebar()

st.header("Last Run Summary")

last_run = load_most_recent_run()

if last_run:
    counters = last_run.get("results", {})

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Algorithm", last_run["algorithm"])
    col2.metric("Input Length", last_run["input_meta"].get("length", "-"))
    col3.metric("Comparisons", counters.get("comparisons", 0))
    col4.metric("Assignments", counters.get("assignments", 0))

else:
    st.info("No runs recorded yet. Run an algorithm to get started!")

# -----------------------------
# Section 2: Recent Activity
# -----------------------------
st.header("Recent Activity")

recent_runs = load_recent_runs(limit=5)

if recent_runs:
    rows = []
    for run in recent_runs:
        counters = run.get("results", {})

        rows.append({
            "Algorithm": run["algorithm"],
            "Mode": run.get("params", {}).get("mode", "-"),
            "Length": run.get("input_meta", {}).get("length", "-"),
            "Comparisons": counters.get("comparisons", 0),
            "Assignments": counters.get("assignments", 0),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

else:
    st.info("No recent activity yet.")

# -----------------------------
# Section 3: Cached Algorithms
# -----------------------------
st.header("Cached Algorithms")

CACHE_DIR = pathlib.Path("cache/algorithms")
cached_files = [f.stem for f in CACHE_DIR.glob("*.joblib")]

if cached_files:
    cols = st.columns(min(len(cached_files), 4))

    for i, algo in enumerate(cached_files[:4]):
        payload = load_cache(algo)

        if payload:
            counters = payload.get("counters", {})

            with cols[i]:
                st.subheader(algo)
                st.metric("Comparisons", counters.get("comparisons", 0))
                st.metric("Assignments", counters.get("assignments", 0))

else:
    st.info("No cached algorithms yet.")
