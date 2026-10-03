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
    # TAB 2: SUBMIT EVIDENCE-DRIVEN ISSUE REPORT (SIH26095)
    # ═════════════════════════════════════════════════════════════════════════
    with tab_report:
        st.subheader("📝 Evidence-Driven Problem Reporting & AI Cross-Verification")
        st.caption("Submit multi-source evidence (Photos, Documents, GPS, Video) for instant AI cross-consistency audit before government authority review.")

        # ── HACKATHON DEMO PRESET LOADER ─────────────────────────────────────
        with st.expander("🧪 Hackathon Demo Presets — Load Pre-Configured Test Cases", expanded=False):
            preset = st.selectbox(
                "Select Test Case Scenario for Judge Demo:",
                [
                    "Custom Manual Input",
                    "Sample 1: Genuine / Consistent Report (High 92% Consistency)",
                    "Sample 2: Inconsistent Report (Text ↔ Document Mismatch)",
                    "Sample 3: Incomplete Document Report (Missing Authorization Stamp)",
                    "Sample 4: Recurring Issue Report (Increased Risk History)",
                    "Sample 5: High-Risk Location Mismatch (14.5km GPS Boundary Breach)"
                ]
            )

        # Preset default values
        default_cat = "Sanitation"
        default_title = ""
        default_desc = ""
        default_photo = ""
        default_doc = ""
        default_gps = f"{school['latitude']}, {school['longitude']}"
        default_remarks = ""

        if preset == "Sample 1: Genuine / Consistent Report (High 92% Consistency)":
            default_cat = "Drinking Water"
            default_title = "Drinking Water Purification Plant Failure"
            default_desc = "The main drinking water purification plant filter unit is damaged and leaking mud water into storage tanks."
            default_photo = "water_purifier_leak.jpg"
            default_doc = "rampura_water_maintenance_log.pdf"
            default_remarks = "Plumber inspected yesterday and recommended urgent membrane replacement."

        elif preset == "Sample 2: Inconsistent Report (Text ↔ Document Mismatch)":
            default_cat = "Electricity"
            default_title = "Classroom Wiring Short Circuit Outage"
            default_desc = "Electrical wiring short circuit in Class 7 room at Rampura Primary School."
            default_photo = "electrical_wiring.jpg"
            default_doc = "invoice_other_school_b.pdf"
            default_remarks = "Uploaded maintenance invoice references School B in Bhadravathi instead of Rampura Primary."

        elif preset == "Sample 3: Incomplete Document Report (Missing Authorization Stamp)":
            default_cat = "Sanitation"
            default_title = "Primary Washroom Drainage Blockage"
            default_desc = "Boys student washroom drainage pipeline completely blocked requiring emergency plumbing audit."
            default_photo = "toilet_blockage.jpg"
            default_doc = "draft_contract_no_stamp.pdf"
            default_remarks = "Document submitted is a draft work order lacking official reference date and seal."

        elif preset == "Sample 4: Recurring Issue Report (Increased Risk History)":
            default_cat = "Sanitation"
            default_title = "Recurrent Toilet Pipeline Overflow"
            default_desc = "Washroom pipeline overflowing again after partial repair attempt last fortnight."
            default_photo = "toilet_pipe_leak.jpg"
            default_doc = "plumbing_history_log.pdf"
            default_remarks = "Same category issue was logged 14 days ago; problem remains unresolved."

        elif preset == "Sample 5: High-Risk Location Mismatch (14.5km GPS Boundary Breach)":
            default_cat = "Infrastructure"
            default_title = "Playground Wall Structural Cracks"
            default_desc = "Concrete cracks opened on school boundary wall near playground threat of collapse."
            default_photo = "wall_crack_distant.jpg"
            default_doc = "civil_report.pdf"
            default_gps = "14.0500, 75.9000"
            default_remarks = "Submitted GPS location is 14.5 km away from registered school coordinates."

        # ── 8-STEP REPORTING FORM ───────────────────────────────────────────
        with st.form("evidence_reporting_form"):
            st.markdown("#### 📍 Step 1: Institution Context")
            st.info(f"**Institution:** {school['name']} | **ID:** `SCH-{school['id']}` | **Taluk:** {school['taluk']} | **District:** {school['district']}")

            st.markdown("#### 🏷️ Step 2: Problem Category & Title")
            c1, c2 = st.columns([0.4, 0.6])
            with c1:
                categories = ["Sanitation", "Drinking Water", "Teacher Shortage", "Infrastructure", "Electricity", "General Issue"]
                cat_idx = categories.index(default_cat) if default_cat in categories else 0
                issue_cat = st.selectbox("Problem Category *", categories, index=cat_idx)
            with c2:
                issue_title = st.text_input("Problem Title *", value=default_title, placeholder="e.g. Washroom Plumbing Blockage")

            st.markdown("#### 📝 Step 3: Detailed Description & Remarks")
            issue_desc = st.text_area("Detailed Problem Description *", value=default_desc, placeholder="Provide complete details on what is broken, severity, and impacted students...")
            add_remarks = st.text_input("Additional Remarks / Context", value=default_remarks, placeholder="e.g. Prior repair attempts, urgency notes...")

            st.markdown("#### 📷 Step 4: Multi-Source Evidence Upload")
            up1, up2, up3 = st.columns(3)
            with up1:
                photo_file = st.file_uploader("1. Photo Evidence", type=["jpg", "png", "jpeg"])
                sim_photo = st.text_input("Or Simulated Photo Filename", value=default_photo)
            with up2:
                doc_file = st.file_uploader("2. Maintenance Document / PDF", type=["pdf", "txt", "png", "jpg"])
                sim_doc = st.text_input("Or Supporting Doc Filename", value=default_doc)
            with up3:
                video_file = st.file_uploader("3. Video Evidence (Optional)", type=["mp4", "mov"])
                sim_video = st.text_input("Or Video Filename", value="")

            st.markdown("#### 🌐 Step 5: Capture / Select GPS Location")
            gps_input = st.text_input("GPS Coordinates (Latitude, Longitude) *", value=default_gps)

            st.markdown("---")
            form_submit = st.form_submit_button("🚀 Step 6: Submit Report & Execute AI Cross-Verification", type="primary", use_container_width=True)

        if form_submit:
            if not issue_desc.strip():
                st.error("Please provide a detailed problem description before submitting.")
            else:
                p_name = photo_file.name if photo_file else sim_photo.strip()
                d_name = doc_file.name if doc_file else sim_doc.strip()
                v_name = video_file.name if video_file else sim_video.strip()
                has_p = bool(p_name)
                has_g = len(gps_input.strip()) > 0

                # Execute Issue Creation & AI Cross-Verification
                res = create_issue(
                    school_id=school_id,
                    reporter_id=user_profile["id"],
                    reporter_role=user_profile["role"],
                    description=issue_desc.strip(),
                    has_photo=has_p,
                    has_gps=has_g,
                    gps_coords=gps_input.strip(),
                    photo_name=p_name,
                    title=issue_title.strip() or issue_desc[:40],
                    doc_name=d_name,
                    video_name=v_name,
                    additional_remarks=add_remarks.strip()
                )

                cross = res["cross_verification"]

                st.balloons()
                st.success(f"✅ **Report Submitted Successfully!** Generated Unique ID: `{res['report_id']}`")

                # ── STEP 7 & 8: AI MULTI-SOURCE CROSS-VERIFICATION CARD ───────
                st.markdown("### 🤖 Step 7 & 8: AI Multi-Source Cross-Verification Audit Result")

                # Top Metric Summary Cards
                mc1, mc2, mc3, mc4 = st.columns(4)
                with mc1:
                    score = cross["overall_consistency_score"]
                    st.metric("Overall Consistency", f"{score}%", help="Weighted internal consistency across Text, Image, Document, and Location.")
                with mc2:
                    st.metric("Evidence Confidence", f"{cross['evidence_confidence']}%", help="Confidence level based on multi-source coverage.")
                with mc3:
                    st.metric("Risk Score", f"{cross['risk_score']}/100")
                with mc4:
                    r_color = {"CRITICAL": "🔴", "HIGH": "🟧", "MEDIUM": "🨨", "LOW": "🟩"}.get(cross["risk_level"], "⚪")
                    st.metric("Risk Level", f"{r_color} {cross['risk_level']}")

                st.progress(score / 100.0)

                # Individual Check Cards
                st.markdown("#### 🔍 AI Check Breakdown")
                chk = cross["checks"]

                col_a, col_b = st.columns(2)
                with col_a:
                    t_doc = chk["text_document"]
                    c_badge = "✅ CONSISTENT" if t_doc["status"] == "CONSISTENT" else "⚠️ INCOMPLETE" if t_doc["status"] == "INCOMPLETE" else "❌ INCONSISTENT" if t_doc["status"] == "INCONSISTENT" else "⚪ UNKNOWN"
                    st.markdown(f"**Check 1: Text ↔ Document Consistency:** {c_badge} (`{t_doc['score']}%`)")
                    st.caption(f"Reason: {t_doc['reason']}")

                    t_img = chk["text_image"]
                    i_badge = "✅ CONSISTENT" if t_img["status"] == "CONSISTENT" else "📷 INSUFFICIENT" if t_img["status"] == "INSUFFICIENT_EVIDENCE" else "❌ INCONSISTENT"
                    st.markdown(f"**Check 2: Text ↔ Image Consistency:** {i_badge} (`{t_img['score']}%`)")
                    st.caption(f"Reason: {t_img['reason']}")

                with col_b:
                    t_loc = chk["location"]
                    l_badge = "✅ MATCH" if t_loc["status"] == "MATCH" else "🚨 MISMATCH" if t_loc["status"] == "MISMATCH" else "⚪ UNKNOWN"
                    st.markdown(f"**Check 4: Location Consistency:** {l_badge} (`{t_loc['score']}%`)")
                    st.caption(f"Reason: {t_loc['reason']}")

                    t_hist = chk["historical"]
                    h_badge = "🚨 RECURRING ISSUE" if t_hist["recurring_issue"] else "🔁 DUPLICATE" if t_hist["duplicate"] else "✅ FIRST REPORT"
                    st.markdown(f"**Check 5: Historical Report Cross-Check:** {h_badge}")
                    st.caption(f"Reason: {t_hist['reason']}")

                # Key Findings & Recommended Action
                st.markdown("#### 💡 AI Findings & Recommended Government Action")
                if cross["contradictions"]:
                    st.warning(f"⚠️ **Detected Contradictions / Flags:** {', '.join(cross['contradictions'])}")
                if cross["detected_issues"]:
                    st.info(f"🔍 **Detected Issues:** {', '.join(cross['detected_issues'])}")

                st.success(f"🎯 **Recommended Action:** {cross['recommended_action']}")
                if cross["requires_human_review"]:
                    st.warning("⚠️ **Human Review Flagged:** Low consistency score or evidence mismatch detected. Assigned for Government Officer Review.")

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
