"""
components/maps.py
------------------
Renders geographical coordinates of schools on an interactive map.
Color-codes markers based on school Priority Levels.
"""
import streamlit as st
import pandas as pd

def draw_schools_map(schools: list):
    """
    Plots schools on a map, color-coded by priority level:
    - LOW: Green (#22c55e)
    - MODERATE: Yellow (#eab308)
    - HIGH: Orange (#f97316)
    - CRITICAL: Red (#ef4444)
    - EMERGENCY: Dark Red (#7f1d1d)
    """
    if not schools:
        st.info("No school coordinate coordinates found to draw.")
        return
    
    df = pd.DataFrame(schools)
    
    # Define hex colors for priority levels
    color_mapping = {
        "LOW": "#22c55e",
        "MODERATE": "#eab308",
        "HIGH": "#f97316",
        "CRITICAL": "#ef4444",
        "EMERGENCY": "#7f1d1d"
    }
    
    # Map priority_level to color, fallback to slate gray
    df["color"] = df["priority_level"].map(color_mapping).fillna("#64748b")
    
    # Display coordinates using Streamlit built-in map engine
    st.map(df, latitude="latitude", longitude="longitude", color="color", size=30)
