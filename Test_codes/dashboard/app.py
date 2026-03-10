import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title="AI Tutoring Dashboard",
    layout="wide",
    page_icon="📊"
)

# Load Data
data = pd.read_csv("sample_data.csv")

# Sidebar
st.sidebar.title("📚 Dashboard Menu")
page = st.sidebar.radio(
    "Navigate",
    ["Instructor Dashboard", "Student Progress"]
)

# Metrics
total_submissions = len(data)
avg_grade = round(data["grade"].mean(), 2)
graded = len(data)
plagiarism_flags = len(data[data["plagiarism"] > 0.15])
waiting_deadline = 5

concept_cols = [
    "concept_recursion",
    "concept_trees",
    "concept_graphs",
    "concept_dp"
]

concept_means = data[concept_cols].mean()
weak_concepts = concept_means.sort_values().head(2)

# Instructor Dashboard
if page == "Instructor Dashboard":

    st.title("🎓 Instructor Analytics Dashboard")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Submissions", total_submissions)
    col2.metric("Graded", graded)
    col3.metric("Waiting Deadline", waiting_deadline)
    col4.metric("Plagiarism Flags", plagiarism_flags)
    col5.metric("Average Grade", avg_grade)

    st.markdown("---")

    colA, colB = st.columns(2)

    # Grade Distribution
    fig = px.histogram(
        data,
        x="grade",
        nbins=10,
        title="Grade Distribution",
        color_discrete_sequence=["#636EFA"]
    )

    colA.plotly_chart(fig, use_container_width=True)

    # Plagiarism Scatter
    fig2 = px.scatter(
        data,
        x="grade",
        y="plagiarism",
        color="student",
        size="plagiarism",
        title="Plagiarism vs Grade"
    )

    colB.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    colC, colD = st.columns(2)

    # Concept Performance
    concept_df = concept_means.reset_index()
    concept_df.columns = ["Concept", "Score"]

    fig3 = px.bar(
        concept_df,
        x="Concept",
        y="Score",
        color="Score",
        title="Average Concept Scores"
    )

    colC.plotly_chart(fig3, use_container_width=True)

    # Weak Concepts
    weak_df = weak_concepts.reset_index()
    weak_df.columns = ["Concept", "Score"]

    fig4 = px.pie(
        weak_df,
        values="Score",
        names="Concept",
        title="Weak Concepts"
    )

    colD.plotly_chart(fig4, use_container_width=True)

# Student Dashboard
elif page == "Student Progress":

    st.title("👨‍🎓 Student Progress Analytics")

    students = data["student"].unique()
    selected_student = st.selectbox("Select Student", students)

    student_data = data[data["student"] == selected_student]

    st.subheader(f"Performance of {selected_student}")

    col1, col2 = st.columns(2)

    # Grade Trend
    fig = px.line(
        student_data,
        x="assignment",
        y="grade",
        markers=True,
        title="Grade Trend Over Time"
    )

    col1.plotly_chart(fig, use_container_width=True)

    # Plagiarism Trend
    fig2 = px.line(
        student_data,
        x="assignment",
        y="plagiarism",
        markers=True,
        title="Plagiarism Score Trend"
    )

    col2.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # Concept Radar Chart
    concept_values = student_data[concept_cols].mean()

    radar_df = pd.DataFrame({
        "Concept": concept_cols,
        "Score": concept_values
    })

    fig3 = px.line_polar(
        radar_df,
        r="Score",
        theta="Concept",
        line_close=True,
        title="Concept Skill Radar"
    )

    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    # Weak Concepts
    weak_student = concept_values.sort_values().head(2)

    st.subheader("⚠ Current Weak Concepts")

    for concept in weak_student.index:
        st.warning(concept)

    st.subheader("💡 Personalized Recommendations")

    if "concept_recursion" in weak_student.index:
        st.write("• Practice recursion base cases")

    if "concept_trees" in weak_student.index:
        st.write("• Study tree traversal algorithms")

    if "concept_graphs" in weak_student.index:
        st.write("• Solve BFS/DFS problems")

    if "concept_dp" in weak_student.index:
        st.write("• Review dynamic programming patterns")