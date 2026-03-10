import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

def show():

    st.title("Student Progress")

    data = load_data()

    students = data["student"].unique()
    student = st.selectbox("Select Student", students)

    student_data = data[data["student"] == student]

    st.subheader("Score Trend")

    fig = px.line(
        student_data,
        x="assignment",
        y="score",
        markers=True,
        color="question"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Question Performance Radar")

    avg_scores = student_data.groupby("question")["score"].mean().reset_index()

    fig2 = px.line_polar(
        avg_scores,
        r="score",
        theta="question",
        line_close=True
    )

    st.plotly_chart(fig2, use_container_width=True)