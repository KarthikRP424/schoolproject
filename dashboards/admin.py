"""
dashboards/admin.py
-------------------
System Administrator dashboard: full statewide monitoring + ADMIN-ONLY safe demo reset.
SECURITY: System Administrator role ONLY - State Officers cannot access.
"""
import streamlit as st
import pandas as pd
from database.connection import execute_query
from services.priority_engine import update_all_school_scores
from services.sla_service import check_and_escalate_sla
from services.audit_service import log_audit_event


def render_admin_dashboard(user_profile: dict):
    if user_profile.get("role") != "System Administrator":
        st.error("Access Denied. Restricted to System Administrators only.")
        st.stop()

    st.title("System Administration Control Center")
    tab1, tab2, tab3 = st.tabs(["State Overview", "Database Management", "Audit Log"])

    with tab1:
        update_all_school_scores()
        sla_result = check_and_escalate_sla()
        if sla_result["escalated"]:
            n = sla_result["total_breached"]
            e = len(sla_result["escalated"])
            st.warning(f"SLA Engine: {n} overdue issue(s). {e} escalated.")

        schools = execute_query("SELECT * FROM schools ORDER BY priority_score DESC;")
        issues = execute_query(
            "SELECT i.*, s.name as school_name, s.district "
            "FROM issues i JOIN schools s ON i.school_id = s.id "
            "ORDER BY i.submitted_time DESC;"
        )
        ur = execute_query("SELECT COUNT(*) as count FROM users;", fetch="one")
        open_issues = [i for i in issues if i.get("status") not in ("CLOSED", "MERGED")]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Schools", len(schools))
        col2.metric("Total Issues", len(issues))
        col3.metric("Open Issues", len(open_issues))
        col4.metric("Registered Users", ur["count"] if ur else 0)

        high = [s for s in schools if str(s.get("priority_level", "")).upper() in ("HIGH", "URGENT")]
        if high:
            st.markdown("#### High Priority Schools")
            df = pd.DataFrame(high)
            visible = [c for c in ["name", "district", "priority_level", "health_score", "priority_score", "decline_risk"] if c in df.columns]
            st.dataframe(df[visible], use_container_width=True)

    with tab2:
        st.markdown("### Safe Demo Database Reset")
        st.info("Deletes synthetic demo records and re-seeds fresh data. Schema is NOT dropped.")
        st.warning("WARNING: Deletes all issues, users, notifications, and audit logs then re-seeds. Cannot be undone.")

        row_counts = {}
        for table in ["schools", "issues", "users", "notifications", "audit_logs"]:
            try:
                r = execute_query(f"SELECT COUNT(*) as count FROM {table};", fetch="one")
                row_counts[table] = r["count"] if r else 0
            except Exception:
                row_counts[table] = "N/A"

        st.markdown("**Current Row Counts:**")
        for tbl, cnt in row_counts.items():
            st.text(f"  {tbl}: {cnt} rows")

        confirm = st.checkbox("I confirm: delete all demo data and re-seed the database.")
        if st.button("Reset Demo Database", type="primary", disabled=not confirm):
            _safe_demo_reset(user_profile)
            st.success("Demo database reset and re-seeded successfully!")
            st.rerun()

    with tab3:
        st.markdown("### System Audit Trail")
        logs = execute_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 200;")
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True)
        else:
            st.info("No audit events recorded yet.")


def _safe_demo_reset(user_profile: dict):
    from database.seed import seed_demo_data
    log_audit_event(
        user_id=user_profile["id"],
        action="ADMIN_DEMO_RESET",
        entity_type="system",
        entity_id="database",
        prev_value="Demo data present",
        new_value="Cleared and re-seeded"
    )
    for table in ["audit_logs", "notifications", "issue_evidence", "issue_verifications",
                  "inspections", "historical_scores", "enrollment_records", "attendance_records",
                  "issues", "users", "schools", "system_meta"]:
        try:
            execute_query(f"DELETE FROM {table};", fetch="rowcount")
        except Exception:
            pass
    seed_demo_data()
