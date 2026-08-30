"""
components/timelines.py
-----------------------
Visual timeline components.
Renders issue lifecycle stages, audit log trails, and chronological evidence.
"""
import streamlit as st

def draw_issue_status_timeline(current_status: str):
    """
    Renders horizontal indicators of the issue workflow stages.
    Highlights past, current, and future stages.
    """
    stages = [
        "Pending", "Verified", "Under Review", "Inspection Required",
        "Inspection Completed", "Action Started", "Action Completed",
        "Student Verification", "Closed"
    ]
    
    try:
        current_idx = stages.index(current_status)
    except ValueError:
        current_idx = 0
        
    st.markdown("### 🗺️ Issue Resolution Stage Progress")
    
    # Render vertical progress timeline cleanly
    timeline_html = ""
    for idx, stage in enumerate(stages):
        if idx < current_idx:
            status_icon = "🟢"
            status_text = f"<b>{stage}</b> (Completed)"
        elif idx == current_idx:
            status_icon = "🔵"
            status_text = f"<span style='color: #1e3a8a;'><b>{stage} (Active Stage)</b></span>"
        else:
            status_icon = "⚪"
            status_text = f"<span style='color: gray;'>{stage}</span>"
        timeline_html += f"<div>{status_icon} {status_text}</div>"
        
    st.markdown(timeline_html, unsafe_allow_html=True)

def draw_evidence_timeline(evidences: list):
    """
    Displays photo evidence timeline.
    """
    if not evidences:
        st.info("No timeline evidence uploads registered yet.")
        return
        
    st.markdown("### 📷 Chronological Evidence Timeline")
    for ev in evidences:
        st.markdown(f"**📅 Stage: {ev['stage']}** — *{ev['timestamp']}*")
        st.markdown(f"📁 Image: `{ev['photo_name']}`")
        st.markdown(f"📝 Description: {ev['description']}")
        st.markdown("---")

def draw_audit_trail_timeline(logs: list):
    """
    Displays chronological log trails.
    """
    if not logs:
        st.info("No system audit trail activities recorded.")
        return
        
    st.markdown("### 🕒 Immutable System Audit Trail")
    for log in logs:
        st.markdown(
            f"**[{log['timestamp']}]** {log['username']} ({log['role']}) "
            f"executed `{log['action']}` on {log['entity_type']} **{log['entity_id']}**"
        )
        if log["prev_value"] is not None or log["new_value"] is not None:
            st.markdown(f"➔ Change: `{log['prev_value']}` ➔ `{log['new_value']}`")
        st.markdown("---")
