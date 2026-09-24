"""
services/verification_service.py
--------------------------------
Handles verification scoring and conflict discrepancy checks.
Calculates trust confidence (0–100) based on role weights and raises conflict alerts.
"""
from datetime import datetime
from database.connection import execute_query
from services.notification_service import create_notification
from services.audit_service import log_audit_event

def submit_verification(issue_id: int, user_id: int, user_role: str,
                        confirms_issue: bool) -> tuple[float, str, bool]:
    """
    Submits a new verification record and updates the issue's confidence score and status.
    Returns: (new_confidence_score, new_status, conflict_detected)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    confirms_int = 1 if confirms_issue else 0
    
    # 1. Check if user already verified this issue
    existing = execute_query(
        "SELECT id, confirms_issue FROM issue_verifications WHERE issue_id = ? AND user_id = ?;",
        (issue_id, user_id),
        fetch="one"
    )
    
    # Determine confidence weight for the specific role
    from config import VERIFICATION_WEIGHTS
    role_key = user_role
    if "student" in user_role.lower():
        role_key = "Student Representative"
    elif "volunteer" in user_role.lower():
        role_key = "Village Volunteer"
    elif "headmaster" in user_role.lower():
        role_key = "Headmaster"
    weight = VERIFICATION_WEIGHTS.get(role_key, 0.0)

    if existing:
        # Update existing
        if existing["confirms_issue"] != confirms_int:
            execute_query(
                "UPDATE issue_verifications SET confirms_issue = ?, timestamp = ? WHERE id = ?;",
                (confirms_int, timestamp, existing["id"]),
                fetch="rowcount"
            )
    else:
        # Insert new
        execute_query(
            """
            INSERT INTO issue_verifications (issue_id, user_id, user_role, confidence_weight, confirms_issue, timestamp)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (issue_id, user_id, user_role, weight, confirms_int, timestamp),
            fetch="rowcount"
        )

    # 2. Recalculate verification metrics
    confidence, status, conflict = recalculate_verification_confidence(issue_id)

    # 3. Log Audit Trail
    issue = execute_query("SELECT report_id, school_id FROM issues WHERE id = ?;", (issue_id,), fetch="one")
    if issue:
        log_audit_event(
            user_id=user_id,
            action="VERIFY_REPORT",
            entity_type="issue",
            entity_id=issue["report_id"],
            prev_value=f"Confirms: {not confirms_issue}",
            new_value=f"Confirms: {confirms_issue}"
        )

        # Notify if conflict detected
        if conflict:
            school = execute_query("SELECT name FROM schools WHERE id = ?;", (issue["school_id"],), fetch="one")
            school_name = school["name"] if school else "School"
            create_notification(
                user_id=None,
                role_target="District Education Officer",
                message=f"⚠️ CONFLICT DETECTED: Opposing verification reviews submitted on {issue['report_id']} at {school_name}.",
                notify_type="Conflict",
                issue_id=issue_id
            )

    return confidence, status, conflict

def recalculate_verification_confidence(issue_id: int) -> tuple[float, str, bool]:
    """
    Computes verification score and checks for conflicts among reporter statuses.
    """
    issue = execute_query(
        "SELECT report_id, photo_evidence_available, gps_location_available FROM issues WHERE id = ?;",
        (issue_id,),
        fetch="one"
    )
    if not issue:
        return 0.0, "Review Required", False

    verifications = execute_query(
        "SELECT user_role, confirms_issue FROM issue_verifications WHERE issue_id = ?;",
        (issue_id,)
    )

    from config import VERIFICATION_WEIGHTS
    confidence = 0.0

    # Add evidence score component (10% each for photo and GPS)
    if issue["photo_evidence_available"]:
        confidence += VERIFICATION_WEIGHTS.get("Evidence", 0.20) * 50.0
    if issue["gps_location_available"]:
        confidence += VERIFICATION_WEIGHTS.get("Evidence", 0.20) * 50.0

    # Consolidate confirmations by unique user role
    role_confirmations = {}
    for v in verifications:
        role = v["user_role"]
        role_key = role
        if "student" in role.lower():
            role_key = "Student Representative"
        elif "volunteer" in role.lower():
            role_key = "Village Volunteer"
        elif "headmaster" in role.lower():
            role_key = "Headmaster"
            
        # Overwrite or average (let's keep the latest verification per role type)
        role_confirmations[role_key] = v["confirms_issue"]

    # Check for conflict: at least one confirming and one denying
    confirms = [val for val in role_confirmations.values() if val == 1]
    denies = [val for val in role_confirmations.values() if val == 0]
    conflict_detected = len(confirms) > 0 and len(denies) > 0

    # Sum up confirming weights
    for r_key, confirms_issue in role_confirmations.items():
        if confirms_issue == 1:
            confidence += VERIFICATION_WEIGHTS.get(r_key, 0.0) * 100.0

    if conflict_detected:
        # Subtract penalty for conflict
        confidence = max(0.0, confidence - 30.0)
        v_status = "Review Required"
    else:
        if confidence >= 85.0:
            v_status = "Highly Verified"
        elif confidence >= 70.0:
            v_status = "Verified"
        elif confidence >= 40.0:
            v_status = "Review Required"
        else:
            v_status = "Low Confidence"

    # Update database verification state
    execute_query(
        "UPDATE issues SET verification_confidence = ?, verification_status = ? WHERE id = ?;",
        (confidence, v_status, issue_id),
        fetch="rowcount"
    )

    # Perform issue status transition if currently in REPORTED status
    current = execute_query("SELECT report_id, status FROM issues WHERE id = ?;", (issue_id,), fetch="one")
    if current and current["status"] in ["REPORTED", "Pending"]:
        target_status = None
        if conflict_detected:
            target_status = "UNDER_REVIEW"
        elif v_status in ["Verified", "Highly Verified"]:
            target_status = "VERIFIED"
            
        if target_status and target_status != current["status"]:
            # Perform transition
            execute_query("UPDATE issues SET status = ? WHERE id = ?;", (target_status, issue_id), fetch="rowcount")
            # Log transition to audit trails (user_id=0 → resolved as 'System' inside audit_service)
            log_audit_event(
                user_id=None,
                action="AUTO_STATUS_TRANSITION",
                entity_type="issue",
                entity_id=current["report_id"],
                prev_value=current["status"],
                new_value=target_status
            )

    return confidence, v_status, conflict_detected
