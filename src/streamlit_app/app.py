import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Algorithm Operation Analysis")

st.header("Bubble Sort Analysis")
st.text("Using the arr [2, 5, 3, 1, 4]")
# Your results
results = {
    "assignments": 15,
    "indexing": 30,
    "function_calls": 6,
    "comparisons": 10,
    "arithmetic": 28,
    "loops": 14
}

# Convert to DataFrame
df = pd.DataFrame({
    "Operation": results.keys(),
    "Count": results.values()
})

# Create bar chart
fig = px.bar(
    df,
    x="Operation",
    y="Count",
    text="Count",
    title="Operation Count Distribution"
)

fig.update_traces(textposition="outside")

st.plotly_chart(fig, use_container_width=True)

# Show numeric table
st.subheader("Raw Data")
st.dataframe(df)

fig = px.pie(
    df,
    names="Operation",
    values="Count",
    title="Operation Distribution (%)"
)

st.plotly_chart(fig)

n = 5
df["Per Element"] = df["Count"] / n

st.dataframe(df)
