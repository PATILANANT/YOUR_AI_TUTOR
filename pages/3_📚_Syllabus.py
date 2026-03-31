import streamlit as st
from utils.session_init import init_session
init_session()



st.title("📚 Syllabus Manager")

# if "user_id" not in st.session_state:
#     st.warning("Please login first 🔐")
#     st.stop()

if "profile" not in st.session_state:
    st.session_state.profile = {
        "goal": None,
        "syllabus": [],
        "progress": {},
        "weak_topics": []
    }

syllabus_input = st.text_area("Enter topics (comma separated)")

if st.button("Save Syllabus"):
    topics = [t.strip() for t in syllabus_input.split(",")]
    st.session_state.profile["syllabus"] = topics
    st.success("Syllabus Saved ✅")

st.write("Current Syllabus:", st.session_state.profile["syllabus"])