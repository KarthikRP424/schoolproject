"""
dashboards/school.py
--------------------
Defines the dashboard view for school-level stakeholders (Headmasters, Student Reps, Volunteers).
Provides complete digital profile views, issue reporting modules, verification actions, and student feedback loops.
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from database.connection import execute_query
from services.issue_service import create_issue, get_filtered_issues, update_issue_status
from services.verification_service import submit_verification
from services.inspection_service import submit_student_consensus, get_pending_student_verifications
from services.sla_service import get_sla_status_for_issue
from services.priority_engine import (
    calculate_school_health, calculate_school_priority, 
    calculate_school_decline_risk, get_school_improvement_score
)
from services.audit_service import get_audit_trail
from components.timelines import draw_issue_status_timeline, draw_evidence_timeline, draw_audit_trail_timeline
from components.charts import plot_enrollment_trend, plot_attendance_trend, plot_historical_scores

def render_school_dashboard(user_profile: dict):
    """
    Renders school digital profile tabs, reporting, and issue verifications.
    """
    # 1. Fetch Assigned School ID
    school_id = user_profile.get("school_id")
    
    if not school_id and user_profile.get("role") == "Village Volunteer":
        # Volunteers look up schools inside their assigned village
        village_schools = execute_query("SELECT id, name FROM schools WHERE village = ?;", (user_profile.get("village"),))
        if village_schools:
            school_select = st.selectbox("Select School to Inspect", options=[s["id"] for s in village_schools],
                                           format_func=lambda sid: next(s["name"] for s in village_schools if s["id"] == sid))
            school_id = school_select
        else:
            st.error("No schools mapped to your village scope.")
            return
            
    if not school_id:
        st.error("Access Denied: No school assigned to your profile.")
        return

    # Fetch school details from DB
    school = execute_query("SELECT * FROM schools WHERE id = ?;", (school_id,), fetch="one")
    if not school:
        st.error("School record not found.")
        return

    # Trigger re-calculations for real-time scores consistency
    priority = calculate_school_priority(school_id)
    health = calculate_school_health(school_id)
    risk = calculate_school_decline_risk(school_id)
    improvement = get_school_improvement_score(school_id)

    # ─────────────────────────────────────────────────────────────────────────
    # HEADER
    # ─────────────────────────────────────────────────────────────────────────
    st.title(f"🏫 Digital Profile: {school['name']}")
    st.write(f"📍 Location: {school['village']}, {school['taluk']} Taluk, {school['district']} District.")

    tab_profile, tab_report, tab_verify = st.tabs([
        "📊 School Digital Profile", 
        "📝 Submit Issue Report", 
        "🔍 Verify & Confirm Issues"
    ])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1: DIGITAL PROFILE OVERVIEW
    # ═════════════════════════════════════════════════════════════════════════
    with tab_profile:
        # Top level scorecard metrics
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Health Score Index", f"{health['score']}/100", help="Evaluates general school operation status.")
        with m2:
            st.metric("Priority score", f"{priority['score']}/100", help="Measures need for immediate governmental intervention.")
        with m3:
            st.metric("Decline Risk Warning", f"{risk['percentage']}%", delta=risk["risk_level"], delta_color="inverse")
        with m4:
            st.metric("Improvement Net", f"{'+' if improvement >= 0 else ''}{improvement} pts", help="Historical progress tracking.")

        # Layout division: Core stats vs Facility Grid
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("👥 Operational Details")
            st.write(f"**School Type:** {school['school_type']}")
            st.write(f"**Total Student Enrollment:** {school['num_students']} children")
            st.write(f"**Teachers Available:** {school['available_teachers']} / {school['required_teachers']} required positions")
            st.write(f"**Daily Student Attendance average:** {school['attendance_pct']}%")
            
            # Sub-charts: Enrollment history
            st.write("**Enrollment History**")
            enroll_recs = execute_query("SELECT year, num_students FROM enrollment_records WHERE school_id = ?;", (school_id,))
            plot_enrollment_trend(enroll_recs)

        with col_right:
            st.subheader("🏗️ Facility Condition Check")
            fac_status = json.loads(school["facility_status_json"]) if school["facility_status_json"] else {}
            
            # Format as grid of statuses
            fac_rows = []
            for fac, status in fac_status.items():
                icon = "✅" if status == "Available" else "⚠️" if status == "Partially Available" else "❌" if status == "Not Available" else "🚨"
                fac_rows.append({"Facility": fac.replace("_", " ").title(), "Status": f"{icon} {status}"})
            st.table(pd.DataFrame(fac_rows))

        # Attendance and Scores history
        st.subheader("📈 Performance Metrics Trends")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Attendance History**")
            att_recs = execute_query("SELECT month_name, attendance_pct FROM attendance_records WHERE school_id = ?;", (school_id,))
            plot_attendance_trend(att_recs)
        with c2:
            st.write("**Historical Health vs Priority Score**")
            score_recs = execute_query("SELECT timestamp, health_score, priority_score FROM historical_scores WHERE school_id = ?;", (school_id,))
            plot_historical_scores(score_recs)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2: SUBMIT ISSUE REPORT
    # ═════════════════════════════════════════════════════════════════════════
    with tab_report:
        st.subheader("📝 Report School Facility Deficit")
        st.write("Submit plumbing, electricity, teacher, or structural issues directly to district education officers.")

        with st.form("school_reporting_form"):
            issue_cat = st.selectbox("Issue Category", [
                "Sanitation", "Drinking Water", "Teacher Shortage", "Infrastructure", "Electricity", "General Issue"
            ])
            issue_desc = st.text_area("Issue Description", placeholder="Be detailed. State what is broken and who is affected...")
            
            st.markdown("**Evidence Upload (Simulation)**")
            up_col1, up_col2 = st.columns(2)
            with up_col1:
                photo_file = st.file_uploader("Upload Evidence Photo", type=["jpg", "png", "jpeg"])
                has_photo = photo_file is not None
            with up_col2:
                gps_input = st.text_input("GPS Coordinates (Latitude, Longitude)", value=f"{school['latitude']}, {school['longitude']}")
                has_gps = len(gps_input.strip()) > 0

            form_submit = st.form_submit_button("🔍 Submit to Department")

        if form_submit:
            if not issue_desc.strip():
                st.error("Please provide a description of the issue.")
            else:
                p_name = photo_file.name if has_photo else ""
                res = create_issue(
                    school_id=school_id,
                    reporter_id=user_profile["id"],
                    reporter_role=user_profile["role"],
                    description=issue_desc.strip(),
                    has_photo=has_photo,
                    has_gps=has_gps,
                    gps_coords=gps_input.strip(),
                    photo_name=p_name
                )
                
                st.success("Report submitted successfully and sent to Government Officer dashboard.")
                st.info(f"📋 **Generated Report ID:** `{res['report_id']}`")
                if res["is_duplicate"]:
                    st.warning(f"⚠️ Possible Duplicate Warning: This issue resembles RPT-`{res['parent_report_id']}` already logged.")

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 3: VERIFY & CONFIRM OPEN ISSUES
    # ═════════════════════════════════════════════════════════════════════════
    with tab_verify:
        st.subheader("🔍 Local Verification Loop")
        st.write("Confirm reports logged by others or give student-representative closure approvals.")

        # Fetch open issues for this school using canonical status names
        open_issues = execute_query(
            """SELECT * FROM issues WHERE school_id = ?
               AND status NOT IN ('CLOSED','MERGED','Closed')
               ORDER BY submitted_time DESC;""",
            (school_id,)
        )

        if not open_issues:
            st.info("No open reports require verification feedback at this school.")
        else:
            issue_select = st.selectbox(
                "Select Issue Report to Verify:",
                options=[i["id"] for i in open_issues],
                format_func=lambda iid: next(f"{i['report_id']} - {i['category']} ({i['status']})" for i in open_issues if i["id"] == iid)
            )
            
            selected_issue = next(i for i in open_issues if i["id"] == issue_select)
            
            # SLA Status Badge
            sla = get_sla_status_for_issue(selected_issue)
            sla_icon = {"BREACHED": "🔴", "DUE_SOON": "🟡", "ON_TRACK": "🟢"}.get(sla["status"], "⚪")
            st.markdown(f"**SLA Status:** {sla_icon} `{sla['label']}`")
            
            st.markdown(f"💬 **Complaint Description:** \"{selected_issue['description']}\"")
            st.markdown(f"📈 **Confidence:** `{selected_issue['verification_confidence']}%` | **Verification Status:** `{selected_issue['verification_status']}`")
            
            # Show progress timeline
            draw_issue_status_timeline(selected_issue["status"])

            # Student Consensus voting (only for STUDENT_VERIFICATION status)
            if selected_issue["status"] == "STUDENT_VERIFICATION" and user_profile["role"] == "Student Representative":
                st.markdown("### 🗳️ Student Consensus Vote")
                st.info("3 of 5 student representatives must approve to CLOSE, or 3 rejections to REOPEN.")
                col_a, col_r = st.columns(2)
                with col_a:
                    if st.button("✅ Approve — Issue Resolved", key=f"cons_app_{issue_select}"):
                        result = submit_student_consensus(issue_select, user_profile["id"], approves=True)
                        if result["action"] == "CLOSED":
                            st.success(f"Issue CLOSED by consensus! ({result['approvals']}/5 approvals)")
                        else:
                            st.info(f"Vote recorded. Approvals: {result['approvals']}, Rejections: {result['rejections']}")
                        st.rerun()
                with col_r:
                    if st.button("❌ Reject — Problem Not Fixed", key=f"cons_rej_{issue_select}"):
                        result = submit_student_consensus(issue_select, user_profile["id"], approves=False)
                        if result["action"] == "REOPENED":
                            st.warning(f"Issue REOPENED! ({result['rejections']}/5 rejections)")
                        else:
                            st.info(f"Vote recorded. Approvals: {result['approvals']}, Rejections: {result['rejections']}")
                        st.rerun()

            # ─────────────────────────────────────────────────────────────────
            # VERIFY ACTION
            # ─────────────────────────────────────────────────────────────────
            st.markdown("### ✍️ Provide Verification Signature")
            
            # Check if user already submitted a verification
            prior_verification = execute_query(
                "SELECT confirms_issue FROM issue_verifications WHERE issue_id = ? AND user_id = ?;",
                (issue_select, user_profile["id"]),
                fetch="one"
            )
            
            if prior_verification:
                st.info(f"You have already verified this issue. Your choice: {'Confirms Problem' if prior_verification['confirms_issue'] == 1 else 'Declares Problem False/No Conflict'}")
            
            vc1, vc2 = st.columns(2)
            with vc1:
                if st.button("Confirm Issue Exists", key="conf_yes", use_container_width=True):
                    submit_verification(issue_select, user_profile["id"], user_profile["role"], confirms_issue=True)
                    st.success("Verification submitted!")
                    st.rerun()
            with vc2:
                if st.button("Declare Issue is Not Present (Raise Conflict)", key="conf_no", use_container_width=True):
                    submit_verification(issue_select, user_profile["id"], user_profile["role"], confirms_issue=False)
                    st.warning("Conflict signature recorded. Notification dispatched to District Officer.")
                    st.rerun()

            # ─────────────────────────────────────────────────────────────────
            # STUDENT CLOSURE LOOP
            # ─────────────────────────────────────────────────────────────────
            if selected_issue["status"] == "Action Completed" and user_profile["role"] == "Student Representative":
                st.markdown("### 🎓 Student Representative Resolution Review")
                st.write("Work has been marked completed by the department. Does the issue actually resolve the problem?")
                
                with st.form("student_feedback_form"):
                    resolved_rating = st.selectbox(
                        "Status Rating",
                        options=["Fully Solved", "Partially Solved", "Not Solved"],
                        help="Choose if the work done fully solved the issue."
                    )
                    feedback_msg = st.text_area("Feedback Message", placeholder="Enter details about the quality of resolution...")
                    feedback_submit = st.form_submit_button("Submit Resolution Review")

                if feedback_submit:
                    # Save feedback
                    execute_query(
                        """
                        INSERT INTO student_feedback (issue_id, rep_name, status_rating, feedback_text, timestamp)
                        VALUES (?, ?, ?, ?, ?);
                        """,
                        (issue_select, user_profile["username"], resolved_rating, feedback_msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        fetch="rowcount"
                    )
                    
                    if resolved_rating == "Fully Solved":
                        # Check student rep consensus: if 3/5 or more students mark Fully Solved, close report!
                        all_feedback = execute_query(
                            "SELECT status_rating FROM student_feedback WHERE issue_id = ?;", (issue_select,)
                        )
                        fully_solved_count = sum(1 for f in all_feedback if f["status_rating"] == "Fully Solved")
                        
                        if fully_solved_count >= 3:
                            update_issue_status(issue_select, "Closed", user_profile)
                            st.success("Consensus reached! 3+ Student Representatives marked issue as solved. Report is now CLOSED.")
                            st.rerun()
                        else:
                            st.success(f"Feedback logged. Current consensus: {fully_solved_count}/3 reviews required to close.")
                    else:
                        # Re-open or trigger alert
                        st.warning("Resolution rejected. Notification sent to Taluk education officer to review plumber/engineer work.")

            # Display chronological logs
            logs = get_audit_trail("issue", selected_issue["report_id"])
            draw_audit_trail_timeline(logs)
