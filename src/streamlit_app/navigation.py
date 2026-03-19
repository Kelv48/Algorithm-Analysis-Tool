import streamlit as st
from streamlit_option_menu import option_menu

def show_sidebar():
    with st.sidebar:
        selected = option_menu(
            menu_title="Navigation",
            menu_icon="cast",
            options=["Dashboard", "Single Execution", "Multi Execution", "Settings"],
            icons=['speedometer2', 'play-circle', "layers", 'gear'],
            default_index=["Dashboard", "Single Execution", "Multi Execution", "Settings"].index(st.session_state.get("page", "Dashboard")),
            orientation="vertical",
            styles={
                "container": {
                    "background-color": "inherit",
                    "padding": "0!important"
                },
            }
        )

    page_map = {
        "Dashboard": "app.py",
        "Single Execution": "pages/single_execution.py",
        "Multi Execution": "pages/multi_execution.py",
    }

    if st.session_state.get("page") != selected:
        st.session_state.page = selected
        st.switch_page(page_map[selected])