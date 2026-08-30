"""
config.py
---------
Configuration parameters for the Karnataka Government School Monitoring Platform.
Contains settings for the database provider, SLA configurations, and logic weights.
"""
import os

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # Options: "sqlite", "mysql"
SQLITE_DB_PATH = "school_monitoring.db"

# MySQL Configurations (for future migration support)
MYSQL_HOST = os.getenv("DB_HOST", "localhost")
MYSQL_PORT = int(os.getenv("DB_PORT", "3306"))
MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "")
MYSQL_DATABASE = os.getenv("DB_NAME", "school_monitoring")

# ─────────────────────────────────────────────────────────────────────────────
# SLA RESOLUTION DEADLINES (IN HOURS)
# ─────────────────────────────────────────────────────────────────────────────
SLA_HOURS = {
    "EMERGENCY": 24,
    "CRITICAL": 48,
    "HIGH": 168,      # 7 Days
    "MODERATE": 720,  # 30 Days
    "LOW": 1440       # 60 Days
}

# ─────────────────────────────────────────────────────────────────────────────
# CALCULATION ENGINE WEIGHTS
# ─────────────────────────────────────────────────────────────────────────────

# Verification Confidence weights (must sum to 1.0)
VERIFICATION_WEIGHTS = {
    "Headmaster": 0.30,
    "Student Representative": 0.30,
    "Village Volunteer": 0.20,
    "Evidence": 0.20
}

# Priority Score components (must sum to 1.0)
PRIORITY_WEIGHTS = {
    "teacher_shortage": 0.25,
    "infrastructure_condition": 0.25,
    "basic_facilities": 0.20,
    "enrollment_decline": 0.15,
    "unresolved_issues": 0.15
}
