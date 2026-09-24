"""
services/sla_service.py
-----------------------
SLA Tracking and Escalation Engine.

Checks issues that have breached their resolution_deadline and
cascades escalation notifications up the chain:
    School Headmaster -> Taluk Officer -> District Officer -> State Officer

NOTE: This is prototype behaviour - triggered on dashboard load.
In production, this should run as a scheduled cron job.
"""
from datetime import datetime
from database.connection import execute_query
from services.notification_service import create_notification
from services.audit_service import log_audit_event

ESCALATION_CHAIN = [
    "Headmaster",
    "Taluk Education Officer",
    "District Education Officer",
    "State Education Department Official",
]

ESCALATABLE_STATUSES = (
    "REPORTED", "VERIFIED", "UNDER_REVIEW", "INSPECTION_REQUIRED",
    "INSPECTION_COMPLETED", "ACTION_STARTED", "ACTION_COMPLETED",
    "STUDENT_VERIFICATION", "REOPENED",
    "Pending", "Under Review",
)


def check_and_escalate_sla():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    placeholders = ",".join("?" * len(ESCALATABLE_STATUSES))

    breached_issues = execute_query(
        f"""
        SELECT i.id, i.report_id, i.school_id, i.category, i.status,
               i.resolution_deadline, i.escalation_level,
               s.name as school_name, s.district, s.taluk, s.village
        FROM issues i
        JOIN schools s ON i.school_id = s.id
        WHERE i.status IN ({placeholders})
          AND i.resolution_deadline IS NOT NULL
          AND i.resolution_deadline < ?
        ORDER BY i.resolution_deadline ASC;
        """,
        (*ESCALATABLE_STATUSES, now)
    )

    escalated = []
    for issue in breached_issues:
        current_level = issue.get("escalation_level") or 0
        next_level = min(current_level + 1, len(ESCALATION_CHAIN) - 1)

        if current_level >= len(ESCALATION_CHAIN) - 1:
            continue

        target_role = ESCALATION_CHAIN[next_level]
        deadline_str = issue["resolution_deadline"]

        try:
            deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
            overdue_hours = int((datetime.now() - deadline_dt).total_seconds() / 3600)
            overdue_label = f"{overdue_hours}h overdue"
        except Exception:
            overdue_label = "deadline exceeded"

        msg = (
            f"SLA BREACH: Issue {issue['report_id']} ({issue['category']}) at "
            f"{issue['school_name']}, {issue['district']} is {overdue_label}. "
            f"Status: {issue['status']}. Escalated to {target_role}."
        )

        create_notification(
            user_id=None,
            role_target=target_role,
            message=msg,
            notify_type="SLA_Breach",
            issue_id=issue["id"]
        )

        execute_query(
            "UPDATE issues SET escalation_level = ? WHERE id = ?;",
            (next_level, issue["id"]),
            fetch="rowcount"
        )

        log_audit_event(
            user_id=None,
            action="SLA_ESCALATION",
            entity_type="issue",
            entity_id=issue["report_id"],
            prev_value=f"Level {current_level} ({ESCALATION_CHAIN[current_level]})",
            new_value=f"Level {next_level} ({target_role})"
        )

        escalated.append({
            "report_id": issue["report_id"],
            "school": issue["school_name"],
            "overdue": overdue_label,
            "escalated_to": target_role
        })

    return {
        "total_breached": len(breached_issues),
        "escalated": escalated
    }


def get_sla_status_for_issue(issue):
    deadline_str = issue.get("resolution_deadline")
    if not deadline_str:
        return {"status": "NO_DEADLINE", "remaining_hours": None, "label": "No deadline set"}

    try:
        deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return {"status": "INVALID", "remaining_hours": None, "label": "Invalid deadline"}

    now = datetime.now()
    diff_hours = int((deadline_dt - now).total_seconds() / 3600)

    if diff_hours < 0:
        label = f"Overdue by {abs(diff_hours)}h"
        status = "BREACHED"
    elif diff_hours <= 24:
        label = f"Due soon: {diff_hours}h remaining"
        status = "DUE_SOON"
    else:
        days = diff_hours // 24
        label = f"On track: {days}d {diff_hours % 24}h remaining"
        status = "ON_TRACK"

    return {
        "status": status,
        "remaining_hours": diff_hours,
        "label": label
    }
