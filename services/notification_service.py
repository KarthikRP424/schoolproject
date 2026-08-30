"""
services/notification_service.py
--------------------------------
Handles alert logging and notification routing across users and administration roles.
Provides counts of unread notifications and marks them read.
"""
from datetime import datetime
from database.connection import execute_query

def create_notification(user_id: int or None, role_target: str or None,
                        message: str, notify_type: str, issue_id: int or None = None):
    """
    Saves an alert log in the database.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query(
        """
        INSERT INTO notifications (user_id, role_target, message, is_read, timestamp, type, issue_id)
        VALUES (?, ?, ?, 0, ?, ?, ?);
        """,
        (user_id, role_target, message, timestamp, notify_type, issue_id),
        fetch="rowcount"
    )

def get_unread_notifications(user_profile: dict) -> list:
    """
    Returns unread alerts matching the active user or target user role.
    """
    role = user_profile.get("role")
    user_id = user_profile.get("id")
    return execute_query(
        """
        SELECT * FROM notifications 
        WHERE is_read = 0 AND (user_id = ? OR role_target = ?)
        ORDER BY timestamp DESC;
        """,
        (user_id, role)
    )

def mark_notification_as_read(notif_id: int):
    """
    Updates the is_read status of the notification.
    """
    execute_query("UPDATE notifications SET is_read = 1 WHERE id = ?;", (notif_id,), fetch="rowcount")
