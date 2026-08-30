"""
services/issue_service.py
-------------------------
Handles business logic for reporting, viewing, and resolving school issues.
Supports automatic duplicate detection, SLA deadline calculation, and audit trail hooks.
"""
from datetime import datetime, timedelta
import json
from database.connection import execute_query, get_db_connection
from auth.permissions import get_user_scope_filter
from agent import analyze_school_report
from services.audit_service import log_audit_event
from services.notification_service import create_notification

def get_deadline_for_priority(priority_level: str) -> str:
    """
    Returns resolution deadline timestamp based on configured SLA hours.
    """
    from config import SLA_HOURS
    hours = SLA_HOURS.get(priority_level.upper(), 720)  # Default: 30 days
    deadline = datetime.now() + timedelta(hours=hours)
    return deadline.strftime("%Y-%m-%d %H:%M:%S")

def create_issue(school_id: int, reporter_id: int, reporter_role: str,
                 description: str, has_photo: bool, has_gps: bool,
                 gps_coords: str = "", photo_name: str = "") -> dict:
    """
    Creates a new issue in the system, running the AI agent analysis,
    calculating SLA deadlines, and checking for duplicates.
    """
    # 1. Fetch School Details (Geographical context)
    school = execute_query("SELECT name, district, taluk, village FROM schools WHERE id = ?;", (school_id,), fetch="one")
    if not school:
        raise ValueError("School ID not found.")

    # 2. Package data for the rule-based AI agent
    report_data = {
        "school_name": school["name"],
        "district": school["district"],
        "taluk": school["taluk"],
        "reporter_role": reporter_role,
        "issue_description": description,
        "has_photo": has_photo,
        "has_gps": has_gps
    }
    analysis = analyze_school_report(report_data)

    # 3. Parse coordinates
    lat, lon = "None", "None"
    if gps_coords and "," in gps_coords:
        try:
            parts = gps_coords.split(",")
            lat, lon = parts[0].strip(), parts[1].strip()
        except Exception:
            pass

    # 4. Generate unique report_id and time variables
    submitted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate incremental RPT identifier
    count_row = execute_query("SELECT COUNT(*) as count FROM issues;", fetch="one")
    count = count_row["count"] if count_row else 0
    report_id = f"RPT-{str(count + 1).zfill(4)}"
    
    # Calculate resolution SLA timestamp
    priority_level = analysis["priority_level"]
    resolution_deadline = get_deadline_for_priority(priority_level)
    dangerous_status = 1 if priority_level == "Urgent" else 0

    # 5. Check for duplicate complaints
    is_duplicate, parent_id = check_for_duplicate(school_id, analysis["category"], description)
    status = "Pending"
    if is_duplicate:
        status = "Under Review" # Automatically flags for review

    # 6. Insert issue record
    query = """
        INSERT INTO issues (
            report_id, school_id, reporter_id, reporter_role, category, description,
            submitted_time, latitude, longitude, status, verification_status,
            verification_confidence, dangerous_school_status,
            photo_evidence_available, gps_location_available, uploaded_image_name,
            resolution_deadline
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    issue_id = execute_query(
        query,
        (
            report_id, school_id, reporter_id, reporter_role, analysis["category"], description,
            submitted_time, lat, lon, status, analysis["verification_status"],
            10.0 if has_photo or has_gps else 0.0,  # Base confidence
            dangerous_status,
            1 if has_photo else 0,
            1 if has_gps else 0,
            photo_name if has_photo else None,
            resolution_deadline
        ),
        fetch="lastrowid"
    )

    # 7. Add evidence record if photo submitted
    if has_photo and photo_name:
        execute_query(
            """
            INSERT INTO issue_evidence (issue_id, stage, photo_name, description, timestamp, reporter_id)
            VALUES (?, 'Initial', ?, 'Initial photo submitted by reporter.', ?, ?);
            """,
            (issue_id, photo_name, submitted_time, reporter_id)
        )

    # 8. Trigger alert notifications for urgent or emergency situations
    if dangerous_status == 1:
        create_notification(
            user_id=None,
            role_target="District Education Officer",
            message=f"🚨 EMERGENCY: Unsafe {analysis['category']} reported at {school['name']} (ID: {report_id}).",
            notify_type="Emergency",
            issue_id=issue_id
        )

    # 9. Audit log entry
    log_audit_event(
        user_id=reporter_id,
        action="SUBMIT_REPORT",
        entity_type="issue",
        entity_id=report_id,
        new_value=status
    )

    return {
        "id": issue_id,
        "report_id": report_id,
        "category": analysis["category"],
        "priority_level": priority_level,
        "priority_score": analysis["priority_score"],
        "recommended_action": analysis["recommended_action"],
        "officer_summary": analysis["officer_summary"],
        "is_duplicate": is_duplicate,
        "parent_report_id": parent_id
    }

def check_for_duplicate(school_id: int, category: str, description: str) -> tuple[bool, str or None]:
    """
    Scans active reports for the same school and category to detect duplicates.
    Returns: (is_duplicate, parent_report_id)
    """
    active_issues = execute_query(
        "SELECT report_id, description FROM issues WHERE school_id = ? AND category = ? AND status != 'Closed';",
        (school_id, category)
    )
    for issue in active_issues:
        # Check text similarity or overlapping keywords
        words_existing = set(issue["description"].lower().split())
        words_new = set(description.lower().split())
        overlap = words_existing.intersection(words_new)
        
        # Simple heuristic: if 30% or more words overlap, it's a potential duplicate
        if len(overlap) > 0 and (len(overlap) / max(len(words_new), 1)) > 0.3:
            return True, issue["report_id"]
            
    return False, None

def get_filtered_issues(user_profile: dict, filters: dict = None) -> list:
    """
    Fetches school issues according to user role permissions and filters.
    """
    where_scope, params = get_user_scope_filter(user_profile, table_alias="i")
    
    query = f"""
        SELECT i.*, s.name as school_name, s.district, s.taluk, s.village, 
               s.priority_level, s.priority_score, u.username as reporter_username
        FROM issues i
        JOIN schools s ON i.school_id = s.id
        JOIN users u ON i.reporter_id = u.id
        WHERE {where_scope}
    """
    
    if filters:
        if filters.get("district") and filters["district"] != "All":
            query += " AND s.district = ?"
            params.append(filters["district"])
        if filters.get("taluk") and filters["taluk"] != "All":
            query += " AND s.taluk = ?"
            params.append(filters["taluk"])
        if filters.get("reporter_role") and filters["reporter_role"] != "All":
            query += " AND i.reporter_role = ?"
            params.append(filters["reporter_role"])
        if filters.get("priority_level") and filters["priority_level"] != "All":
            query += " AND s.priority_level = ?"
            params.append(filters["priority_level"])
        if filters.get("status") and filters["status"] != "All":
            query += " AND i.status = ?"
            params.append(filters["status"])
            
    query += " ORDER BY i.submitted_time DESC;"
    return execute_query(query, tuple(params))

def update_issue_status(issue_id: int, new_status: str, user_profile: dict) -> bool:
    """
    Updates the status of an issue and appends an entry to audit logs.
    """
    current_issue = execute_query("SELECT report_id, status FROM issues WHERE id = ?;", (issue_id,), fetch="one")
    if not current_issue:
        return False

    prev_status = current_issue["status"]
    if prev_status == new_status:
        return True

    # Update in DB
    execute_query("UPDATE issues SET status = ? WHERE id = ?;", (new_status, issue_id), fetch="rowcount")

    # Logging and auditing
    log_audit_event(
        user_id=user_profile["id"],
        action="UPDATE_STATUS",
        entity_type="issue",
        entity_id=current_issue["report_id"],
        prev_value=prev_status,
        new_value=new_status
    )
    
    return True
