import streamlit as st
from smart_engine import analyze_performance

from utils.session_init import init_session
init_session()

st.title("📊 Student Dashboard")

if "profile" not in st.session_state:
    st.warning("No data yet. Start learning first.")
else:
    profile = st.session_state.profile

    st.write("🎯 Goal:", profile["goal"])
    st.write("📚 Syllabus:", profile["syllabus"])
    st.write("📈 Progress:", profile["progress"])
    st.write("⚠️ Weak Topics:", profile["weak_topics"])


# from smart_engine import analyze_performance

profile = st.session_state.profile
analysis = analyze_performance(profile)

st.markdown("## 🧠 Insights")

if "avg_score" in analysis:
    st.write(f"📊 Average Score: {analysis['avg_score']:.2f}")
    st.write(f"⚠️ Weak Topics: {analysis['weak_topics']}")
    st.write(f"📘 Topics Covered: {analysis['total_topics']}")