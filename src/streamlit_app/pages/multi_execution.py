import streamlit as st
from navigation import show_sidebar

st.set_page_config(initial_sidebar_state="expanded")

show_sidebar()
st.title("Multi Execution Page")
st.write("This is a test page. Use the sidebar to navigate to other pages.")
page = st.session_state.get("page")
st.write(f"Current page: {page}")

# This page will allow a user to run a single algorithm up to 10 times with either the same of different inputs and then show
# differences between runs, the average accross runs, etc. This will be useful for showing how the same algorithm can perform differently on different 
# inputs and also how it can perform differently on the same input due to factors like caching, CPU load, etc. 
# It will also be useful for showing how the performance of an algorithm can vary across different runs and how it can be affected by factors 
# like garbage collection, etc.

# Akso can be used to calculate the complexity of the algorithm by running it on different input sizes and then showing how the performance 
# changes with input size..
