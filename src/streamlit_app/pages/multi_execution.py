import streamlit as st
from navigation import show_sidebar

st.set_page_config(initial_sidebar_state="expanded")

show_sidebar()
st.title("Multi Execution Page")
st.write("This is a test page. Use the sidebar to navigate to other pages.")
page = st.session_state.get("page")
st.write(f"Current page: {page}")
