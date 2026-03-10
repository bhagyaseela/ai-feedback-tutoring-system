import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

def show():

    st.title("Instructor Dashboard")

    data = load_data()

    courses = data["course"].unique()
    selected_course = st.selectbox("Select Course", courses)

    course_data = data[data["course"] == selected_course]

    assignments = course_data["assignment"].unique()
    selected_assignment = st.selectbox("Select Assignment", assignments)

    assignment_data = course_data[course_data["assignment"] == selected_assignment]

    total_submissions = assignment_data["student"].nunique()
    avg_grade = assignment_data["score"].mean()
    plagiarism_flags = len(assignment_data[assignment_data["plagiarism"] > 0.15])

    col1, col2, col3 = st.columns(3)

    col1.metric("Students Submitted", total_submissions)
    col2.metric("Average Score", round(avg_grade,2))
    col3.metric("Plagiarism Flags", plagiarism_flags)

    st.divider()

    st.subheader("Question Performance")

    q_scores = assignment_data.groupby("question")["score"].mean().reset_index()

    fig = px.bar(
        q_scores,
        x="question",
        y="score",
        title="Average Score per Question"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Score Distribution")

    fig2 = px.histogram(
        assignment_data,
        x="score",
        nbins=10
    )

    st.plotly_chart(fig2, use_container_width=True)