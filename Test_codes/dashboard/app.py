import streamlit as st
from pages import instructor_dashboard, student_progress, settings

st.set_page_config(layout="wide", page_title="AI Tutoring Dashboard")

st.sidebar.title("AI Tutoring System")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Instructor Dashboard",
        "Student Progress",
        "Settings"
    ]
)

if menu == "Instructor Dashboard":
    instructor_dashboard.show()

elif menu == "Student Progress":
    student_progress.show()

elif menu == "Settings":
    settings.show()