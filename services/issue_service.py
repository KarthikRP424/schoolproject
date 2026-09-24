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

def check_for_duplicate(school_id: int, category: str, description: str) -> tuple:
    """
    Scans active reports for the same school and category to detect duplicates.
    Returns: (is_duplicate, parent_report_id)
    """
    OPEN_STATUSES = ("REPORTED", "VERIFIED", "UNDER_REVIEW", "INSPECTION_REQUIRED",
                     "INSPECTION_COMPLETED", "ACTION_STARTED", "ACTION_COMPLETED",
                     "STUDENT_VERIFICATION", "REOPENED", "Pending", "Under Review")
    
    placeholders = ",".join("?" * len(OPEN_STATUSES))
    active_issues = execute_query(
        f"SELECT id, report_id, description FROM issues WHERE school_id = ? AND category = ? AND status IN ({placeholders});",
        (school_id, category, *OPEN_STATUSES)
    )
    for issue in active_issues:
        words_existing = set(issue["description"].lower().split())
        words_new = set(description.lower().split())
        overlap = words_existing.intersection(words_new)
        if len(overlap) > 0 and (len(overlap) / max(len(words_new), 1)) > 0.3:
            return True, issue["report_id"]
    return False, None


def merge_duplicate_issues(duplicate_issue_id: int, master_issue_id: int, user_profile: dict) -> bool:
    """
    Marks a duplicate issue as MERGED, linking it to the master via parent_issue_id.
    Preserves all evidence — does NOT copy or delete. 
    Admin/DEO only (enforced via scope check on master issue).
    """
    allowed_roles = {"System Administrator", "District Education Officer", "State Education Department Official"}
    if user_profile.get("role") not in allowed_roles:
        return False
    
    # Verify master issue is accessible in scope
    master = get_issue_by_id(master_issue_id, user_profile)
    if not master:
        return False
    
    # Verify duplicate issue exists (bypass scope filter — admin access)
    dup = execute_query(
        "SELECT id, report_id, status, school_id FROM issues WHERE id = ?;",
        (duplicate_issue_id,), fetch="one"
    )
    if not dup or dup["status"] == "MERGED":
        return False
    
    # Must be same school
    if dup["school_id"] != master["school_id"]:
        return False
    
    prev_status = dup["status"]
    
    # Link duplicate to master and set status to MERGED
    execute_query(
        "UPDATE issues SET status = 'MERGED', parent_issue_id = ? WHERE id = ?;",
        (master_issue_id, duplicate_issue_id), fetch="rowcount"
    )
    
    # Audit log
    log_audit_event(
        user_id=user_profile["id"],
        action="MERGE_DUPLICATE",
        entity_type="issue",
        entity_id=dup["report_id"],
        prev_value=prev_status,
        new_value=f"MERGED → {master['report_id']}"
    )
    
    # Notify officers
    create_notification(
        user_id=None,
        role_target="District Education Officer",
        message=f"🔗 Issue {dup['report_id']} merged into {master['report_id']} as a duplicate.",
        notify_type="Info",
        issue_id=master_issue_id
    )
    
    return True

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

def get_issue_by_id(issue_id: int, user_profile: dict) -> dict or None:
    """
    Retrieves a single issue by its ID, enforcing role-based scoping limits.
    """
    where_scope, params = get_user_scope_filter(user_profile, table_alias="i")
    
    query = f"""
        SELECT i.*, s.name as school_name, s.district, s.taluk, s.village, 
               s.priority_level, s.priority_score, u.username as reporter_username
        FROM issues i
        JOIN schools s ON i.school_id = s.id
        JOIN users u ON i.reporter_id = u.id
        WHERE i.id = ? AND {where_scope}
    """
    params.insert(0, issue_id)
    return execute_query(query, tuple(params), fetch="one")

def is_valid_transition(old_status: str, new_status: str) -> bool:
    """
    Enforces the rigid state transition graph matching the master specification.
    """
    old = old_status.upper()
    new = new_status.upper()
    
    if old == new:
        return True
        
    valid_transitions = {
        "REPORTED": ["VERIFIED", "UNDER_REVIEW"],
        "PENDING": ["REPORTED", "VERIFIED", "UNDER_REVIEW"],  # Backward compatibility fallback
        "VERIFIED": ["INSPECTION_REQUIRED", "UNDER_REVIEW"],
        "UNDER_REVIEW": ["INSPECTION_REQUIRED", "CLOSED"],
        "INSPECTION_REQUIRED": ["INSPECTION_COMPLETED", "UNDER_REVIEW"],
        "INSPECTION_COMPLETED": ["ACTION_STARTED", "UNDER_REVIEW"],
        "ACTION_STARTED": ["ACTION_COMPLETED", "UNDER_REVIEW"],
        "ACTION_COMPLETED": ["STUDENT_VERIFICATION", "UNDER_REVIEW"],
        "STUDENT_VERIFICATION": ["CLOSED", "REOPENED"],
        "REOPENED": ["UNDER_REVIEW", "ACTION_STARTED"],
        "CLOSED": ["REOPENED"],
        "MERGED": []
    }
    
    return new in valid_transitions.get(old, [])

def update_issue_status(issue_id: int, new_status: str, user_profile: dict) -> bool:
    """
    Updates the status of an issue and appends an entry to audit logs.
    Enforces scope verification first to block unauthorized access.
    """
    current_issue = get_issue_by_id(issue_id, user_profile)
    if not current_issue:
        return False  # Block access to scoped database object

    prev_status = current_issue["status"]
    if prev_status == new_status:
        return True

    # Validate transition path legality
    if not is_valid_transition(prev_status, new_status):
        return False

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
