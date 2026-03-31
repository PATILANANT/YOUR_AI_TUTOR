import streamlit as st
import requests

st.title("🔐 Login / Register")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Register"):
    res = requests.post(
        "http://127.0.0.1:8000/register",
        json={"username": username, "password": password}
    )
    st.success(res.json().get("message"))

if st.button("Login"):
    res = requests.post(
        "http://127.0.0.1:8000/login",
        json={"username": username, "password": password}
    )

    if res.status_code == 200:
        user_id = res.json()["user_id"]
        st.session_state.user_id = user_id

        # Load profile from backend
        profile_res = requests.get(
            f"http://127.0.0.1:8000/load_profile/{user_id}"
        )

        st.session_state.profile = profile_res.json()["profile"]
        st.success("Logged in successfully ✅")
    else:
        st.error("Login failed ❌")