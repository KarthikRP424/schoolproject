"""
components/charts.py
--------------------
Renders visual data representation using Streamlit native components.
Displays trends for enrollment, attendance, school health indices, and district comparisons.
"""
import streamlit as st
import pandas as pd

def plot_enrollment_trend(records: list):
    """
    Renders a line chart displaying multi-year enrollment growth or decline.
    """
    if not records:
        st.info("No enrollment history found.")
        return
    
    df = pd.DataFrame(records)
    df = df.sort_values("year")
    df = df.rename(columns={"year": "Year", "num_students": "Student Count"})
    df = df.set_index("Year")
    st.line_chart(df["Student Count"])

def plot_attendance_trend(records: list):
    """
    Renders a bar chart tracking monthly student attendance percentages.
    """
    if not records:
        st.info("No attendance history found.")
        return
    
    df = pd.DataFrame(records)
    df = df.rename(columns={"month_name": "Month", "attendance_pct": "Attendance (%)"})
    df = df.set_index("Month")
    st.bar_chart(df["Attendance (%)"])

def plot_historical_scores(records: list):
    """
    Renders comparison lines for Health Score vs. Priority Score over time.
    """
    if not records:
        st.info("No historical score tracking logged.")
        return
    
    df = pd.DataFrame(records)
    df = df.sort_values("timestamp")
    df = df.rename(columns={
        "timestamp": "Date Evaluated",
        "health_score": "School Health Score",
        "priority_score": "Priority Urgent Score"
    })
    df = df.set_index("Date Evaluated")
    st.line_chart(df[["School Health Score", "Priority Urgent Score"]])

def plot_district_comparison(schools: list):
    """
    Renders a bar chart comparing average health indices across districts.
    """
    if not schools:
        return
    
    df = pd.DataFrame(schools)
    grouped = df.groupby("district")["health_score"].mean().reset_index()
    grouped = grouped.rename(columns={"district": "District", "health_score": "Average Health Index"})
    grouped = grouped.set_index("District")
    st.bar_chart(grouped["Average Health Index"])
