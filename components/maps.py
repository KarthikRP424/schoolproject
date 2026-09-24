"""
components/maps.py
------------------
Renders geographical coordinates of schools on an interactive map.
Color-codes markers by priority level with RGBA tuples for Streamlit st.map.
"""
import streamlit as st
import pandas as pd

# RGBA color tuples [r, g, b, a] per priority level
PRIORITY_COLORS = {
    "LOW":       [34,  197, 94,  180],   # Green
    "MODERATE":  [234, 179, 8,   200],   # Yellow
    "HIGH":      [249, 115, 22,  220],   # Orange
    "CRITICAL":  [239, 68,  68,  220],   # Red
    "EMERGENCY": [127, 29,  29,  255],   # Dark Red
    "URGENT":    [239, 68,  68,  220],   # Red (alias)
}
PRIORITY_SIZE = {
    "LOW": 100, "MODERATE": 150, "HIGH": 220, "CRITICAL": 300, "EMERGENCY": 400, "URGENT": 300
}
DEFAULT_COLOR = [100, 116, 139, 160]  # Slate gray
DEFAULT_SIZE  = 120


def draw_schools_map(schools: list, title: str = "School Locations"):
    """
    Plots schools on a map, color-coded by priority level.
    Safely casts string coordinates to float and skips invalid rows.
    """
    if not schools:
        st.info("No school coordinate data found.")
        return

    rows = []
    for s in schools:
        try:
            lat = float(s.get("latitude") or 0)
            lon = float(s.get("longitude") or 0)
            if lat == 0 and lon == 0:
                continue
        except (TypeError, ValueError):
            continue

        level = str(s.get("priority_level") or "").upper()
        rows.append({
            "latitude":  lat,
            "longitude": lon,
            "color":     PRIORITY_COLORS.get(level, DEFAULT_COLOR),
            "size":      PRIORITY_SIZE.get(level, DEFAULT_SIZE),
            "name":      s.get("name", ""),
            "district":  s.get("district", ""),
            "priority":  s.get("priority_level", "Unknown"),
        })

    if not rows:
        st.warning("No schools with valid coordinates to display.")
        return

    df = pd.DataFrame(rows)
    st.caption(f"🗺️ {title} — {len(df)} school(s) with valid coordinates")
    st.map(df, latitude="latitude", longitude="longitude", color="color", size="size")

    # Priority legend
    legend_cols = st.columns(len(PRIORITY_COLORS))
    for i, (level, rgba) in enumerate(PRIORITY_COLORS.items()):
        hex_c = "#{:02x}{:02x}{:02x}".format(*rgba[:3])
        legend_cols[i].markdown(
            f"<span style='background:{hex_c};padding:2px 8px;border-radius:4px;font-size:0.75rem;color:#fff'>"
            f"{level}</span>",
            unsafe_allow_html=True
        )

