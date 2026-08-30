"""
dashboards/state.py
-------------------
State-level officer dashboard providing comprehensive monitoring across Karnataka.
Features high-risk warnings, resource allocation priorities, heatmaps, and audit registers.
"""
import streamlit as st
import pandas as pd
import json
from database.connection import execute_query
from services.priority_engine import update_all_school_scores
from services.notification_service import get_unread_notifications, mark_notification_as_read
from components.maps import draw_schools_map
from components.charts import plot_district_comparison

def render_state_dashboard(user_profile: dict):
    """
    Renders analytics, maps, resource rankings, and notifications for state-level officials.
    """
    st.title("🏛️ Karnataka State School Monitoring Command Center")
    st.write("Welcome, State Administrator. Real-time data compiled from school inspection nodes across districts.")

    # Refresh scores on loading dashboard
    update_all_school_scores()

    # Load all schools
    schools = execute_query("SELECT * FROM schools;")
    # Load all issues
    issues = execute_query(
        """
        SELECT i.*, s.name as school_name, s.district, s.taluk, s.priority_level 
        FROM issues i JOIN schools s ON i.school_id = s.id;
        """
    )
    # Load notifications
    notifications = get_unread_notifications(user_profile)

    # ─────────────────────────────────────────────────────────────────────────
    # ALERTS & NOTIFICATIONS
    # ─────────────────────────────────────────────────────────────────────────
    if notifications:
        with st.expander(f"🔔 Unread Alerts & Notifications ({len(notifications)})", expanded=True):
            for notif in notifications:
                c_alert, c_btn = st.columns([0.8, 0.2])
                with c_alert:
                    if notif["type"] == "Emergency":
                        st.error(f"🛑 {notif['message']} (*{notif['timestamp']}*)")
                    elif notif["type"] == "Conflict":
                        st.warning(f"⚠️ {notif['message']} (*{notif['timestamp']}*)")
                    else:
                        st.info(f"📋 {notif['message']} (*{notif['timestamp']}*)")
                with c_btn:
                    if st.button("Mark Read", key=f"notif_{notif['id']}"):
                        mark_notification_as_read(notif["id"])
                        st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # STATE OVERVIEW METRICS
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("📈 Statewide KPI Overview")
    
    total_schools = len(schools)
    open_issues = sum(1 for i in issues if i["status"] != "Closed")
    critical_schools = sum(1 for s in schools if s["priority_level"] in ["CRITICAL", "EMERGENCY"])
    high_risk_decline = sum(1 for s in schools if s["decline_risk"] >= 50.0)
    
    avg_health = sum(s["health_score"] for s in schools) / max(total_schools, 1)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Schools Mapped", total_schools)
    with m2:
        st.metric("Average School Health", f"{avg_health:.1f}/100")
    with m3:
        st.metric("🔴 Emergency & Critical Schools", critical_schools)
    with m4:
        st.metric("⚠️ Decline Risk Warning", high_risk_decline)
    with m5:
        st.metric("📂 Unresolved Issues Logs", open_issues)

    # ─────────────────────────────────────────────────────────────────────────
    # MAPS & HEATMAPS
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("🗺️ Geographic Risk Mapping")
    
    map_tab, heatmap_tab = st.tabs(["🔴 Coordinate Risk Map", "🔥 Facility Deficit Map"])
    
    with map_tab:
        st.write("Markers color-coded by School Priority Level (Green = Healthy, Red = Critical, Dark Red = Emergency).")
        draw_schools_map(schools)
        
    with heatmap_tab:
        issue_cat_select = st.selectbox(
            "Filter Geographic Heatmap by Facility Deficit Category:",
            ["All", "Sanitation", "Drinking Water", "Teacher Shortage", "Infrastructure", "Electricity"]
        )
        
        if issue_cat_select == "All":
            active_coords = [
                {"latitude": float(i["latitude"]), "longitude": float(i["longitude"]), "priority_level": i["priority_level"]}
                for i in issues if i["latitude"] not in ["None", None] and i["status"] != "Closed"
            ]
        else:
            active_coords = [
                {"latitude": float(i["latitude"]), "longitude": float(i["longitude"]), "priority_level": i["priority_level"]}
                for i in issues if i["latitude"] not in ["None", None] and i["status"] != "Closed" and i["category"] == issue_cat_select
            ]
            
        if active_coords:
            st.write(f"Showing active coordinate nodes for: **{issue_cat_select}**")
            draw_schools_map(active_coords)
        else:
            st.info("No active reports matching selected category contain coordinate metadata.")

    # ─────────────────────────────────────────────────────────────────────────
    # RESOURCE PRIORITIZATION
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("💰 Smart Budget & Resource Allocator")
    st.markdown(
        "> 🤖 **AI/Rule-Based Recommendation** — This model ranks facility needs using combined priority and safety coefficients. "
        "It does not represent binding financial policy."
    )
    
    budget = st.number_input("Input Available Infrastructure Budget (₹):", min_value=10000, value=2500000, step=50000)
    
    # Prioritization ranking algorithm
    ranked_schools = []
    for s in schools:
        # Cost factor estimate: Sanitation=3L, Water=1.5L, Staff=0L, Infra=8L, Elect=1L
        needed_fund = 0
        reasons = []
        
        # Parse facility JSON
        facs = json.loads(s["facility_status_json"]) if s["facility_status_json"] else {}
        if facs.get("girls_toilet") in ["Not Available", "Damaged"] or facs.get("boys_toilet") in ["Not Available", "Damaged"]:
            needed_fund += 300000
            reasons.append("Toilets Reconstruction")
        if facs.get("drinking_water") in ["Not Available", "Damaged"]:
            needed_fund += 150000
            reasons.append("RO Plant Setup")
        if facs.get("building_condition") == "Damaged" or facs.get("classrooms") == "Damaged":
            needed_fund += 800000
            reasons.append("Structural Repairs")
        if facs.get("electricity") in ["Not Available", "Damaged"]:
            needed_fund += 100000
            reasons.append("Electrical Re-wiring")
            
        if needed_fund > 0:
            ranked_schools.append({
                "id": s["id"],
                "name": s["name"],
                "district": s["district"],
                "taluk": s["taluk"],
                "score": s["priority_score"],
                "decline_risk": s["decline_risk"],
                "required_fund": needed_fund,
                "reasons": ", ".join(reasons)
            })
            
    # Sort schools by priority score descending
    ranked_schools = sorted(ranked_schools, key=lambda x: x["score"], reverse=True)
    
    # Distribute budget
    allocated_list = []
    rem_budget = budget
    for r in ranked_schools:
        if rem_budget >= r["required_fund"]:
            status = "₹" + f"{r['required_fund']:,}"
            rem_budget -= r["required_fund"]
        else:
            status = "Partially Funded"
        
        allocated_list.append({
            "School Name": r["name"],
            "Location": f"{r['taluk']}, {r['district']}",
            "Priority score": r["score"],
            "Estimated Cost": f"₹{r['required_fund']:,}",
            "Allocation Recommendation": status,
            "Target Areas": r["reasons"]
        })
        
    st.dataframe(pd.DataFrame(allocated_list), use_container_width=True)
    st.write(f"⚖️ Remaining Unallocated Reserve: **₹{rem_budget:,}**")

    # ─────────────────────────────────────────────────────────────────────────
    # ANALYTICS & CHARTS
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("📊 Statewide Analytics & Trends")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**District Health Index Comparisons**")
        plot_district_comparison(schools)
        
    with c2:
        st.write("**Top 5 Highest-Risk Schools**")
        df_risk = pd.DataFrame(schools).sort_values("decline_risk", ascending=False).head(5)
        st.dataframe(
            df_risk[["name", "district", "taluk", "decline_risk"]].rename(columns={
                "name": "School Name", "district": "District", "taluk": "Taluk", "decline_risk": "Decline Risk (%)"
            }),
            use_container_width=True, hide_index=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ACTIVE REPORTS LOG
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("📋 Active Statewide Issue Register")
    if not issues:
        st.info("No active reports listed.")
    else:
        df_issues = pd.DataFrame(issues)
        display_cols = ["report_id", "school_name", "district", "category", "priority_level", "status", "submitted_time"]
        st.dataframe(df_issues[display_cols].rename(columns={
            "report_id": "ID", "school_name": "School", "district": "District",
            "category": "Category", "priority_level": "Priority", "status": "Status", "submitted_time": "Date Logged"
        }), use_container_width=True, hide_index=True)
