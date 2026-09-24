"""
database/models.py
------------------
Contains table schemas and initialization routines for the SQLite database.
Defines SQL execution parameters for all required tracking tables.
"""
from database.connection import get_db_connection

def initialize_database():
    """
    Creates all required tables in the database if they do not exist.
    Runs idempotently on application startup.
    """
    tables = [
        # 1. SCHOOLS
        """
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            district TEXT NOT NULL,
            taluk TEXT NOT NULL,
            village TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            school_type TEXT NOT NULL,
            num_students INTEGER NOT NULL,
            num_teachers INTEGER NOT NULL,
            required_teachers INTEGER NOT NULL,
            available_teachers INTEGER NOT NULL,
            sanctioned_teachers INTEGER DEFAULT 0,
            present_teachers INTEGER DEFAULT 0,
            absent_teachers INTEGER DEFAULT 0,
            attendance_pct REAL NOT NULL,
            enrollment_trend_json TEXT,  -- JSON string of {year: student_count}
            facility_status_json TEXT,   -- JSON string of {facility: status}
            health_score REAL DEFAULT 0.0,
            priority_score REAL DEFAULT 0.0,
            decline_risk REAL DEFAULT 0.0,
            priority_level TEXT DEFAULT 'LOW'
        );
        """,

        # 2. USERS
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL,
            school_id INTEGER NULL,
            district TEXT NULL,
            taluk TEXT NULL,
            village TEXT NULL,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        );
        """,

        # 3. ISSUES
        """
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE NOT NULL,
            school_id INTEGER NOT NULL,
            reporter_id INTEGER NOT NULL,
            reporter_role TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            submitted_time TEXT NOT NULL,
            latitude TEXT,
            longitude TEXT,
            status TEXT DEFAULT 'Pending', -- 'Pending', 'Verified', 'Under Review', 'Inspection Required', 'Inspection Completed', 'Action Started', 'Action Completed', 'Student Verification', 'Closed'
            verification_status TEXT DEFAULT 'Review Required', -- 'Low Confidence', 'Review Required', 'Verified', 'Highly Verified'
            verification_confidence REAL DEFAULT 0.0,
            dangerous_school_status INTEGER DEFAULT 0,  -- 0 or 1
            photo_evidence_available INTEGER DEFAULT 0,  -- 1 if a photo was submitted
            gps_location_available INTEGER DEFAULT 0,    -- 1 if GPS coordinates were provided
            uploaded_image_name TEXT,
            assignment TEXT NULL,
            resolution_deadline TEXT NOT NULL,
            is_escalated INTEGER DEFAULT 0,
            escalation_level INTEGER DEFAULT 0,
            parent_issue_id INTEGER NULL,
            FOREIGN KEY (school_id) REFERENCES schools(id),
            FOREIGN KEY (reporter_id) REFERENCES users(id),
            FOREIGN KEY (parent_issue_id) REFERENCES issues(id)
        );
        """,

        # 4. ISSUE EVIDENCE
        """
        CREATE TABLE IF NOT EXISTS issue_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            stage TEXT NOT NULL, -- 'Initial', 'Verification', 'Inspection', 'Action Started', 'Action Completed', 'Student Verification'
            photo_name TEXT NOT NULL,
            description TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            reporter_id INTEGER NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id),
            FOREIGN KEY (reporter_id) REFERENCES users(id)
        );
        """,

        # 5. ISSUE VERIFICATIONS
        """
        CREATE TABLE IF NOT EXISTS issue_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            user_role TEXT NOT NULL,
            confidence_weight REAL NOT NULL,
            confirms_issue INTEGER NOT NULL,  -- 1 for Yes, 0 for No (Conflict)
            timestamp TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """,

        # 6. STUDENT FEEDBACK (Verification after Action Completed)
        """
        CREATE TABLE IF NOT EXISTS student_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            rep_name TEXT NOT NULL,
            status_rating TEXT NOT NULL, -- 'Fully Solved', 'Partially Solved', 'Not Solved'
            feedback_text TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id)
        );
        """,

        # 7. INSPECTIONS
        """
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            issue_id INTEGER NULL,
            inspector_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            findings TEXT NOT NULL,
            latitude TEXT,
            longitude TEXT,
            verified_status TEXT NOT NULL,
            recommendations TEXT,
            FOREIGN KEY (school_id) REFERENCES schools(id),
            FOREIGN KEY (issue_id) REFERENCES issues(id)
        );
        """,

        # 8. AUDIT LOGS
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            prev_value TEXT,
            new_value TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """,

        # 9. NOTIFICATIONS
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NULL,
            role_target TEXT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL, -- 'Emergency', 'Conflict', 'Escalation', 'SLA Approaching', 'Resolution Rejected'
            issue_id INTEGER NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (issue_id) REFERENCES issues(id)
        );
        """,

        # 10. ATTENDANCE RECORDS (for historical trend tracking)
        """
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            month_name TEXT NOT NULL,
            attendance_pct REAL NOT NULL,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        );
        """,

        # 11. ENROLLMENT RECORDS (for trend plotting)
        """
        CREATE TABLE IF NOT EXISTS enrollment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            num_students INTEGER NOT NULL,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        );
        """,

        # 12. HISTORICAL SCORES (school score history tracker)
        """
        CREATE TABLE IF NOT EXISTS historical_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            health_score REAL NOT NULL,
            priority_score REAL NOT NULL,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        );
        """,

        # 13. SEED LOG (To track idempotent seeds)
        """
        CREATE TABLE IF NOT EXISTS system_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        import config
        for statement in tables:
            if config.DB_TYPE == "mysql":
                # Translate DDL parameters for MySQL compatibility
                statement = statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INT AUTO_INCREMENT PRIMARY KEY")
                statement = statement.replace("REAL", "DOUBLE")
                statement = statement.replace("TEXT", "LONGTEXT")
            cursor.execute(statement)
