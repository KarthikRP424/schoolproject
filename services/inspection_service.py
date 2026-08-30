"""
services/inspection_service.py
------------------------------
Logs and manages inspector findings and verification logs.
Automatically updates target issue statuses and logs audit trails.
"""
from datetime import datetime
from database.connection import execute_query
from services.audit_service import log_audit_event

def create_inspection(school_id: int, issue_id: int or None, inspector_name: str,
                      findings: str, verified_status: str, recommendations: str = "",
                      lat: str = "", lon: str = "") -> int:
    """
    Saves an inspection visit record in the database.
    If associated with an open issue, updates the issue status and logs audit tracking.
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
        # Advance issue workflow to 'Inspection Completed'
        execute_query(
            "UPDATE issues SET status = 'Inspection Completed', verification_status = 'Verified' WHERE id = ?;",
            (issue_id,),
            fetch="rowcount"
        )
        
        issue = execute_query("SELECT report_id FROM issues WHERE id = ?;", (issue_id,), fetch="one")
        if issue:
            # Audit trail hook
            log_audit_event(
                user_id=None,
                action="LOG_INSPECTION",
                entity_type="issue",
                entity_id=issue["report_id"],
                prev_value="Inspection Required",
                new_value=f"Inspection Completed by {inspector_name}"
            )
            
    return ins_id

def get_school_inspections(school_id: int) -> list:
    """
    Fetches the history of inspections logged against a specific school.
    """
    return execute_query("SELECT * FROM inspections WHERE school_id = ? ORDER BY timestamp DESC;", (school_id,))
