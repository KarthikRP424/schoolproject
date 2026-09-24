"""
services/inspection_service.py
------------------------------
Logs and manages inspector findings and verification logs.
Automatically updates target issue statuses and logs audit trails.
Includes student consensus 3/5 voting for final issue closure.
"""
from datetime import datetime
from database.connection import execute_query
from services.audit_service import log_audit_event
from services.notification_service import create_notification

def create_inspection(school_id: int, issue_id: int or None, inspector_name: str,
                      findings: str, verified_status: str, recommendations: str = "",
                      lat: str = "", lon: str = "") -> int:
    """
    Saves an inspection visit record in the database.
    Advances the issue to INSPECTION_COMPLETED and logs the audit trail.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ins_id = execute_query(
        """
        INSERT INTO inspections (school_id, issue_id, inspector_name, timestamp, findings, latitude, longitude, verified_status, recommendations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (school_id, issue_id, inspector_name, timestamp, findings, lat, lon, verified_status, recommendations),
        fetch="lastrowid"
    )
    
    if issue_id:
        # Advance issue workflow to canonical INSPECTION_COMPLETED
        execute_query(
            "UPDATE issues SET status = 'INSPECTION_COMPLETED', verification_status = 'Verified' WHERE id = ?;",
            (issue_id,),
            fetch="rowcount"
        )
        
        issue = execute_query("SELECT report_id, school_id FROM issues WHERE id = ?;", (issue_id,), fetch="one")
        if issue:
            log_audit_event(
                user_id=None,
                action="LOG_INSPECTION",
                entity_type="issue",
                entity_id=issue["report_id"],
                prev_value="INSPECTION_REQUIRED",
                new_value=f"INSPECTION_COMPLETED by {inspector_name}"
            )
            # Notify District Officer that inspection is done
            create_notification(
                user_id=None,
                role_target="District Education Officer",
                message=f"✅ Inspection completed for issue {issue['report_id']} by {inspector_name}. Findings: {findings[:100]}",
                notify_type="Inspection",
                issue_id=issue_id
            )
            
    return ins_id


def get_school_inspections(school_id: int) -> list:
    """
    Fetches the history of inspections logged against a specific school.
    """
    return execute_query("SELECT * FROM inspections WHERE school_id = ? ORDER BY timestamp DESC;", (school_id,))


def submit_student_consensus(issue_id: int, student_user_id: int, approves: bool) -> dict:
    """
    Records a student representative's consensus vote on a resolved issue.
    Requires 3 out of 5 approvals to CLOSE, or 3 rejections to REOPEN.
    Returns: { 'action': 'CLOSED' | 'REOPENED' | 'PENDING', 'approvals': int, 'rejections': int }
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    confirms_int = 1 if approves else 0
    
    # Upsert student vote in issue_verifications with stage='consensus'
    existing = execute_query(
        "SELECT id FROM issue_verifications WHERE issue_id = ? AND user_id = ? AND user_role = 'Student Representative';",
        (issue_id, student_user_id), fetch="one"
    )
    if existing:
        execute_query(
            "UPDATE issue_verifications SET confirms_issue = ?, timestamp = ? WHERE id = ?;",
            (confirms_int, timestamp, existing["id"]), fetch="rowcount"
        )
    else:
        execute_query(
            """
            INSERT INTO issue_verifications (issue_id, user_id, user_role, confidence_weight, confirms_issue, timestamp)
            VALUES (?, ?, 'Student Representative', 0.10, ?, ?);
            """,
            (issue_id, student_user_id, confirms_int, timestamp), fetch="rowcount"
        )

    # Count consensus votes (student reps only)
    votes = execute_query(
        "SELECT confirms_issue FROM issue_verifications WHERE issue_id = ? AND user_role = 'Student Representative';",
        (issue_id,)
    )
    approvals = sum(1 for v in votes if v["confirms_issue"] == 1)
    rejections = sum(1 for v in votes if v["confirms_issue"] == 0)
    
    action = "PENDING"
    issue = execute_query("SELECT report_id, status FROM issues WHERE id = ?;", (issue_id,), fetch="one")
    
    if approvals >= 3:
        # Majority approval → CLOSE
        execute_query("UPDATE issues SET status = 'CLOSED' WHERE id = ?;", (issue_id,), fetch="rowcount")
        action = "CLOSED"
        if issue:
            log_audit_event(
                user_id=student_user_id,
                action="STUDENT_CONSENSUS_CLOSED",
                entity_type="issue",
                entity_id=issue["report_id"],
                prev_value=issue["status"],
                new_value="CLOSED"
            )
    elif rejections >= 3:
        # Majority rejection → REOPEN
        execute_query("UPDATE issues SET status = 'REOPENED' WHERE id = ?;", (issue_id,), fetch="rowcount")
        action = "REOPENED"
        if issue:
            log_audit_event(
                user_id=student_user_id,
                action="STUDENT_CONSENSUS_REOPENED",
                entity_type="issue",
                entity_id=issue["report_id"],
                prev_value=issue["status"],
                new_value="REOPENED"
            )
            create_notification(
                user_id=None,
                role_target="District Education Officer",
                message=f"⚠️ Issue {issue['report_id']} REOPENED by student consensus ({rejections}/5 rejections).",
                notify_type="Reopen",
                issue_id=issue_id
            )

    return {"action": action, "approvals": approvals, "rejections": rejections}


def get_pending_student_verifications(school_id: int) -> list:
    """
    Returns issues awaiting student consensus (status = STUDENT_VERIFICATION) for a school.
    """
    return execute_query(
        """
        SELECT i.*, s.name as school_name 
        FROM issues i 
        JOIN schools s ON i.school_id = s.id 
        WHERE i.school_id = ? AND i.status = 'STUDENT_VERIFICATION'
        ORDER BY i.submitted_time DESC;
        """,
        (school_id,)
    )

