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
from services.sla_service import check_and_escalate_sla
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

    # Run SLA escalation check (prototype — dashboard-triggered)
    sla_result = check_and_escalate_sla()
    if sla_result["escalated"]:
        st.warning(f"⏰ **SLA Alert:** {sla_result['total_breached']} overdue issue(s) in your district. "
                   f"{len(sla_result['escalated'])} escalated to higher authority.")

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

                # Selected Detail View / Government Review & AI Verification
                st.markdown("---")
                st.subheader(f"🏛️ Government Authority Review & AI Evidence Audit — {selected_rpt_id}")
                selected_issue = next(i for i in issues if i["report_id"] == selected_rpt_id)

                # Fetch AI verification JSON
                ai_json = selected_issue.get("ai_verification_json")
                if ai_json:
                    try:
                        cross_ver = json.loads(ai_json)
                    except Exception:
                        cross_ver = None
                else:
                    cross_ver = None

                # ── 1. REPORT SUMMARY ─────────────────────────────────────────
                r_col1, r_col2, r_col3 = st.columns(3)
                with r_col1:
                    st.markdown(f"**Institution:** {selected_issue.get('school_name')}")
                    st.markdown(f"**Category:** `{selected_issue.get('category')}`")
                    st.markdown(f"**Title:** {selected_issue.get('title') or selected_issue.get('category')}")
                with r_col2:
                    st.markdown(f"**Reporter:** {selected_issue.get('reporter_role')} (ID: `{selected_issue.get('reporter_id')}`)")
                    st.markdown(f"**Date Logged:** `{selected_issue.get('submitted_time')}`")
                    st.markdown(f"**Current Status:** `{selected_issue.get('status')}`")
                with r_col3:
                    st.markdown(f"**Location:** GPS (`{selected_issue.get('latitude')}, {selected_issue.get('longitude')}`)")
                    st.markdown(f"**SLA Deadline:** `{selected_issue.get('resolution_deadline')}`")
                    if selected_issue.get("officer_decision"):
                        st.success(f"**Officer Decision:** {selected_issue['officer_decision']}")

                st.markdown(f"💬 **Complaint Description:** \"{selected_issue['description']}\"")
                if selected_issue.get("additional_remarks"):
                    st.caption(f"Remarks: {selected_issue['additional_remarks']}")

                # ── 2. EVIDENCE PANEL ─────────────────────────────────────────
                with st.expander("📁 Uploaded Evidence Files (Photo / Document / Video / GPS)", expanded=True):
                    e_col1, e_col2, e_col3 = st.columns(3)
                    with e_col1:
                        img_name = selected_issue.get("uploaded_image_name")
                        if img_name:
                            st.markdown(f"📷 **Image Evidence:** `{img_name}`")
                            st.caption("Visual evidence uploaded by reporter.")
                        else:
                            st.info("No photo evidence attached.")
                    with e_col2:
                        doc_name = selected_issue.get("uploaded_doc_name")
                        if doc_name:
                            st.markdown(f"📄 **Supporting Document:** `{doc_name}`")
                            st.caption("Maintenance invoice / engineering report attached.")
                        else:
                            st.info("No supporting document attached.")
                    with e_col3:
                        vid_name = selected_issue.get("uploaded_video_name")
                        if vid_name:
                            st.markdown(f"🎥 **Video Evidence:** `{vid_name}`")
                        else:
                            st.caption("No video evidence attached.")

                # ── 3. AI CROSS-VERIFICATION ENGINE BREAKDOWN ─────────────────
                if cross_ver:
                    st.markdown("#### 🤖 AI Multi-Source Cross-Verification Engine Audit")

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        c_score = cross_ver.get("overall_consistency_score", 0)
                        st.metric("Overall Consistency", f"{c_score}%")
                    with m2:
                        st.metric("Evidence Confidence", f"{cross_ver.get('evidence_confidence', 0)}%")
                    with m3:
                        st.metric("Risk Score", f"{cross_ver.get('risk_score', 0)}/100")
                    with m4:
                        r_lvl = cross_ver.get("risk_level", "LOW")
                        r_icon = {"CRITICAL": "🔴", "HIGH": "🟧", "MEDIUM": "🨨", "LOW": "🟩"}.get(r_lvl, "⚪")
                        st.metric("Risk Level", f"{r_icon} {r_lvl}")

                    st.progress(c_score / 100.0)

                    # 5 Checks Breakdown
                    chk = cross_ver.get("checks", {})
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        td = chk.get("text_document", {})
                        st.markdown(f"**Check 1: Text ↔ Document:** `{td.get('status')}` (`{td.get('score')}%`)")
                        st.caption(f"{td.get('reason')}")

                        ti = chk.get("text_image", {})
                        st.markdown(f"**Check 2: Text ↔ Image:** `{ti.get('status')}` (`{ti.get('score')}%`)")
                        st.caption(f"{ti.get('reason')}")

                        ds = chk.get("document", {})
                        st.markdown(f"**Check 3: Document Audit:** `{ds.get('status')}` (`{ds.get('score')}%`)")
                        st.caption(f"{ds.get('reason')}")

                    with c_col2:
                        lc = chk.get("location", {})
                        st.markdown(f"**Check 4: Location Consistency:** `{lc.get('status')}` (`{lc.get('score')}%`)")
                        st.caption(f"{lc.get('reason')}")

                        hc = chk.get("historical", {})
                        st.markdown(f"**Check 5: Historical Check:** Recurring: `{hc.get('recurring_issue')}` | Duplicate: `{hc.get('duplicate')}`")
                        st.caption(f"{hc.get('reason')}")

                    if cross_ver.get("contradictions"):
                        st.warning(f"🚨 **Flags & Contradictions:** {', '.join(cross_ver['contradictions'])}")
                    st.success(f"🎯 **AI Recommended Action:** {cross_ver.get('recommended_action')}")

                # ── 4. GOVERNMENT OFFICER DECISION PANEL ──────────────────────
                st.markdown("---")
                st.markdown("### 🏛️ Government Authority Formal Decision Panel")
                st.write("Review the report and AI evidence cross-verification above, then record your official administrative decision.")

                with st.form(f"officer_decision_form_{selected_issue['id']}"):
                    d_col1, d_col2 = st.columns([0.4, 0.6])
                    with d_col1:
                        decision_choice = st.radio(
                            "Select Government Decision *",
                            ["Accept", "Assign Inspection", "Request Clarification", "Escalate", "Reject", "Mark Resolved"]
                        )
                    with d_col2:
                        decision_remarks = st.text_area(
                            "Officer Remarks / Action Instructions *",
                            placeholder="Enter official remarks, sanction work orders, or specify required clarifications..."
                        )

                    submit_decision = st.form_submit_button("✍️ Record Government Decision & Update Status", type="primary", use_container_width=True)

                if submit_decision:
                    if not decision_remarks.strip():
                        st.error("Please enter officer remarks explaining your administrative decision.")
                    else:
                        from services.issue_service import record_officer_decision
                        ok = record_officer_decision(
                            issue_id=selected_issue["id"],
                            officer_id=user_profile["id"],
                            decision=decision_choice,
                            remarks=decision_remarks.strip()
                        )
                        if ok:
                            st.success(f"✅ Decision '{decision_choice}' recorded successfully with official audit log!")
                            st.rerun()

                # Display chronological status & audit logs
                st.markdown("#### 📜 Timeline & Audit History")
                draw_issue_status_timeline(selected_issue["status"])
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
