"""
dashboards/district.py
----------------------
Defines the dashboard view for District Education Officers (DEO).
Limits scope to the officer's district and supports status tracking, inspector assignment, and log verification.
"""
import streamlit as st
import pandas as pd
from database.connection import execute_query
from services.issue_service import get_filtered_issues, update_issue_status
from services.inspection_service import create_inspection
from services.notification_service import get_unread_notifications, mark_notification_as_read
from components.maps import draw_schools_map
from components.timelines import draw_issue_status_timeline, draw_evidence_timeline, draw_audit_trail_timeline
from services.audit_service import get_audit_trail

def render_district_dashboard(user_profile: dict):
    """
    Renders analytics, maps, issues, and inspection forms for District Officers.
    """
    district = user_profile.get("district")
    st.title(f"🏛️ District Education Command Center: {district}")
    st.write(f"Welcome, District Officer. Displaying monitoring data for **{district} District** schools.")

    # Load notifications for this role
    notifications = get_unread_notifications(user_profile)
    if notifications:
        with st.expander(f"🔔 Jurisdictional Alerts ({len(notifications)})", expanded=True):
            for notif in notifications:
                c_alert, c_btn = st.columns([0.8, 0.2])
                with c_alert:
                    if notif["type"] == "Emergency":
                        st.error(f"🛑 {notif['message']} (*{notif['timestamp']}*)")
                    else:
                        st.warning(f"⚠️ {notif['message']} (*{notif['timestamp']}*)")
                with c_btn:
                    if st.button("Mark Read", key=f"notif_{notif['id']}"):
                        mark_notification_as_read(notif["id"])
                        st.rerun()

    # 1. Fetch District Schools
    district_schools = execute_query("SELECT * FROM schools WHERE district = ?;", (district,))
    
    # 2. Fetch District Issues
    filters = {"district": district}
    issues = get_filtered_issues(user_profile, filters)

    # ─────────────────────────────────────────────────────────────────────────
    # DISTRICT OVERVIEW METRICS
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("📊 District KPIs")
    total_sch = len(district_schools)
    open_iss = sum(1 for i in issues if i["status"] != "Closed")
    urgent_iss = sum(1 for i in issues if i["priority_level"] == "Urgent" and i["status"] != "Closed")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total District Schools", total_sch)
    with m2:
        st.metric("Active Open Reports", open_iss)
    with m3:
        st.metric("🔴 Urgent Situations", urgent_iss)
    with m4:
        avg_h = sum(s["health_score"] for s in district_schools) / max(total_sch, 1)
        st.metric("Average Health index", f"{avg_h:.1f}/100")

    # Display Map
    st.subheader("🗺️ District Schools Risk Map")
    draw_schools_map(district_schools)

    tab_issues, tab_inspect = st.tabs(["📋 Active Complaints Register", "🔍 Schedule & Log Inspections"])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1: DISCIPLINARY LOGS & REPAIR ASSIGNMENTS
    # ═════════════════════════════════════════════════════════════════════════
    with tab_issues:
        st.subheader("📋 Active Issues Register")
        if not issues:
            st.info("No active open reports listed in your district.")
        else:
            df_issues = pd.DataFrame(issues)
            
            # Filter bar
            f_taluk, f_priority, f_status = st.columns(3)
            with f_taluk:
                tal_opts = ["All"] + sorted(df_issues["taluk"].unique().tolist())
                sel_tal = st.selectbox("Filter Taluk", tal_opts)
            with f_priority:
                pri_opts = ["All"] + sorted(df_issues["priority_level"].unique().tolist())
                sel_pri = st.selectbox("Filter Priority", pri_opts)
            with f_status:
                stat_opts = ["All"] + sorted(df_issues["status"].unique().tolist())
                sel_stat = st.selectbox("Filter Status", stat_opts)
                
            filtered_df = df_issues.copy()
            if sel_tal != "All":
                filtered_df = filtered_df[filtered_df["taluk"] == sel_tal]
            if sel_pri != "All":
                filtered_df = filtered_df[filtered_df["priority_level"] == sel_pri]
            if sel_stat != "All":
                filtered_df = filtered_df[filtered_df["status"] == sel_stat]

            if filtered_df.empty:
                st.info("No issues match selected filters.")
            else:
                display_cols = ["report_id", "school_name", "taluk", "category", "priority_level", "status", "submitted_time"]
                st.dataframe(filtered_df[display_cols].rename(columns={
                    "report_id": "ID", "school_name": "School Name", "taluk": "Taluk",
                    "category": "Category", "priority_level": "Priority", "status": "Status", "submitted_time": "Date Logged"
                }), use_container_width=True, hide_index=True)

                # Selected Detail View / Status Updates
                st.subheader("⚙️ Update Issue Assignment & Status Log")
                selected_rpt_id = st.selectbox("Select Report ID:", options=filtered_df["report_id"].tolist())
                
                # Fetch target issue
                selected_issue = next(i for i in issues if i["report_id"] == selected_rpt_id)
                st.markdown(f"💬 **Complaint Description:** \"{selected_issue['description']}\"")
                st.markdown(f"⏳ **SLA Deadline:** `{selected_issue['resolution_deadline']}`")
                
                # Display progress status
                draw_issue_status_timeline(selected_issue["status"])

                uc1, uc2 = st.columns(2)
                with uc1:
                    # Update status
                    new_status = st.selectbox(
                        "Transition Status Stage:",
                        options=["Pending", "Verified", "Under Review", "Inspection Required", "Action Started", "Action Completed", "Closed"],
                        index=["Pending", "Verified", "Under Review", "Inspection Required", "Action Started", "Action Completed", "Closed"].index(selected_issue["status"])
                    )
                    if new_status != selected_issue["status"]:
                        update_issue_status(selected_issue["id"], new_status, user_profile)
                        st.success("Status stage updated!")
                        st.rerun()
                with uc2:
                    # Update contractor assignment
                    current_assign = selected_issue.get("assignment", "")
                    new_assign = st.text_input("Assign Officer/Contractor Department:", value=current_assign if current_assign else "")
                    if st.button("Save Assignment"):
                        execute_query("UPDATE issues SET assignment = ? WHERE id = ?;", (new_assign, selected_issue["id"]), fetch="rowcount")
                        st.success("Department assignment saved!")
                        st.rerun()

                # Display chronological logs
                logs = get_audit_trail("issue", selected_rpt_id)
                draw_audit_trail_timeline(logs)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2: LOG INSPECTIONS
    # ═════════════════════════════════════════════════════════════════════════
    with tab_inspect:
        st.subheader("🔍 Record Inspection Visit findings")
        st.write("Record physical site findings to confirm issues or trigger state repair grants.")

        with st.form("district_inspection_form"):
            sch_select = st.selectbox(
                "Target School Site:",
                options=[s["id"] for s in district_schools],
                format_func=lambda sid: next(s["name"] for s in district_schools if s["id"] == sid)
            )
            
            # Filter issues linked to this school to link inspection
            open_school_issues = execute_query(
                "SELECT id, report_id, category FROM issues WHERE school_id = ? AND status != 'Closed';",
                (sch_select,)
            )
            issue_options = [(None, "No Linked Complaint (Routine Inspection)")]
            if open_school_issues:
                for oi in open_school_issues:
                    issue_options.append((oi["id"], f"{oi['report_id']} - {oi['category']}"))
            
            selected_issue_tuple = st.selectbox(
                "Associate with Open Complaint:",
                options=[io[0] for io in issue_options],
                format_func=lambda iid: next(io[1] for io in issue_options if io[0] == iid)
            )
            
            inspector = st.text_input("Inspector Name / Credentials:", value=user_profile["username"])
            findings = st.text_area("Observations and Findings:")
            ver_status = st.selectbox("Findings Verification:", ["Verified Problem", "Minor Issues Only", "No Deficit Found"])
            recommendations = st.text_area("Recommendations:")
            
            ins_submit = st.form_submit_button("Record Inspection Report")

        if ins_submit:
            if not findings.strip() or not inspector.strip():
                st.error("Please provide inspector name and findings.")
            else:
                create_inspection(
                    school_id=sch_select,
                    issue_id=selected_issue_tuple,
                    inspector_name=inspector.strip(),
                    findings=findings.strip(),
                    verified_status=ver_status,
                    recommendations=recommendations.strip()
                )
                st.success("Inspection findings recorded. Target issue has been transitioned to 'Inspection Completed'.")
                st.rerun()
