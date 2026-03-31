import streamlit as st

def init_session():
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "goal": None,
            "syllabus": [],
            "progress": {},
            "weak_topics": {}
        }

    if "messages" not in st.session_state:
        st.session_state.messages = []
        