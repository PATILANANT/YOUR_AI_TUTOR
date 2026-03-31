import streamlit as st
from smart_engine import analyze_performance
from utils.session_init import init_session
init_session()

st.title("📈 Performance Analysis")

if "user_id" not in st.session_state:
    st.warning("Please login first 🔐")
    st.stop()

if "profile" not in st.session_state:
    st.warning("No data available.")
else:
    progress = st.session_state.profile["progress"]

    if progress:
        scores = list(progress.values())

        st.metric("Total Topics Covered", len(scores))
        st.metric("Average Score", sum(scores)/len(scores))

        st.bar_chart(scores)
    else:
        st.info("No performance data yet.")



profile = st.session_state.profile
analysis = analyze_performance(profile)

if "avg_score" in analysis:
    st.metric("Average Score", f"{analysis['avg_score']:.2f}")
    st.metric("Topics Covered", analysis["total_topics"])

    st.bar_chart(list(profile["progress"].values()))