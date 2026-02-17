import streamlit as st
from streamlit_option_menu import option_menu

def show_sidebar():
    with st.sidebar:
        selected = option_menu(
            None,
            ["Home", "Multi Execution", "None", "None"],
            icons=['house', 'cloud-upload', "list-task", 'gear'],
            default_index=["Home", "Multi Execution", "None", "None"].index(st.session_state.get("page", "Home")),
            orientation="vertical",
            styles={
                "container": {
                    "background-color": "inherit",
                    "padding": "0!important"
                },
            }
        )

    page_map = {
        "Home": "app.py",
        "Multi Execution": "pages/multi_execution.py",
        "None": "pages/Tasks.py",
        "None": "pages/Settings.py",
    }

    if st.session_state.get("page") != selected:
        st.session_state.page = selected
        st.switch_page(page_map[selected])