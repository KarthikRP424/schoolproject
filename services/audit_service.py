"""
services/audit_service.py
-------------------------
Manages the application's immutable audit log history.
Captures key administrative events (status updates, verifications, system edits).
"""
from datetime import datetime
from database.connection import execute_query

def log_audit_event(user_id: int or None, action: str, entity_type: str,
                    entity_id: str, prev_value: str = None, new_value: str = None):
    """
    Writes a single log record into the audit_logs table.
    Determines user profile context automatically if user_id is provided.
    """
    username = "System"
    role = "Automated Job"
    if user_id:
        user = execute_query("SELECT username, role FROM users WHERE id = ?;", (user_id,), fetch="one")
        if user:
            username = user["username"]
            role = user["role"]
            
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query(
        """
        INSERT INTO audit_logs (user_id, username, role, action, timestamp, entity_type, entity_id, prev_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (user_id, username, role, action, timestamp, entity_type, str(entity_id), prev_value, new_value),
        fetch="rowcount"
    )

def get_audit_trail(entity_type: str, entity_id: str) -> list:
    """
    Returns history of actions logged against a specific entity.
    """
    return execute_query(
        "SELECT * FROM audit_logs WHERE entity_type = ? AND entity_id = ? ORDER BY timestamp ASC;",
        (entity_type, str(entity_id))
    )
